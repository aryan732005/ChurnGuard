import time

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field, field_validator

from app.auth.basic_auth import verify_admin
from app.ml.experiments import compare_runs, get_run, list_runs, save_retrain_experiment
from app.ml.nl_explain import generate_nl_explanation
from app.ml.predictor import predictor
from app.ml.retrain import simulate_retrain
from app.ml.sanitize import sanitize_prediction_payload
from app.ml.validation import validate_csv_upload, validate_prediction_input
from app.ml.drift import check_drift
from app.ml.features import apply_feature_engineering_df
from app.observability.logging_config import get_recent_logs, latency_stats, record_latency_ms, setup_logging
from app.rate_limit import limiter
from app.reports.email_report import send_executive_report
from app.reports.executive_pdf import build_executive_summary_pdf

router = APIRouter(prefix="/api", tags=["api"])
logger = setup_logging()


class PredictRequest(BaseModel):
    gender: str = "Male"
    SeniorCitizen: int = 0
    Partner: str = "No"
    Dependents: str = "No"
    tenure: int = Field(12, ge=0, le=72)
    PhoneService: str = "Yes"
    MultipleLines: str = "No"
    InternetService: str = "DSL"
    OnlineSecurity: str = "No"
    OnlineBackup: str = "No"
    DeviceProtection: str = "No"
    TechSupport: str = "No"
    StreamingTV: str = "No"
    StreamingMovies: str = "No"
    Contract: str = "Month-to-month"
    PaperlessBilling: str = "Yes"
    PaymentMethod: str = "Electronic check"
    MonthlyCharges: float = Field(70.0, ge=0, le=200)
    TotalCharges: float = Field(840.0, ge=0)


class RoiRequest(BaseModel):
    at_risk_count: int = Field(10, ge=0)
    avg_monthly_revenue: float = Field(70.0, ge=0)
    offer_cost: float = Field(15.0, ge=0)
    lifetime_months: float = Field(24.0, ge=1)
    success_rate_pct: float = Field(25.0, ge=0, le=100)


class NlExplainRequest(BaseModel):
    risk_level: str = "Medium"
    churn_probability: float = 50.0
    top_factors: list[dict] = Field(default_factory=list)
    attributes: dict = Field(default_factory=dict)


class CohortSimRequest(BaseModel):
    retain_pct: float = Field(15.0, ge=5, le=30)
    months: int = Field(6, ge=3, le=12)
    success_rate_pct: float = Field(25.0, ge=5, le=60)


class CompareExperimentsRequest(BaseModel):
    run_ids: list[str] = Field(..., min_length=1, max_length=3)


class InterestRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)
    message: str = Field("", max_length=2000)
    source: str = Field("landing", max_length=50)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        import re
        cleaned = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", cleaned):
            raise ValueError("Invalid email address")
        return cleaned

    @field_validator("message", "source")
    @classmethod
    def strip_text(cls, v: str) -> str:
        return v.strip()


class ImpactCalcRequest(BaseModel):
    avg_monthly_revenue: float = Field(70.0, ge=0)
    retention_capacity: int = Field(50, ge=1)
    top_pct: float = Field(10.0, ge=1, le=50)
    success_rate_pct: float = Field(25.0, ge=0, le=100)
    lifetime_months: float = Field(24.0, ge=1)
    offer_cost: float = Field(15.0, ge=0)


class ReportEmailRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=200)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        import re
        cleaned = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", cleaned):
            raise ValueError("Invalid email address")
        return cleaned


@router.post("/predict")
@limiter.limit("60/minute")
def api_predict(request: Request, body: PredictRequest):
    if not predictor.ready:
        raise HTTPException(503, "Model not available")
    raw = body.model_dump()
    clean, sanitize_errors = sanitize_prediction_payload(raw)
    if sanitize_errors:
        raise HTTPException(400, detail={"errors": sanitize_errors})
    errors = validate_prediction_input(clean)
    if errors:
        raise HTTPException(400, detail={"errors": errors})
    t0 = time.perf_counter()
    result = predictor.predict_one(clean)
    record_latency_ms((time.perf_counter() - t0) * 1000, "/api/predict")
    logger.info("predict risk=%s prob=%s", result.get("risk_level"), result.get("churn_probability"))
    return result


@router.post("/predict/explain")
@limiter.limit("30/minute")
def api_predict_explain(request: Request, body: NlExplainRequest):
    return generate_nl_explanation(
        body.risk_level,
        body.churn_probability,
        body.top_factors,
        body.attributes,
    )


@router.post("/batch-predict")
@limiter.limit("20/minute")
async def api_batch_predict(request: Request, file: UploadFile = File(...)):
    if not predictor.ready:
        raise HTTPException(503, "Model not available")
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, detail={"errors": ["Upload a CSV file (.csv extension required)."]})

    import io
    import pandas as pd

    content = await file.read()
    logger.info("batch_upload filename=%s bytes=%s", file.filename, len(content))
    errors = validate_csv_upload(None, len(content))
    if errors:
        raise HTTPException(400, detail={"errors": errors})

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception:
        logger.exception("batch_csv_parse_error")
        raise HTTPException(400, detail={"errors": ["Could not parse CSV. Check file encoding and format."]})

    errors = validate_csv_upload(df, len(content))
    if errors:
        raise HTTPException(400, detail={"errors": errors})

    drift = check_drift(apply_feature_engineering_df(df))
    predictor.last_drift = drift
    result = predictor.predict_batch(df)
    return {
        "rows": len(result),
        "columns": list(result.columns),
        "data": result.head(500).to_dict(orient="records"),
        "csv": result.to_csv(index=False),
        "drift": drift,
    }


@router.post("/retrain-simulation")
@limiter.limit("10/minute")
async def api_retrain_simulation(
    request: Request,
    file: UploadFile = File(...),
    _admin: str = Depends(verify_admin),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, detail={"errors": ["Upload a CSV file with Churn labels for simulation."]})

    content = await file.read()
    import io
    import pandas as pd

    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception:
        raise HTTPException(400, detail={"errors": ["Invalid CSV file."]})

    errors = validate_csv_upload(df, len(content))
    if errors:
        raise HTTPException(400, detail={"errors": errors})
    if "Churn" not in df.columns:
        raise HTTPException(400, detail={"errors": ['Column "Churn" is required for retrain simulation.']})

    metrics = predictor.metrics().get("best_test_metrics", {})
    # Flatten mean±std dicts for retrain simulation
    flat_metrics = {}
    for k, v in metrics.items():
        flat_metrics[k] = v.get("mean", v) if isinstance(v, dict) else v
    try:
        result = simulate_retrain(content, flat_metrics)
    except ValueError as exc:
        raise HTTPException(400, detail={"errors": [str(exc)]})
    exp = save_retrain_experiment(result)
    result["experiment_id"] = exp["full_run_id"]
    result["experiments_url"] = f"/experiments?run={exp['full_run_id']}"
    return result


@router.post("/roi")
@limiter.limit("60/minute")
def api_roi(request: Request, body: RoiRequest):
    return predictor.compute_roi(
        body.at_risk_count,
        body.avg_monthly_revenue,
        body.offer_cost,
        body.lifetime_months,
        body.success_rate_pct,
    )


@router.post("/cohort-simulation")
@limiter.limit("60/minute")
def api_cohort_simulation(request: Request, body: CohortSimRequest):
    return predictor.cohort_retention_simulation(
        body.retain_pct, body.months, body.success_rate_pct
    )


@router.get("/model-info")
@limiter.limit("120/minute")
def api_model_info(request: Request):
    return predictor.model_info()


@router.get("/drift-status")
@limiter.limit("120/minute")
def api_drift_status(request: Request):
    if predictor.last_drift:
        return predictor.last_drift
    return predictor.stats.get(
        "drift_monitoring",
        {"overall_status": "unknown", "note": "Upload a batch CSV to compute drift."},
    )


@router.post("/drift-check")
@limiter.limit("20/minute")
async def api_drift_check(request: Request, file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, detail={"errors": ["Upload a CSV file."]})
    import io
    import pandas as pd
    content = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(content))
    except Exception:
        raise HTTPException(400, detail={"errors": ["Could not parse CSV."]})
    drift = check_drift(apply_feature_engineering_df(df))
    predictor.last_drift = drift
    return drift


@router.get("/metrics")
@limiter.limit("120/minute")
def api_metrics(request: Request):
    return predictor.metrics()


@router.get("/business-impact")
@limiter.limit("60/minute")
def api_business_impact(request: Request, top_pct: float = Query(10.0, ge=1, le=50)):
    if not predictor.ready:
        raise HTTPException(503, "Model not available")
    return predictor.business_impact(top_pct)


@router.post("/impact-calculator")
@limiter.limit("60/minute")
def api_impact_calculator(request: Request, body: ImpactCalcRequest):
    if not predictor.ready:
        raise HTTPException(503, "Model not available")
    impact = predictor.business_impact(body.top_pct)
    actionable = min(body.retention_capacity, impact["customer_count"])
    roi = predictor.compute_roi(
        actionable,
        body.avg_monthly_revenue,
        body.offer_cost,
        body.lifetime_months,
        body.success_rate_pct,
    )
    return {
        **impact,
        "retention_capacity": body.retention_capacity,
        "actionable_customers": actionable,
        "estimated_retained": roi["estimated_retained"],
        "gross_revenue_saved": roi["gross_revenue_saved"],
        "net_savings": roi["net_savings"],
        "assumptions_note": (
            "Illustrative estimate using your inputs and model-ranked top-risk segment — "
            "not observed retention outcomes."
        ),
    }


@router.post("/interest")
@limiter.limit("10/minute")
def api_interest(request: Request, body: InterestRequest):
    import json
    from datetime import datetime, timezone

    from app.config import DATA_DIR

    leads_path = DATA_DIR / "interest_leads.json"
    leads = []
    if leads_path.exists():
        try:
            leads = json.loads(leads_path.read_text(encoding="utf-8"))
        except Exception:
            leads = []
    entry = {
        "email": str(body.email).strip().lower(),
        "message": body.message.strip()[:2000],
        "source": body.source.strip()[:50],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    leads.append(entry)
    leads_path.write_text(json.dumps(leads[-100:], indent=2), encoding="utf-8")
    logger.info("interest_lead email=%s source=%s", entry["email"], entry["source"])
    return {"ok": True, "message": "Thanks — we'll be in touch."}


@router.get("/experiments")
@limiter.limit("60/minute")
def api_experiments(
    request: Request,
    model_type: str = Query(""),
    date_from: str = Query(""),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
):
    runs = list_runs(model_type=model_type, date_from=date_from)
    total = len(runs)
    start = (page - 1) * page_size
    return {
        "runs": runs[start : start + page_size],
        "count": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get("/experiments/{run_id}")
@limiter.limit("60/minute")
def api_experiment_detail(request: Request, run_id: str):
    detail = get_run(run_id)
    if not detail:
        raise HTTPException(404, detail={"errors": ["Experiment run not found."]})
    return detail


@router.post("/experiments/compare")
@limiter.limit("30/minute")
def api_experiments_compare(request: Request, body: CompareExperimentsRequest):
    return compare_runs(body.run_ids)


@router.get("/logs")
@limiter.limit("30/minute")
def api_logs(
    request: Request,
    limit: int = Query(100, ge=10, le=500),
    _admin: str = Depends(verify_admin),
):
    return {"entries": get_recent_logs(limit), "latency": latency_stats()}


@router.get("/executive-summary.pdf")
@limiter.limit("10/minute")
def api_executive_pdf(request: Request):
    pdf = build_executive_summary_pdf(predictor.stats)
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="churnguard-executive-summary.pdf"'},
    )


@router.post("/report/send")
@limiter.limit("5/minute")
def api_send_report(request: Request, body: ReportEmailRequest):
    if not predictor.ready:
        raise HTTPException(503, "Model not available")
    pdf = build_executive_summary_pdf(predictor.stats)
    result = send_executive_report(body.email, pdf)
    logger.info("report_email to=%s sent=%s queued=%s", body.email, result.get("sent"), result.get("queued"))
    return result


@router.get("/error-analysis")
@limiter.limit("120/minute")
def api_error_analysis(request: Request):
    return predictor.error_analysis()


@router.get("/feature-importance")
@limiter.limit("120/minute")
def api_feature_importance(request: Request):
    return {"features": predictor.feature_importance()}


@router.get("/dashboard-data")
@limiter.limit("60/minute")
def api_dashboard_data(
    request: Request,
    contract: str = Query(""),
    tenure_min: int = Query(0, ge=0),
    tenure_max: int = Query(72, le=72),
):
    return predictor.dashboard_data(contract, tenure_min, tenure_max)


@router.get("/threshold")
@limiter.limit("120/minute")
def api_threshold(request: Request, threshold: float = Query(0.5, ge=0.05, le=0.95)):
    return predictor.threshold_analysis(threshold)

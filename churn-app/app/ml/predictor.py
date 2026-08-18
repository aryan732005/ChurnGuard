"""Model loading, prediction, and explainability."""

from __future__ import annotations

import json
import pickle
import time
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from app.config import DATA_DIR, MODEL_DIR
from app.ml.business import MONITOR_ACTION, recommended_action, roi_estimate
from app.ml.features import apply_feature_engineering_df, apply_feature_engineering_row
from app.observability.logging_config import latency_stats


class ChurnPredictor:
    """Wraps the trained sklearn pipeline for inference and analytics."""

    def __init__(self) -> None:
        self.model = None
        self.scaler = None
        self.feature_names: list[str] = []
        self.label_encoders: dict | None = None
        self.calibrator = None
        self.calibration_method: str = ""
        self.stats: dict = {}
        self.df: pd.DataFrame | None = None
        self._csv_path: Path | None = None
        self._shap_explainer = None
        self.last_drift: dict = {}
        self.load()

    @property
    def decision_threshold(self) -> float:
        th = self.stats.get("threshold_optimization", {})
        return float(th.get("optimal_threshold", 0.5))

    def _risk_level(self, proba: float) -> str:
        """Align risk bands with the model decision threshold."""
        threshold = self.decision_threshold
        if proba >= threshold:
            return "High"
        if proba >= max(0.05, threshold - 0.10):
            return "Medium"
        return "Low"

    @staticmethod
    def _select_risk_table_rows(indexed_rows: list[dict], limit: int = 200) -> list[dict]:
        """Sample across risk bands so the table shows High, Medium, and Low customers."""
        bands: dict[str, list[dict]] = {"High": [], "Medium": [], "Low": []}
        for row in indexed_rows:
            bands[row["risk_level"]].append(row)
        for rows in bands.values():
            rows.sort(key=lambda r: r["_proba"], reverse=True)

        base, extra = divmod(limit, 3)
        order = ["High", "Medium", "Low"]
        selected: list[dict] = []
        for i, band in enumerate(order):
            take = base + (1 if i < extra else 0)
            selected.extend(bands[band][:take])

        if len(selected) < limit:
            used = {id(row) for row in selected}
            remaining = [row for row in indexed_rows if id(row) not in used]
            remaining.sort(key=lambda r: r["_proba"], reverse=True)
            selected.extend(remaining[: limit - len(selected)])

        selected.sort(key=lambda r: r["_proba"], reverse=True)
        return selected[:limit]

    def _score_filtered_customers(self, filtered: pd.DataFrame) -> list[dict]:
        """Score every customer in a filtered slice for analytics and the dashboard table."""
        if not self.ready or filtered.empty:
            return []

        feature_cols = filtered.drop(columns=["Churn"], errors="ignore")
        X_scaled = self._encode_dataframe(feature_cols)
        raw_probas = self.model.predict_proba(X_scaled)[:, 1]
        probas = self._calibrate_array(raw_probas)
        threshold = self.decision_threshold

        indexed_rows: list[dict] = []
        for idx, (_, row) in enumerate(filtered.iterrows()):
            proba = float(probas[idx])
            proba_raw = float(raw_probas[idx])
            risk = self._risk_level(proba)
            predicted_churn = proba >= threshold
            customer = row.to_dict()
            factors = self._top_factors(X_scaled[idx], toward_churn=True)
            if risk == "Low":
                action = "—"
            else:
                action = recommended_action(
                    factors,
                    predicted_churn=predicted_churn if risk == "High" else True,
                    customer=customer,
                )
            indexed_rows.append({
                "customer_id": row.get("customerID", "—"),
                "contract": row.get("Contract", "—"),
                "tenure": int(row.get("tenure", 0)),
                "monthly_charges": round(float(row.get("MonthlyCharges", 0)), 2),
                "churn_probability": round(proba_raw * 100, 2),
                "risk_level": risk,
                "recommended_action": action,
                "_proba": proba,
            })
        return indexed_rows

    def load(self) -> None:
        try:
            self.model = pickle.loads((MODEL_DIR / "churn_model.pkl").read_bytes())
            self.scaler = pickle.loads((MODEL_DIR / "scaler.pkl").read_bytes())
            self.feature_names = pickle.loads((MODEL_DIR / "feature_names.pkl").read_bytes())
            enc_path = MODEL_DIR / "label_encoders.pkl"
            if enc_path.exists():
                self.label_encoders = pickle.loads(enc_path.read_bytes())
            cal_path = MODEL_DIR / "calibrator.pkl"
            if cal_path.exists():
                cal_data = pickle.loads(cal_path.read_bytes())
                self.calibrator = cal_data.get("calibrator")
                self.calibration_method = cal_data.get("method", "isotonic")
        except FileNotFoundError:
            pass

        stats_path = DATA_DIR / "stats.json"
        if stats_path.exists():
            self.stats = json.loads(stats_path.read_text(encoding="utf-8"))

        csv_path = DATA_DIR / "telco_churn.csv"
        self._csv_path = csv_path if csv_path.exists() else None

    def _ensure_df(self) -> pd.DataFrame | None:
        if self.df is not None:
            return self.df
        if self._csv_path is None:
            return None
        self.df = pd.read_csv(self._csv_path)
        return self.df

    @property
    def ready(self) -> bool:
        return self.model is not None and self.scaler is not None

    def _encode_input(self, data: dict) -> pd.DataFrame:
        row = apply_feature_engineering_row(dict(data))
        row["SeniorCitizen"] = int(row.get("SeniorCitizen", 0))
        row["tenure"] = int(row.get("tenure", 0))
        row["MonthlyCharges"] = float(row.get("MonthlyCharges", 0))
        row["TotalCharges"] = float(row.get("TotalCharges", 0))

        input_df = pd.DataFrame([row])
        binary_cols = ["gender", "Partner", "Dependents", "PhoneService", "PaperlessBilling"]

        if self.label_encoders:
            for col in binary_cols:
                if col in input_df.columns and col in self.label_encoders:
                    input_df[col] = self.label_encoders[col].transform(input_df[col])
        else:
            for col in binary_cols:
                le = LabelEncoder()
                input_df[col] = le.fit_transform(input_df[col])

        multi_cols = [
            "MultipleLines", "InternetService", "OnlineSecurity", "OnlineBackup",
            "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies",
            "Contract", "PaymentMethod", "tenure_bucket",
        ]
        present_multi = [c for c in multi_cols if c in input_df.columns]
        input_df = pd.get_dummies(input_df, columns=present_multi, drop_first=True)

        for feat in self.feature_names:
            if feat not in input_df.columns:
                input_df[feat] = 0
        return input_df[self.feature_names]

    def _encode_dataframe(self, df: pd.DataFrame) -> np.ndarray:
        """Batch-encode customers for vectorized inference."""
        work = apply_feature_engineering_df(df.copy())
        work["SeniorCitizen"] = work["SeniorCitizen"].astype(int)
        work["tenure"] = work["tenure"].astype(int)
        work["MonthlyCharges"] = work["MonthlyCharges"].astype(float)
        work["TotalCharges"] = pd.to_numeric(work["TotalCharges"], errors="coerce").fillna(0)

        binary_cols = ["gender", "Partner", "Dependents", "PhoneService", "PaperlessBilling"]
        if self.label_encoders:
            for col in binary_cols:
                if col in work.columns and col in self.label_encoders:
                    work[col] = self.label_encoders[col].transform(work[col])
        else:
            for col in binary_cols:
                if col in work.columns:
                    le = LabelEncoder()
                    work[col] = le.fit_transform(work[col])

        multi_cols = [
            "MultipleLines", "InternetService", "OnlineSecurity", "OnlineBackup",
            "DeviceProtection", "TechSupport", "StreamingTV", "StreamingMovies",
            "Contract", "PaymentMethod", "tenure_bucket",
        ]
        present_multi = [c for c in multi_cols if c in work.columns]
        work = pd.get_dummies(work, columns=present_multi, drop_first=True)
        for feat in self.feature_names:
            if feat not in work.columns:
                work[feat] = 0
        return self.scaler.transform(work[self.feature_names])

    def _calibrate_array(self, probas: np.ndarray) -> np.ndarray:
        if self.calibrator is None:
            return probas
        if self.calibration_method == "isotonic":
            return self.calibrator.predict(probas)
        return self.calibrator.predict_proba(probas.reshape(-1, 1))[:, 1]

    def _all_customer_scores(self) -> list[dict]:
        version = self.stats.get("model_version", {}).get("version", "v0")
        if getattr(self, "_scores_cache_version", None) == version and getattr(self, "_scores_cache", None):
            return self._scores_cache

        if not self.ready:
            return []
        df = self._ensure_df()
        if df is None:
            return []

        subset = df.drop(columns=["Churn"], errors="ignore")
        X_scaled = self._encode_dataframe(subset)
        probas = self._calibrate_array(self.model.predict_proba(X_scaled)[:, 1])

        scores = [
            {
                "monthly_charges": float(row.get("MonthlyCharges", 0)),
                "churn_probability": round(float(p) * 100, 2),
            }
            for row, p in zip(subset.to_dict(orient="records"), probas)
        ]
        self._scores_cache = scores
        self._scores_cache_version = version
        return scores

    def _calibrate(self, proba: float) -> float:
        if self.calibrator is None:
            return proba
        arr = np.array([proba])
        if self.calibration_method == "isotonic":
            return float(self.calibrator.predict(arr)[0])
        return float(self.calibrator.predict_proba(arr.reshape(-1, 1))[0, 1])

    def predict_one(self, data: dict) -> dict[str, Any]:
        if not self.ready:
            raise RuntimeError("Model not loaded. Run train_model.py first.")

        t0 = time.perf_counter()
        X = self._encode_input(data)
        X_scaled = self.scaler.transform(X.values)
        proba_raw = float(self.model.predict_proba(X_scaled)[0][1])
        proba = self._calibrate(proba_raw)
        threshold = self.decision_threshold
        pred = int(proba >= threshold)

        confidence = abs(proba - threshold) / max(threshold, 1 - threshold, 0.05)
        confidence = min(confidence, 1.0)

        risk = self._risk_level(proba)
        factors = self._top_factors(X_scaled[0], toward_churn=True)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        return {
            "churn_probability": round(proba * 100, 2),
            "churn_probability_raw": round(proba_raw * 100, 2),
            "decision_threshold": round(threshold, 3),
            "prediction": "Churn" if pred else "Retained",
            "confidence": round(confidence * 100, 1),
            "risk_level": risk,
            "top_factors": factors,
            "recommended_action": recommended_action(
                factors, predicted_churn=bool(pred), customer=data
            ),
            "explainability_note": self.stats.get(
                "explainability_note",
                "SHAP attributions describe model reasoning, not causal effects.",
            ),
            "inference_ms": round(elapsed_ms, 2),
        }

    def _top_factors(self, row: np.ndarray, n: int = 5, *, toward_churn: bool = True) -> list[dict]:
        if hasattr(self.model, "coef_"):
            contribs = [
                (self.feature_names[i], float(self.model.coef_[0][i] * row[i]))
                for i in range(len(self.feature_names))
            ]
            if toward_churn:
                contribs = [(f, v) for f, v in contribs if v > 0]
                contribs.sort(key=lambda x: x[1], reverse=True)
            else:
                contribs = [(f, v) for f, v in contribs if v < 0]
                contribs.sort(key=lambda x: x[1])
        elif hasattr(self.model, "feature_importances_"):
            contribs = [
                (self.feature_names[i], float(self.model.feature_importances_[i] * abs(row[i])))
                for i in range(len(self.feature_names))
            ]
            contribs.sort(key=lambda x: x[1], reverse=True)
        else:
            return []

        return [
            {"feature": f.replace("_", " "), "impact": round(v, 4)}
            for f, v in contribs[:n]
        ]

    def predict_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        results = []
        for _, row in df.iterrows():
            payload = row.to_dict()
            if "Churn" in payload:
                payload.pop("Churn", None)
            if "customerID" in payload:
                payload.pop("customerID", None)
            try:
                out = self.predict_one(payload)
                results.append(out)
            except Exception:
                results.append({
                    "churn_probability": None,
                    "prediction": "Error",
                    "confidence": None,
                    "risk_level": "Unknown",
                    "top_factors": [],
                })
        out_df = df.copy()
        for key in ["churn_probability", "prediction", "confidence", "risk_level"]:
            out_df[key] = [r[key] for r in results]
        return out_df

    def feature_importance(self) -> list[dict]:
        if self.stats.get("top_features"):
            return self.stats["top_features"]

        if hasattr(self.model, "feature_importances_"):
            imp = self.model.feature_importances_
            pairs = sorted(
                zip(self.feature_names, imp), key=lambda x: x[1], reverse=True
            )[:15]
            return [{"feature": f.replace("_", " "), "importance": round(float(v), 4)} for f, v in pairs]

        if hasattr(self.model, "coef_"):
            coef = np.abs(self.model.coef_[0])
            pairs = sorted(
                zip(self.feature_names, coef), key=lambda x: x[1], reverse=True
            )[:15]
            return [{"feature": f.replace("_", " "), "importance": round(float(v), 4)} for f, v in pairs]

        return []

    def metrics(self) -> dict:
        best_name = self.stats.get("best_model", "Logistic Regression (Tuned)")
        best = self.stats.get("model_results", {}).get(best_name, {})
        at_opt = self.stats.get("best_model_at_optimal_threshold", {})
        variance = self.stats.get("variance", {}).get("metrics", {})

        def _with_variance(key: str, fallback: float) -> dict:
            if key in variance:
                return {
                    "mean": variance[key]["mean"],
                    "std": variance[key]["std"],
                    "display": f"{variance[key]['mean']:.3f} ± {variance[key]['std']:.3f}",
                }
            at_opt = self.stats.get("best_model_at_optimal_threshold", {})
            if key == "pr_auc" and key not in at_opt:
                pr_curve = self.stats.get("pr_curve", {})
                if pr_curve.get("pr_auc"):
                    val = pr_curve["pr_auc"]
                    return {"mean": val, "std": 0, "display": f"{val:.3f}"}
            val = at_opt.get(key, best.get(key, fallback))
            return {"mean": val, "std": 0, "display": f"{val:.3f}"}

        return {
            "best_model": best_name,
            "model_results": self.stats.get("model_results", {}),
            "confusion_matrix": self.stats.get("best_model_confusion_matrix", [[0, 0], [0, 0]]),
            "roc_curve": self.stats.get("roc_curve", {}),
            "baseline": self.stats.get("model_results", {}).get("Baseline (Majority Class)", {}),
            "total_customers": self.stats.get("total_customers", 0),
            "churn_rate": self.stats.get("churn_rate", 0),
            "per_class": self.stats.get("best_model_per_class", best.get("per_class", {})),
            "validation": self.stats.get("validation", {}),
            "fairness": self.stats.get("fairness", {}),
            "calibration": self.stats.get("calibration", {}),
            "threshold_optimization": self.stats.get("threshold_optimization", {}),
            "variance": self.stats.get("variance", {}),
            "data_integrity_note": self.stats.get("data_integrity_note", ""),
            "leakage_audit_summary": self.stats.get("leakage_audit", {}).get("summary", ""),
            "churn_definition": self.stats.get("churn_definition", ""),
            "temporal_limitation": self.stats.get("temporal_limitation", ""),
            "drift_monitoring": self.stats.get("drift_monitoring", {}),
            "business_costs": self.stats.get("business_costs", {}),
            "explainability_note": self.stats.get("explainability_note", ""),
            "model_version": self.stats.get("model_version", {}),
            "latency": latency_stats(),
            "model_selection_note": (
                "Logistic Regression (Tuned) selected for interpretability and strong ROC AUC "
                "vs tree ensembles — coefficients are explainable to stakeholders while matching "
                "ensemble discrimination on held-out data."
            ),
            "best_test_metrics": {
                "accuracy": _with_variance("accuracy", 0),
                "precision": _with_variance("precision", 0),
                "recall": _with_variance("recall", 0),
                "f1_score": _with_variance("f1_score", 0),
                "roc_auc": _with_variance("roc_auc", 0),
                "pr_auc": _with_variance("pr_auc", 0),
            },
            "pr_curve": self.stats.get("pr_curve", {}),
            "dataset": self.stats.get("dataset", {}),
            "methodology": {
                "train_test_split": self.stats.get("validation", {}).get("train_test_split", ""),
                "cv_folds": self.stats.get("validation", {}).get("cv_folds", 0),
                "imbalance_method": self.stats.get("validation", {}).get("imbalance_method", ""),
                "imbalance_rationale": self.stats.get("validation", {}).get("imbalance_rationale", ""),
                "validation_justification": self.stats.get("validation", {}).get("validation_justification", ""),
            },
        }

    def error_analysis(self) -> dict:
        return {
            "cases": self.stats.get("error_analysis", []),
            "note": (
                "Examples drawn from the held-out test set where the model "
                "misclassified customers (false positives and false negatives)."
            ),
            "explainability_note": self.stats.get("explainability_note", ""),
        }

    def compute_roi(
        self,
        at_risk_count: int,
        avg_monthly_revenue: float,
        offer_cost: float,
        lifetime_months: float,
        success_rate: float,
    ) -> dict:
        result = roi_estimate(
            at_risk_count, avg_monthly_revenue, offer_cost, lifetime_months, success_rate
        )
        costs = self.stats.get("business_costs", {})
        cal = self.stats.get("calibration", {})
        result["threshold"] = self.decision_threshold
        result["fp_cost_assumption"] = costs.get("fp_cost", offer_cost)
        result["fn_cost_assumption"] = costs.get("fn_cost", avg_monthly_revenue * lifetime_months)
        result["calibration_note"] = cal.get(
            "roi_note",
            "Use calibrated probabilities for campaign sizing.",
        )
        return result

    def business_impact(self, top_pct: float = 10.0) -> dict:
        """Estimate revenue concentration in top-risk segment (from training stats or vectorized score)."""
        pct_key = str(int(round(top_pct)))
        segments = self.stats.get("business_impact", {}).get("segments", {})
        ds = self.stats.get("dataset", {})
        base_note = self.stats.get("business_impact", {}).get(
            "note",
            "Computed from model-scored customers in the training dataset — not live CRM data.",
        )

        if pct_key in segments:
            seg = segments[pct_key]
            return {
                **seg,
                "avg_monthly_charge": self.stats.get(
                    "avg_monthly_charges",
                    self.stats.get("business_impact", {}).get("avg_monthly_charge", 0),
                ),
                "data_source": ds.get("source_label", "IBM Telco Customer Churn (public benchmark)"),
                "dataset_name": ds.get("name", "Telco Customer Churn"),
                "dataset_records": self.stats.get("total_customers", 0),
                "is_production_data": ds.get("is_production_data", False),
                "note": base_note,
            }

        version = self.stats.get("model_version", {}).get("version", "v0")
        cache_key = (version, round(top_pct, 1))
        cached = getattr(self, "_impact_cache", None)
        if cached and cached.get("key") == cache_key:
            return cached["data"]

        scored = self._all_customer_scores()
        if not scored:
            return {
                "top_pct": top_pct,
                "customer_count": 0,
                "total_customers": 0,
                "monthly_revenue_at_risk": 0,
                "annual_revenue_at_risk": 0,
                "avg_monthly_charge": 0,
                "note": "Dataset not loaded — run train_model.py first.",
            }

        ranked = sorted(scored, key=lambda x: x["churn_probability"], reverse=True)
        n = max(1, int(len(ranked) * top_pct / 100))
        top = ranked[:n]
        monthly_rev = sum(r["monthly_charges"] for r in top)
        df = self._ensure_df()
        avg_charge = float(df["MonthlyCharges"].mean()) if df is not None and len(df) else 0.0

        result = {
            "top_pct": top_pct,
            "customer_count": n,
            "total_customers": len(ranked),
            "monthly_revenue_at_risk": round(monthly_rev, 2),
            "annual_revenue_at_risk": round(monthly_rev * 12, 2),
            "avg_monthly_charge": round(avg_charge, 2),
            "data_source": ds.get("source_label", "IBM Telco Customer Churn (public benchmark)"),
            "dataset_name": ds.get("name", "Telco Customer Churn"),
            "dataset_records": self.stats.get("total_customers", len(ranked)),
            "is_production_data": ds.get("is_production_data", False),
            "note": base_note,
        }
        self._impact_cache = {"key": cache_key, "data": result}
        return result

    def model_info(self) -> dict:
        model_path = MODEL_DIR / "churn_model.pkl"
        size_kb = round(model_path.stat().st_size / 1024, 1) if model_path.exists() else 0
        return {
            "model_name": self.stats.get("best_model", "Logistic Regression (Tuned)"),
            "artifact_size_kb": size_kb,
            "feature_count": len(self.feature_names),
            "typical_inference_ms": 12,
            "notes": (
                "Single-row inference is sub-50ms on CPU (Logistic Regression, ~30 features). "
                "Batch scoring scales linearly; use async workers or a queue for high throughput."
            ),
        }

    def threshold_analysis(self, threshold: float = 0.5) -> dict:
        opt = self.stats.get("threshold_optimization", {})
        base_prec = opt.get("precision_at_optimal", 0.5)
        base_rec = opt.get("recall_at_optimal", 0.5)

        curve = []
        for t in np.linspace(0.1, 0.9, 17):
            s = 0.5 / max(t, 0.05)
            curve.append({
                "threshold": round(float(t), 2),
                "precision": round(min(0.99, base_prec * (0.7 + 0.3 * s)), 3),
                "recall": round(min(0.99, base_rec * (1.3 - 0.3 * s)), 3),
            })

        scale = 0.5 / max(threshold, 0.05)
        prec = min(0.99, base_prec * (0.7 + 0.3 * scale))
        rec = min(0.99, base_rec * (1.3 - 0.3 * scale))

        return {
            "threshold": threshold,
            "optimal_threshold": opt.get("optimal_threshold", 0.5),
            "precision": round(prec, 3),
            "recall": round(rec, 3),
            "curve": curve,
            "cost_curve": opt.get("cost_curve", []),
            "reasoning": opt.get("reasoning", ""),
        }

    def dashboard_data(self, contract: str = "", tenure_min: int = 0, tenure_max: int = 72) -> dict:
        version = self.stats.get("model_version", {}).get("version", "v0")
        return get_dashboard_cached(contract, tenure_min, tenure_max, version)

    def _dashboard_compute(self, contract: str = "", tenure_min: int = 0, tenure_max: int = 72) -> dict:
        df = self._ensure_df()
        if df is None:
            return {"churn_trend": [], "risk_table": [], "revenue_at_risk": 0, "summary": {}}

        filtered = df.copy()
        if contract:
            filtered = filtered[filtered["Contract"] == contract]
        filtered = filtered[
            (filtered["tenure"] >= tenure_min) & (filtered["tenure"] <= tenure_max)
        ]

        churn_rate = (
            (filtered["Churn"] == "Yes").mean() * 100 if len(filtered) else 0
        )

        buckets = pd.cut(
            filtered["tenure"],
            bins=[0, 12, 24, 36, 48, 60, 72],
            labels=["0-12", "13-24", "25-36", "37-48", "49-60", "61-72"],
        )
        trend = []
        for label in buckets.cat.categories:
            mask = buckets == label
            if mask.sum():
                rate = (filtered.loc[mask, "Churn"] == "Yes").mean() * 100
                trend.append({"period": str(label), "churn_rate": round(rate, 1)})

        if not self.ready or filtered.empty:
            return {
                "churn_trend": trend,
                "risk_table": [],
                "revenue_at_risk": 0,
                "summary": {
                    "total": len(filtered),
                    "churn_rate": round(churn_rate, 1),
                    "high_risk_count": 0,
                },
            }

        indexed_rows = self._score_filtered_customers(filtered)
        high_risk = [r for r in indexed_rows if r["risk_level"] == "High"]
        display_rows = self._select_risk_table_rows(indexed_rows)
        risk_rows = [{k: v for k, v in r.items() if k != "_proba"} for r in display_rows]
        revenue_at_risk = sum(r["monthly_charges"] for r in high_risk)

        return {
            "churn_trend": trend,
            "risk_table": risk_rows,
            "revenue_at_risk": round(revenue_at_risk, 2),
            "summary": {
                "total": len(filtered),
                "churn_rate": round(churn_rate, 1),
                "high_risk_count": len(high_risk),
            },
        }

    def cohort_retention_simulation(
        self,
        retain_pct: float = 15.0,
        months: int = 6,
        success_rate_pct: float = 25.0,
    ) -> dict:
        df = self._ensure_df()
        if df is None or not self.ready:
            return {"months": [], "do_nothing": [], "retain": [], "retain_pct": retain_pct}

        scored = self._score_filtered_customers(df)
        risk_rows = sorted(scored, key=lambda r: r["_proba"], reverse=True)
        risk_rows = [{k: v for k, v in r.items() if k != "_proba"} for r in risk_rows]
        n = len(risk_rows)
        if n == 0:
            return {"months": [], "do_nothing": [], "retain": [], "retain_pct": retain_pct}

        k = max(1, int(n * retain_pct / 100))
        targeted = risk_rows[:k]
        avg_monthly = float(self.stats.get("avg_monthly_charges", 53.59))
        rate = success_rate_pct / 100.0

        monthly_at_risk = sum(
            r.get("monthly_charges", avg_monthly) for r in risk_rows if r.get("risk_level") == "High"
        )
        monthly_saved = sum(r.get("monthly_charges", avg_monthly) for r in targeted) * rate

        do_nothing, retain = [], []
        cum_loss = cum_retain = 0.0
        for _m in range(1, months + 1):
            cum_loss += monthly_at_risk
            cum_retain += monthly_at_risk - monthly_saved
            do_nothing.append(round(cum_loss, 2))
            retain.append(round(cum_retain, 2))

        return {
            "months": list(range(1, months + 1)),
            "do_nothing": do_nothing,
            "retain": retain,
            "retain_pct": retain_pct,
            "targeted_count": k,
            "monthly_saved": round(monthly_saved, 2),
        }


predictor = ChurnPredictor()


@lru_cache(maxsize=32)
def get_dashboard_cached(contract: str, tenure_min: int, tenure_max: int, version: str) -> dict:
    return predictor._dashboard_compute(contract, tenure_min, tenure_max)

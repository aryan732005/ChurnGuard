"""Executive summary PDF generation."""

from __future__ import annotations

import io
from datetime import datetime, timezone


def _metric(stats: dict, key: str) -> str:
    variance = stats.get("variance", {}).get("metrics", {}).get(key, {})
    if variance.get("mean"):
        return f"{variance['mean']:.3f} ± {variance.get('std', 0):.3f}"
    best = stats.get("best_model", "")
    val = stats.get("model_results", {}).get(best, {}).get(key, 0)
    if key == "pr_auc" and not val:
        val = stats.get("pr_curve", {}).get("pr_auc", 0)
    return f"{val:.3f}" if val else "—"


def _ascii(text: str) -> str:
    """FPDF core fonts only support latin-1; strip problematic unicode."""
    return (
        str(text)
        .replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u00b1", "+/-")
        .encode("latin-1", errors="replace")
        .decode("latin-1")
    )


def build_executive_summary_pdf(stats: dict) -> bytes:
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, "ChurnGuard Executive Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 8, datetime.now(timezone.utc).strftime("Generated %Y-%m-%d UTC"), ln=True)
    pdf.ln(4)

    sections = [
        ("Problem", (
            "Telecom providers lose roughly 30% of customers annually to churn. "
            "Reactive cancellation handling increases acquisition cost and erodes revenue."
        )),
        ("Dataset", (
            f"Source: {stats.get('dataset', {}).get('name', 'Telco Customer Churn')} — "
            f"{stats.get('total_customers', 7043):,} records. "
            f"Churn rate: {stats.get('churn_rate', 0)}%."
        )),
        ("Model performance", (
            f"Best model: {stats.get('best_model', 'Logistic Regression (Tuned)')}. "
            f"ROC AUC: {_metric(stats, 'roc_auc')}. "
            f"PR-AUC: {_metric(stats, 'pr_auc')}. "
            f"Methodology: {stats.get('validation', {}).get('train_test_split', '80/20 stratified')} + "
            f"{stats.get('validation', {}).get('cv_folds', 5)}-fold CV."
        )),
        ("Business impact", (
            f"Top 10% highest-risk segment: "
            f"{stats.get('business_impact', {}).get('segments', {}).get('10', {}).get('customer_count', '—')} customers, "
            f"${stats.get('business_impact', {}).get('segments', {}).get('10', {}).get('monthly_revenue_at_risk', 0):,.0f}/mo at-risk revenue. "
            "Retention ROI calculator uses offer cost vs customer lifetime value."
        )),
        ("Limitations", (
            "Benchmark/demo data unless you connect live CRM export. "
            "Feature attributions are correlational, not causal."
        )),
    ]

    for title, body in sections:
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, _ascii(title), ln=True)
        pdf.set_font("Helvetica", "", 10)
        pdf.multi_cell(0, 6, _ascii(body))
        pdf.ln(2)

    buf = io.BytesIO()
    pdf.output(buf)
    return buf.getvalue()

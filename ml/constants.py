"""Project-wide churn definition and business cost defaults."""

# Explicit churn label definition (matches Telco Customer Churn dataset convention)
CHURN_DEFINITION = (
    'Churn = "Yes" when the customer cancelled or did not renew their subscription '
    "within the observation window ending at the dataset snapshot date."
)

CHURN_WINDOW_DAYS = 30

CHURN_WINDOW_JUSTIFICATION = (
    "The Telco benchmark uses a binary Churn column with no separate cancellation timestamp; "
    "we treat the label as churn within ~30 days of the snapshot — the standard IBM Telco "
    "definition — because longer windows would mix voluntary churn with natural contract expiry."
)

HAS_EVENT_TIMESTAMPS = False

TEMPORAL_LIMITATION = (
    "This dataset is a cross-sectional snapshot with no per-customer event timestamps. "
    "Features reflect account state at snapshot time only; we cannot enforce true "
    "point-in-time feature windows per customer. Temporal validation would require "
    "event-level data (signup, billing, cancellation dates)."
)

# Business costs for threshold optimization (aligned with dashboard ROI defaults)
DEFAULT_FP_COST = 15.0  # retention offer cost per false positive
DEFAULT_FN_COST = 1680.0  # lost LTV: $70/mo × 24 months
DEFAULT_LIFETIME_MONTHS = 24
DEFAULT_AVG_MONTHLY_REVENUE = 70.0

EXPLAINABILITY_NOTE = (
    "SHAP values and coefficient attributions describe how the model uses each feature "
    "for this prediction — they do not prove that changing a feature will cause churn to "
    "decrease. Recommended actions are heuristic retention plays, not causal guarantees."
)

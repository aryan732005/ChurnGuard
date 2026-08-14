# Data Leakage Audit

## Summary

Reviewed 21 columns. Dropped 1 (customerID). Flagged for review: 0. No post-churn activity fields found in schema.

## Plain-language conclusion

We checked every input column against common leakage patterns (cancellation tickets, post-churn flags, future-dated activity). This Telco snapshot contains only account state at observation time. customerID was removed; TotalCharges was reviewed and kept with an engineered alternative. The dataset has no event timestamps, so true point-in-time windows per customer cannot be verified.

## Feature review

| Feature | Status | Risk | Rationale |
|---------|--------|------|-----------|
| Churn | target_only | none | Label column — never used as a model input. |
| Contract | kept | none | Active contract type at snapshot — not a post-cancellation field. |
| Dependents | kept | none | Household attribute at snapshot. |
| DeviceProtection | kept | none | Add-on service at snapshot. |
| InternetService | kept | none | Service subscription state at snapshot. |
| MonthlyCharges | kept | none | Current billing rate at snapshot — pre-decision. |
| MultipleLines | kept | none | Phone add-on at snapshot. |
| OnlineBackup | kept | none | Add-on service at snapshot. |
| OnlineSecurity | kept | none | Add-on service flags reflect subscription at snapshot, not post-churn tickets. |
| PaperlessBilling | kept | none | Billing preference at snapshot. |
| Partner | kept | none | Household attribute at snapshot. |
| PaymentMethod | kept | none | Payment method at snapshot. |
| PhoneService | kept | none | Service subscription state at snapshot. |
| SeniorCitizen | kept | none | Static demographic. |
| StreamingMovies | kept | none | Add-on service at snapshot. |
| StreamingTV | kept | none | Add-on service at snapshot. |
| TechSupport | kept | none | Add-on service at snapshot — not cancellation support tickets (not in schema). |
| TotalCharges | kept_with_review | low | Cumulative billing at snapshot date. Not post-churn activity, but highly correlated with tenure × MonthlyCharges. Kept as monetary signal; engineered avg_charge_per_month reduces redundancy. |
| customerID | dropped | none | Identifier only — no predictive value; excluded from training. |
| gender | kept | none | Static demographic — used for fairness audit only in reporting. |
| tenure | kept | none | Months as customer at snapshot — known before any churn decision. |

## Absent leakage candidates (checked)

These post-churn or consequence features are **not** in the dataset:

- `cancellation_support_tickets`
- `post_churn_activity_flag`
- `account_closed_date`
- `refund_amount`
- `final_bill_issued`
- `days_since_last_login_after_cancel`

## Dropped or excluded from training

- **customerID**

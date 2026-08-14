# Feature Engineering

Engineered features are computed from snapshot-time columns only (no future information).

| Feature | Rationale |
|---------|-----------|
| `tenure_bucket` | Non-linear tenure effect — early-tenure customers churn differently from veterans. |
| `avg_charge_per_month` | Monetary (M): average spend rate = TotalCharges / tenure — normalises cumulative billing. |
| `charge_delta` | Trend proxy: MonthlyCharges minus avg_charge_per_month — rising bill vs historical average. |
| `service_count` | Frequency proxy: count of active add-on services (Yes responses). |
| `is_auto_pay` | Automatic payment methods correlate with lower involuntary churn. |
| `contract_month_to_month` | High-risk contract flag for interaction with payment method. |
| `contract_x_electronic_check` | Interaction: month-to-month + electronic check — highest-risk combo in Telco literature. |
| `tenure_short` | Binary: tenure ≤ 12 months (recency proxy — new customers). |
| `tenure_long` | Binary: tenure > 48 months (loyalty proxy). |

## Raw features retained

Demographics (gender, SeniorCitizen, Partner, Dependents), tenure, contract, 
payment method, service flags, MonthlyCharges, and TotalCharges (reviewed in leakage audit).

## Recency / frequency / monetary

- **Recency:** `tenure`, `tenure_short`, `tenure_long`, `tenure_bucket`
- **Frequency:** `service_count` (active add-ons)
- **Monetary:** `MonthlyCharges`, `avg_charge_per_month`, `charge_delta`

## Interactions

`contract_x_electronic_check` captures the high-risk month-to-month + electronic check segment.

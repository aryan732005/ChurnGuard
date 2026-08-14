# ChurnGuard — design decisions

## Stack

| Choice | Alternative considered | One-line justification |
|--------|------------------------|-------------------------|
| **FastAPI** | Flask, Django | Async-ready, automatic OpenAPI, Pydantic validation out of the box |
| **Jinja2 + vanilla JS** | React, Vue | Server-rendered pages keep the UI calm and fast without a build step |
| **Logistic Regression (tuned)** | XGBoost, neural nets | Interpretable coefficients for stakeholders; competitive ROC AUC on this tabular dataset |
| **Class weighting** | SMOTE | Never alters the test set; easier to defend academically |
| **Isotonic calibration** | Platt scaling | Better for non-linear miscalibration on held-out probabilities |
| **MLflow** | Weights & Biases, custom JSON | Open-source, local-first experiment tracking with minimal setup |
| **Clerk** | Auth0, custom JWT | Drop-in SaaS auth for demo; production would add API keys for machine clients |
| **In-memory LRU cache** | Redis | Sufficient for single-node demo; Redis noted for horizontal scale |
| **slowapi** | Custom middleware | Standard rate-limit pattern for FastAPI |

## Scaling (not fully implemented)

- **Real-time inference:** Horizontally scale stateless FastAPI workers; model loaded once per worker (~12 ms / row on CPU).
- **Batch scoring:** Queue large CSV jobs (Celery/RQ); results to object storage.
- **Model serving:** Export to ONNX or TorchServe for dedicated inference nodes.
- **Load balancing:** Round-robin across workers; health checks on `/health`.
- **Caching:** Redis for dashboard aggregates when multiple workers share state.

## Security posture (demo)

- Rate limiting on all `/api/*` routes
- HTTP Basic on `/retrain`, `/logs`, and admin APIs
- CORS restricted to configured origins
- Input sanitization strips unexpected fields and control characters
- See `docs/data-privacy.md` for PII handling in production

from pathlib import Path

from dotenv import load_dotenv
import os

APP_DIR = Path(__file__).resolve().parent
CHURN_APP_ROOT = APP_DIR.parent
REPO_ROOT = CHURN_APP_ROOT.parent

load_dotenv(CHURN_APP_ROOT / ".env.local")
load_dotenv(CHURN_APP_ROOT / ".env")

DATA_DIR = REPO_ROOT / "data"
MODEL_DIR = REPO_ROOT / "models"
DB_PATH = APP_DIR / "data" / "predictions.db"

TEMPLATES_DIR = APP_DIR / "templates"
STATIC_DIR = APP_DIR / "static"

DEFAULT_THRESHOLD = 0.5

CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")

ADMIN_USER = os.getenv("ADMIN_USER", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "churnguard")

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000",
    ).split(",")
    if o.strip()
]

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "reports@churnguard.local")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("1", "true", "yes")

MLRUNS_DIR = REPO_ROOT / "mlruns"
LOG_DIR = CHURN_APP_ROOT / "logs"

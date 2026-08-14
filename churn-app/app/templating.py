from fastapi.templating import Jinja2Templates

from app.config import CLERK_PUBLISHABLE_KEY, TEMPLATES_DIR

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
templates.env.globals["clerk_publishable_key"] = CLERK_PUBLISHABLE_KEY
templates.env.globals["clerk_enabled"] = bool(CLERK_PUBLISHABLE_KEY)

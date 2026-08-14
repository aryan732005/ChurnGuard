from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from app.auth.basic_auth import verify_admin
from app.templating import templates

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request, "page": "home"})


@router.get("/predict", response_class=HTMLResponse)
def predict_page(request: Request):
    return templates.TemplateResponse("predict.html", {"request": request, "page": "predict"})


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request, "page": "dashboard"})


@router.get("/batch", response_class=HTMLResponse)
def batch_page(request: Request):
    return templates.TemplateResponse("batch.html", {"request": request, "page": "batch"})


@router.get("/insights", response_class=HTMLResponse)
def insights_page(request: Request):
    return templates.TemplateResponse("insights.html", {"request": request, "page": "insights"})


@router.get("/experiments", response_class=HTMLResponse)
def experiments_page(request: Request):
    return templates.TemplateResponse("experiments.html", {"request": request, "page": "experiments"})


@router.get("/docs", response_class=HTMLResponse)
def docs_page(request: Request):
    return templates.TemplateResponse("docs.html", {"request": request, "page": "docs"})


@router.get("/about", response_class=HTMLResponse)
def about_page(request: Request):
    return templates.TemplateResponse("about.html", {"request": request, "page": "about"})


@router.get("/retrain", response_class=HTMLResponse)
def retrain_page(request: Request):
    return templates.TemplateResponse("retrain.html", {"request": request, "page": "retrain"})


@router.get("/logs", response_class=HTMLResponse)
def logs_page(request: Request, _admin: str = Depends(verify_admin)):
    return templates.TemplateResponse("logs.html", {"request": request, "page": "logs"})


@router.get("/sign-in", response_class=HTMLResponse)
def sign_in_page(request: Request):
    return templates.TemplateResponse("sign-in.html", {"request": request, "page": "sign-in"})


@router.get("/sign-up", response_class=HTMLResponse)
def sign_up_page(request: Request):
    return templates.TemplateResponse("sign-up.html", {"request": request, "page": "sign-up"})

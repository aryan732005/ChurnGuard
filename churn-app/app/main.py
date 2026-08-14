from pathlib import Path

import time



from fastapi import FastAPI, Request

from fastapi.middleware.cors import CORSMiddleware

from fastapi.responses import JSONResponse, PlainTextResponse

from fastapi.staticfiles import StaticFiles

from starlette.exceptions import HTTPException as StarletteHTTPException

from slowapi.errors import RateLimitExceeded

from slowapi import _rate_limit_exceeded_handler



from app.config import CORS_ORIGINS, STATIC_DIR

from app.observability.logging_config import setup_logging, record_latency_ms

from app.rate_limit import limiter

from app.routers import api, pages

from app.templating import templates



logger = setup_logging()



app = FastAPI(

    title="ChurnGuard",

    description="Customer churn prediction — minimal SaaS-grade analytics",

    version="1.0.0",

    docs_url="/swagger",

    redoc_url=None,

    openapi_url="/openapi.json",

)



app.state.limiter = limiter

app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)



app.add_middleware(

    CORSMiddleware,

    allow_origins=CORS_ORIGINS,

    allow_credentials=True,

    allow_methods=["GET", "POST", "OPTIONS"],

    allow_headers=["Authorization", "Content-Type"],

)



app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

app.include_router(pages.router)

app.include_router(api.router)





@app.middleware("http")

async def observability_middleware(request: Request, call_next):

    t0 = time.perf_counter()

    response = await call_next(request)

    elapsed = (time.perf_counter() - t0) * 1000

    path = request.url.path

    if path.startswith("/api"):

        record_latency_ms(elapsed, path)

        logger.info("api_request path=%s status=%s latency_ms=%.2f", path, response.status_code, elapsed)

    return response





@app.exception_handler(StarletteHTTPException)

async def http_exception_handler(request: Request, exc: StarletteHTTPException):

    if exc.status_code == 404:

        return templates.TemplateResponse(

            "404.html",

            {"request": request, "page": ""},

            status_code=404,

        )

    if request.url.path.startswith("/api"):

        logger.warning("http_error path=%s status=%s detail=%s", request.url.path, exc.status_code, exc.detail)

        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    if exc.status_code in (401, 403):
        headers = dict(exc.headers) if exc.headers else {"WWW-Authenticate": "Basic"}
        return PlainTextResponse(str(exc.detail), status_code=exc.status_code, headers=headers)

    raise exc





@app.get("/health")

def health():

    from app.ml.predictor import predictor

    from app.config import CLERK_PUBLISHABLE_KEY

    return {

        "status": "ok",

        "model_loaded": predictor.ready,

        "clerk_configured": bool(CLERK_PUBLISHABLE_KEY),

    }





if __name__ == "__main__":

    import uvicorn

    uvicorn.run(

        "app.main:app",

        host="127.0.0.1",

        port=8000,

        reload=True,

        reload_dirs=[str(Path(__file__).resolve().parent)],

    )


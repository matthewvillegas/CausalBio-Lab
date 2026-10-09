"""CausalBio Lab FastAPI application factory."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from causalbio_api import __version__
from causalbio_api.config import get_settings
from causalbio_api.exceptions import install_exception_handlers
from causalbio_api.middleware import CorrelationAndSecurityMiddleware, LocalRateLimitMiddleware
from causalbio_api.routers.research import router as research_router
from causalbio_api.routers.v1 import router


def create_app() -> FastAPI:
    settings = get_settings()
    application = FastAPI(
        title="CausalBio Lab API",
        summary="Evidence-grounded biological mechanism investigations",
        description=(
            "Local-first research API for provenance-rich causal graphs, competing hypotheses, "
            "curated Petri simulations, and eligibility-gated Bayesian inference. Not a diagnosis "
            "or prescribing service."
        ),
        version=__version__,
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=sorted(
            {
                settings.web_origin,
                "http://127.0.0.1:3000",
                "http://localhost:3000",
            }
        ),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["content-type", "x-correlation-id"],
        expose_headers=["x-correlation-id", "content-disposition"],
    )
    application.add_middleware(
        LocalRateLimitMiddleware,
        requests_per_minute=settings.local_rate_limit_per_minute,
    )
    application.add_middleware(
        CorrelationAndSecurityMiddleware,
        max_request_bytes=settings.max_request_bytes,
    )
    application.include_router(router)
    application.include_router(research_router)
    install_exception_handlers(application)
    return application


app = create_app()

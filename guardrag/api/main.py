"""FastAPI application factory for GuardRAG."""

from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from guardrag import __version__
from guardrag.api.routes.chat import router as chat_router
from guardrag.api.routes.documents import router as documents_router
from guardrag.api.routes.guardrails import router as guardrails_router
from guardrag.api.routes.system import router as system_router
from guardrag.core.config import get_settings
from guardrag.core.exceptions import GuardRAGError
from guardrag.core.models import ErrorResponse

logger = logging.getLogger(__name__)


def setup_logging() -> None:
    """Configure structured logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events.

    Handles startup and shutdown logic.
    """
    setup_logging()
    logger.info("GuardRAG v%s starting up...", __version__)

    settings = get_settings()
    logger.info(
        "Configuration: env=%s, debug=%s, model=%s, embedding=%s",
        settings.app_env,
        settings.app_debug,
        settings.openai_model,
        settings.openai_embedding_model,
    )

    yield

    logger.info("GuardRAG v%s shutting down...", __version__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI app instance.
    """
    app = FastAPI(
        title="GuardRAG",
        description="Secure Document Q&A System with RAG + LLM Guardrails",
        version=__version__,
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trace ID middleware
    @app.middleware("http")
    async def add_trace_id(request: Request, call_next):
        """Add trace ID to every request."""
        trace_id = str(uuid.uuid4())
        request.state.trace_id = trace_id
        response = await call_next(request)
        response.headers["X-Trace-ID"] = trace_id
        return response

    # Exception handler for GuardRAGError
    @app.exception_handler(GuardRAGError)
    async def guardrag_error_handler(request: Request, exc: GuardRAGError):
        """Handle GuardRAG-specific errors."""
        trace_id = getattr(request.state, "trace_id", "unknown")
        return JSONResponse(
            status_code=exc.status_code,
            content=ErrorResponse(
                title=type(exc).__name__,
                detail=exc.message,
                status=exc.status_code,
                trace_id=trace_id,
            ).model_dump(),
        )

    # Exception handler for generic exceptions
    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        """Handle generic exceptions."""
        trace_id = getattr(request.state, "trace_id", "unknown")
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                title="Internal Server Error",
                detail=str(exc),
                status=500,
                trace_id=trace_id,
            ).model_dump(),
        )

    # Register routers
    app.include_router(documents_router, prefix="/api/v1")
    app.include_router(chat_router, prefix="/api/v1")
    app.include_router(guardrails_router, prefix="/api/v1")
    app.include_router(system_router)

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "GuardRAG",
            "version": __version__,
            "docs": "/docs",
        }

    return app


app = create_app()


def main() -> None:
    """Entry point for running the application."""
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "guardrag.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers,
        reload=settings.app_debug,
    )


if __name__ == "__main__":
    main()

import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.router import api_router
from app.core.config import settings
from app.schemas.face import HealthResponse


logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    settings.enrollment_storage_dir.mkdir(parents=True, exist_ok=True)
    yield


fastapi_app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Face enrollment, privacy-conscious edge inference, identity-aware "
        "context, and personalized text and voice conversation API."
    ),
    debug=settings.app_debug,
    lifespan=lifespan,
)
fastapi_app.include_router(api_router)


@fastapi_app.exception_handler(RequestValidationError)
async def log_request_validation_error(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    errors = exc.errors()
    logger.warning(
        "Request validation failed: method=%s path=%s detail=%s",
        request.method,
        request.url.path,
        errors,
    )
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(errors)},
    )


@fastapi_app.get("/health", response_model=HealthResponse, tags=["system"])
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service=settings.app_name)


# Keep CORS outermost so even unhandled error responses carry browser-readable
# CORS headers. This applies uniformly to every route, including /conversation.
app = CORSMiddleware(
    app=fastapi_app,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

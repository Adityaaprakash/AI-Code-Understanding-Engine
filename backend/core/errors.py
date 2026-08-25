# backend/core/errors.py
"""Centralized exception classes and FastAPI exception handlers."""

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.schemas.errors import ErrorDetail, ErrorResponse

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception for domain and infrastructure errors."""

    def __init__(
        self,
        message: str,
        code: str = "BAD_REQUEST",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details


async def app_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handler for application-specific custom exceptions."""
    if not isinstance(exc, AppException):
        return await unhandled_exception_handler(_request, exc)

    payload = ErrorResponse(
        error=ErrorDetail(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        )
    ).model_dump()
    return JSONResponse(status_code=exc.status_code, content=payload)


async def http_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handler for standard Starlette/FastAPI HTTP exceptions."""
    if not isinstance(exc, StarletteHTTPException):
        return await unhandled_exception_handler(_request, exc)

    code = "NOT_FOUND" if exc.status_code == status.HTTP_404_NOT_FOUND else "HTTP_ERROR"
    message = f"{exc.detail}" if exc.detail else "HTTP request error"

    payload = ErrorResponse(
        error=ErrorDetail(
            code=code,
            message=message,
            details=None,
        )
    ).model_dump()
    return JSONResponse(status_code=exc.status_code, content=payload)


async def validation_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handler for Pydantic/FastAPI request validation errors (HTTP 422)."""
    if not isinstance(exc, RequestValidationError):
        return await unhandled_exception_handler(_request, exc)

    payload = ErrorResponse(
        error=ErrorDetail(
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details=exc.errors(),
        )
    ).model_dump()
    return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload)


async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Handler for unexpected unhandled exceptions (HTTP 500). Prevents leaking tracebacks."""
    logger.exception("Unhandled server exception: %s", exc)
    payload = ErrorResponse(
        error=ErrorDetail(
            code="INTERNAL_ERROR",
            message="An unexpected internal server error occurred",
            details=None,
        )
    ).model_dump()
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=payload,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all global exception handlers on the FastAPI application instance."""
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)


__all__ = [
    "AppException",
    "app_exception_handler",
    "http_exception_handler",
    "register_exception_handlers",
    "unhandled_exception_handler",
    "validation_exception_handler",
]

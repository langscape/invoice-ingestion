"""API middleware for logging and error handling."""
from __future__ import annotations
import time
import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.monotonic()
        try:
            response = await call_next(request)
            duration = int((time.monotonic() - start) * 1000)
            logger.info("request", method=request.method, path=request.url.path,
                       status=response.status_code, duration_ms=duration)
            return response
        except Exception as e:
            duration = int((time.monotonic() - start) * 1000)
            logger.error("request_error", method=request.method, path=request.url.path,
                        error=str(e), duration_ms=duration)
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})

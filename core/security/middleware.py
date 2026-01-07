"""
Military-Grade Security Middleware
Protects high-value targets (yacht owners) from sophisticated attacks
"""
import os
import uuid
import time
from typing import Callable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from core.security.audit_logger import security_logger


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Add comprehensive security headers to all responses.

    Protects against:
    - Clickjacking (X-Frame-Options)
    - MIME sniffing attacks (X-Content-Type-Options)
    - XSS attacks (X-XSS-Protection, CSP)
    - Man-in-the-middle (HSTS)
    - Protocol downgrade attacks (Strict-Transport-Security)
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Prevent clickjacking - don't allow framing
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS protection
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Force HTTPS for 1 year (31536000 seconds)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        # Content Security Policy - restrict resource loading
        # Allows self + inline styles (for HTML emails in activation pages)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )

        # Referrer policy - don't leak URLs to external sites
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy - disable unnecessary browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=(), "
            "magnetometer=(), gyroscope=(), speaker=()"
        )

        return response


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """
    Track all requests with unique IDs for forensic analysis.

    Features:
    - Unique request ID per request
    - Request/response timing
    - Automatic audit logging
    - Correlation for attack pattern detection
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # Record request start time
        start_time = time.time()

        # Log incoming request
        security_logger.info("request_received", extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
        })

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log successful response
            security_logger.info("request_completed", extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": round(duration_ms, 2),
            })

            # Add request ID to response headers for tracking
            response.headers["X-Request-ID"] = request_id

            return response

        except Exception as e:
            # Log errors for incident response
            duration_ms = (time.time() - start_time) * 1000

            security_logger.error("request_failed", extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "duration_ms": round(duration_ms, 2),
            })

            raise


class YachtTargetingProtectionMiddleware(BaseHTTPMiddleware):
    """
    Detect and log targeted attacks on specific yachts.

    High-value targets may face:
    - Repeated activation attempts on specific yacht
    - Brute force on yacht_id_hash
    - Credential stuffing attacks

    This middleware logs patterns for security monitoring.
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract yacht_id from path if present
        path_parts = request.url.path.split('/')
        yacht_id = None

        # Check for yacht_id in URL paths
        if '/activate/' in request.url.path:
            # GET /webhook/activate/{yacht_id}
            try:
                yacht_id = path_parts[-1]
            except IndexError:
                pass
        elif '/check-activation/' in request.url.path:
            # POST /webhook/check-activation/{yacht_id}
            try:
                yacht_id = path_parts[-1]
            except IndexError:
                pass

        # If yacht_id detected, log for monitoring
        if yacht_id:
            request.state.target_yacht = yacht_id

            security_logger.info("yacht_access_attempt", extra={
                "request_id": getattr(request.state, 'request_id', 'unknown'),
                "yacht_id": yacht_id,
                "endpoint": request.url.path,
                "client_ip": request.client.host if request.client else "unknown",
            })

        response = await call_next(request)

        # Log failed attempts (potential attacks)
        if yacht_id and response.status_code in [400, 401, 403, 404]:
            security_logger.warning("yacht_access_denied", extra={
                "request_id": getattr(request.state, 'request_id', 'unknown'),
                "yacht_id": yacht_id,
                "status_code": response.status_code,
                "client_ip": request.client.host if request.client else "unknown",
            })

        return response


class AuthenticationLoggingMiddleware(BaseHTTPMiddleware):
    """
    Log all authentication attempts for security monitoring.

    Critical for detecting:
    - Failed registration attempts (invalid yacht_id_hash)
    - Multiple activation attempts (potential attack)
    - Credential retrieval patterns
    """
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Track authentication endpoints
        auth_endpoints = ['/webhook/register', '/webhook/activate', '/webhook/check-activation']

        is_auth_endpoint = any(endpoint in request.url.path for endpoint in auth_endpoints)

        if is_auth_endpoint:
            security_logger.info("authentication_attempt", extra={
                "request_id": getattr(request.state, 'request_id', 'unknown'),
                "endpoint": request.url.path,
                "method": request.method,
                "client_ip": request.client.host if request.client else "unknown",
            })

        response = await call_next(request)

        # Log authentication failures
        if is_auth_endpoint and response.status_code in [400, 401, 403]:
            security_logger.warning("authentication_failed", extra={
                "request_id": getattr(request.state, 'request_id', 'unknown'),
                "endpoint": request.url.path,
                "status_code": response.status_code,
                "client_ip": request.client.host if request.client else "unknown",
            })

        # Log successful authentications
        if is_auth_endpoint and response.status_code in [200, 202]:
            security_logger.info("authentication_success", extra={
                "request_id": getattr(request.state, 'request_id', 'unknown'),
                "endpoint": request.url.path,
                "client_ip": request.client.host if request.client else "unknown",
            })

        return response

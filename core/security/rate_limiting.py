"""
Military-Grade Rate Limiting
Protects high-value targets from brute force and DoS attacks
"""
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse
from core.security.audit_logger import log_rate_limit_exceeded


# Initialize rate limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],  # Global limit: 100 requests/min per IP
    storage_uri="memory://",  # In-memory storage (for production, use Redis)
    headers_enabled=True,  # Return rate limit info in headers
)


# Custom rate limit exceeded handler
def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """
    Custom handler for rate limit violations.

    Logs security event and returns 429 error.
    """
    client_ip = request.client.host if request.client else "unknown"

    # Log the violation for security monitoring
    log_rate_limit_exceeded(
        endpoint=request.url.path,
        client_ip=client_ip,
        limit=str(exc.detail)
    )

    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": "Too many requests. Please try again later.",
            "retry_after": exc.detail
        },
        headers={
            "Retry-After": str(60),  # Tell client to wait 60 seconds
            "X-RateLimit-Limit": "See rate limit headers",
        }
    )


# Rate limit configurations for different endpoints
# Designed to prevent attacks on high-value targets

RATE_LIMITS = {
    # Registration endpoint - strict limits to prevent mass registration attacks
    "register": [
        "3/minute",   # Max 3 registrations per minute per IP
        "10/hour",    # Max 10 registrations per hour per IP
        "20/day"      # Max 20 registrations per day per IP
    ],

    # Activation endpoint - prevent brute force activation attempts
    "activate": [
        "5/minute",   # Max 5 activation attempts per minute per IP
        "20/hour",    # Max 20 activation attempts per hour per IP
        "50/day"      # Max 50 activation attempts per day per IP
    ],

    # Check activation - allow polling but prevent abuse
    # Legitimate installers poll every 5-10 seconds during activation
    "check_activation": [
        "30/minute",  # Max 30 checks per minute (polling every 2 seconds)
        "300/hour",   # Max 300 checks per hour
        "1000/day"    # Max 1000 checks per day
    ],

    # Health check - higher limits for monitoring systems
    "health": [
        "60/minute"   # Max 60 health checks per minute per IP
    ],

    # API documentation - protect from reconnaissance
    "docs": [
        "10/minute",  # Max 10 docs access per minute per IP
        "50/hour"     # Max 50 docs access per hour per IP
    ],
}


def get_yacht_specific_key(request: Request) -> str:
    """
    Generate rate limit key based on yacht_id + IP.

    This prevents targeted attacks on specific yachts.
    Example: Attacker trying to brute force yacht_id_hash for "LUXURY_YACHT_001"

    Returns:
        Combined key: "IP:yacht_id"
    """
    client_ip = get_remote_address(request)

    # Extract yacht_id from path if present
    path_parts = request.url.path.split('/')

    yacht_id = None
    if '/activate/' in request.url.path or '/check-activation/' in request.url.path:
        try:
            yacht_id = path_parts[-1]
        except IndexError:
            pass

    if yacht_id:
        return f"{client_ip}:{yacht_id}"

    return client_ip


# Yacht-specific rate limits (prevent targeted attacks)
YACHT_SPECIFIC_LIMITS = {
    # Per-yacht activation limits (prevents brute force on single target)
    "activate_per_yacht": [
        "3/minute",   # Max 3 attempts per yacht per IP per minute
        "10/hour",    # Max 10 attempts per yacht per IP per hour
    ],

    # Per-yacht credential check limits
    "check_per_yacht": [
        "20/minute",  # Max 20 checks per yacht per IP per minute
        "100/hour"    # Max 100 checks per yacht per IP per hour
    ],
}

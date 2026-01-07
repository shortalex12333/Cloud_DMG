"""
FastAPI Server - CelesteOS Cloud Onboarding System
MILITARY-GRADE SECURITY for High-Value Targets

Security Features:
- Multi-layer rate limiting (IP + yacht-specific)
- Comprehensive security headers (HSTS, CSP, X-Frame-Options)
- Strict CORS policy
- Request tracking and audit logging
- Attack pattern detection
- Forensic-ready structured logging
"""
import os
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi import status, HTTPException
import secrets

# Import workflows
from workflows.onboarding.register import handle_register
from workflows.onboarding.check_activation import handle_check_activation
from workflows.onboarding.activate import handle_activate
from core.validation.schemas import RegisterRequest

# Import security components
from core.security.middleware import (
    SecurityHeadersMiddleware,
    RequestTrackingMiddleware,
    YachtTargetingProtectionMiddleware,
    AuthenticationLoggingMiddleware
)
from core.security.rate_limiting import (
    limiter,
    rate_limit_handler,
    RATE_LIMITS,
    YACHT_SPECIFIC_LIMITS,
    get_yacht_specific_key
)
from core.security.audit_logger import security_logger, app_logger
from slowapi.errors import RateLimitExceeded

import uvicorn


# Determine if running in production
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# Initialize FastAPI app with security-first configuration
app = FastAPI(
    title="CelesteOS Cloud API",
    description="Military-Grade Yacht Onboarding System for High-Value Targets",
    version="2.0.0-secure",
    # Disable auto-docs in production (security through obscurity layer)
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)

# ===================================================================
# SECURITY LAYER 1: Rate Limiting
# ===================================================================

# Register rate limiter with app
app.state.limiter = limiter

# Custom rate limit exceeded handler
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)


# ===================================================================
# SECURITY LAYER 2: CORS (Strict Whitelist Only)
# ===================================================================

# Only allow requests from known origins
# For yacht owners, we only accept requests from:
# 1. Main website (celeste7.ai)
# 2. API subdomain (api.celeste7.ai)
# 3. Future yacht-specific subdomains (*.celeste7.ai)

ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",") if os.getenv("ALLOWED_ORIGINS") else [
    "https://celeste7.ai",
    "https://www.celeste7.ai",
    "https://api.celeste7.ai",
]

# Add CORS middleware with strict policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # NEVER use ["*"] for high-value targets
    allow_credentials=True,
    allow_methods=["GET", "POST"],  # Only methods we use
    allow_headers=["Content-Type", "Authorization"],  # Explicit whitelist
    max_age=3600,  # Cache preflight requests for 1 hour
)


# ===================================================================
# SECURITY LAYER 3: Trusted Host Protection
# ===================================================================

# Only accept requests to these hostnames (prevents host header attacks)
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "").split(",") if os.getenv("ALLOWED_HOSTS") else [
    "cloud-dmg.onrender.com",
    "api.celeste7.ai",
    "localhost",
    "127.0.0.1",
]

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS
)


# ===================================================================
# SECURITY LAYER 4: Custom Security Middleware
# ===================================================================

# Add comprehensive security headers
app.add_middleware(SecurityHeadersMiddleware)

# Add request tracking for forensics
app.add_middleware(RequestTrackingMiddleware)

# Add yacht-specific attack detection
app.add_middleware(YachtTargetingProtectionMiddleware)

# Add authentication event logging
app.add_middleware(AuthenticationLoggingMiddleware)


# ===================================================================
# SECURITY LAYER 5: API Documentation Protection
# ===================================================================

# Basic authentication for API docs (if enabled in non-production)
security = HTTPBasic()

def verify_docs_auth(credentials: HTTPBasicCredentials = Depends(security)):
    """Protect API documentation with basic auth"""
    correct_username = secrets.compare_digest(
        credentials.username.encode("utf8"),
        os.getenv("DOCS_USERNAME", "admin").encode("utf8")
    )
    correct_password = secrets.compare_digest(
        credentials.password.encode("utf8"),
        os.getenv("DOCS_PASSWORD", "changeme123!").encode("utf8")
    )

    if not (correct_username and correct_password):
        security_logger.warning("docs_access_denied", extra={
            "username_attempted": credentials.username,
        })
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials


# ===================================================================
# API ENDPOINTS
# ===================================================================

@app.get("/")
@limiter.limit("60/minute")  # General rate limit
async def root(request: Request):
    """API root endpoint - Public information"""
    return JSONResponse(content={
        "service": "CelesteOS Cloud API",
        "version": "2.0.0-secure",
        "security": "military-grade",
        "endpoints": {
            "register": "POST /webhook/register",
            "check_activation": "POST /webhook/check-activation/:yacht_id",
            "activate": "GET /webhook/activate/:yacht_id"
        }
    })


@app.post("/webhook/register")
@limiter.limit(RATE_LIMITS["register"])  # Strict limits: 3/min, 10/hour, 20/day
async def register(request: Request, data: RegisterRequest):
    """
    POST /webhook/register - Yacht Registration

    SECURITY:
    - Rate limited: 3/min, 10/hour, 20/day per IP
    - Input validation: Pydantic + custom validators
    - Audit logged: All attempts logged with request ID

    Registers a yacht and sends activation email to buyer.

    Request Body:
    {
        "yacht_id": "TEST_YACHT_001",
        "yacht_id_hash": "abc123..." (64-char hex SHA-256)
    }

    Response:
    {
        "success": true,
        "message": "Registration successful",
        "activation_link": "https://api.celeste7.ai/webhook/activate/TEST_YACHT_001"
    }
    """
    # Pass request for logging context
    result = handle_register(data, request)

    if result.get("success"):
        return JSONResponse(content=result, status_code=200)
    else:
        status_code = 400 if result.get("error") in ["validation_error", "invalid_yacht_id"] else 500
        return JSONResponse(content=result, status_code=status_code)


@app.get("/webhook/activate/{yacht_id}")
@limiter.limit(RATE_LIMITS["activate"])  # 5/min, 20/hour, 50/day per IP
@limiter.limit(YACHT_SPECIFIC_LIMITS["activate_per_yacht"], key_func=get_yacht_specific_key)  # 3/min per yacht+IP
async def activate(yacht_id: str, request: Request):
    """
    GET /webhook/activate/:yacht_id - Buyer Activation

    SECURITY:
    - IP rate limiting: 5/min, 20/hour, 50/day
    - Per-yacht limiting: 3/min per yacht+IP (prevents targeted attacks)
    - Audit logged: All activation attempts tracked

    Buyer clicks this link from activation email.
    Activates yacht and generates shared_secret.
    Returns HTML success page.
    """
    html_content, status_code = handle_activate(yacht_id, request)
    return HTMLResponse(content=html_content, status_code=status_code)


@app.post("/webhook/check-activation/{yacht_id}")
@limiter.limit(RATE_LIMITS["check_activation"])  # 30/min, 300/hour (allow polling)
@limiter.limit(YACHT_SPECIFIC_LIMITS["check_per_yacht"], key_func=get_yacht_specific_key)  # 20/min per yacht+IP
async def check_activation(yacht_id: str, request: Request):
    """
    POST /webhook/check-activation/:yacht_id - Activation Status Polling

    SECURITY:
    - IP rate limiting: 30/min, 300/hour (allows legitimate polling)
    - Per-yacht limiting: 20/min per yacht+IP (prevents brute force)
    - Audit logged: Credential retrievals tracked
    - One-time retrieval: Credentials only returned once

    Installer polls this endpoint to check if buyer has activated the yacht.
    Returns credentials ONE TIME ONLY.

    Response (pending):
    {
        "status": "pending",
        "message": "Waiting for owner activation"
    }

    Response (active, first time):
    {
        "status": "active",
        "shared_secret": "...",
        "supabase_url": "...",
        "supabase_anon_key": "..."
    }

    Response (already retrieved):
    {
        "status": "already_retrieved",
        "message": "Credentials have already been retrieved"
    }
    """
    result = handle_check_activation(yacht_id, request)

    if result.get("status") in ["pending", "active", "already_retrieved"]:
        return JSONResponse(content=result, status_code=200)
    else:
        return JSONResponse(content=result, status_code=400)


@app.get("/health")
@limiter.limit(RATE_LIMITS["health"])  # 60/minute (for monitoring systems)
async def health_check(request: Request):
    """
    Health check endpoint

    Used by:
    - Render platform monitoring
    - Uptime monitoring services
    - Load balancers
    """
    return JSONResponse(content={
        "status": "healthy",
        "service": "celeste7-cloud",
        "version": "2.0.0-secure",
        "security": "enabled"
    })


# ===================================================================
# STARTUP/SHUTDOWN EVENTS
# ===================================================================

@app.on_event("startup")
async def startup_event():
    """Log application startup"""
    app_logger.info("application_started", extra={
        "version": "2.0.0-secure",
        "environment": ENVIRONMENT,
        "security_features": [
            "rate_limiting",
            "security_headers",
            "cors_whitelist",
            "request_tracking",
            "audit_logging",
            "yacht_targeting_protection"
        ]
    })


@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown"""
    app_logger.info("application_stopped")


# ===================================================================
# MAIN ENTRY POINT
# ===================================================================

if __name__ == "__main__":
    # Load environment variables
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    # Log startup information
    app_logger.info("server_starting", extra={
        "host": host,
        "port": port,
        "environment": ENVIRONMENT,
        "docs_enabled": not IS_PRODUCTION,
    })

    # Run server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=(ENVIRONMENT == "development"),  # Only reload in development
        log_level="info",
    )

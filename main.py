"""
FastAPI Server - CelesteOS Cloud Onboarding System
Converted from n8n workflows to Python
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from workflows.onboarding.register import handle_register
from workflows.onboarding.check_activation import handle_check_activation
from workflows.onboarding.activate import handle_activate
from core.validation.schemas import RegisterRequest
import uvicorn
import os

# Initialize FastAPI app
app = FastAPI(
    title="CelesteOS Cloud API",
    description="Yacht onboarding and document management system",
    version="1.0.0"
)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "CelesteOS Cloud API",
        "version": "1.0.0",
        "endpoints": {
            "register": "POST /webhook/register",
            "check_activation": "POST /webhook/check-activation/:yacht_id",
            "activate": "GET /webhook/activate/:yacht_id"
        }
    }


@app.post("/webhook/register")
async def register(request: RegisterRequest):
    """
    POST /webhook/register - Yacht Registration

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
    result = handle_register(request)

    if result.get("success"):
        return JSONResponse(content=result, status_code=200)
    else:
        status_code = 400 if result.get("error") in ["validation_error", "invalid_yacht_id"] else 500
        return JSONResponse(content=result, status_code=status_code)


@app.post("/webhook/check-activation/{yacht_id}")
async def check_activation(yacht_id: str):
    """
    POST /webhook/check-activation/:yacht_id - Activation Status Polling

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
    result = handle_check_activation(yacht_id)

    if result.get("status") in ["pending", "active", "already_retrieved"]:
        return JSONResponse(content=result, status_code=200)
    else:
        return JSONResponse(content=result, status_code=400)


@app.get("/webhook/activate/{yacht_id}")
async def activate(yacht_id: str):
    """
    GET /webhook/activate/:yacht_id - Buyer Activation

    Buyer clicks this link from activation email.
    Activates yacht and generates shared_secret.
    Returns HTML success page.
    """
    html_content, status_code = handle_activate(yacht_id)
    return HTMLResponse(content=html_content, status_code=status_code)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "celeste7-cloud"}


if __name__ == "__main__":
    # Load environment variables
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")

    print("=" * 60)
    print("CelesteOS Cloud API Server")
    print("=" * 60)
    print(f"Starting server on {host}:{port}")
    print(f"Docs: http://{host}:{port}/docs")
    print("=" * 60)

    # Run server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True  # Enable auto-reload for development
    )

"""
Pydantic models for request/response validation
Provides type-safe API contracts
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import re


class RegisterRequest(BaseModel):
    """Request body for POST /register"""
    yacht_id: str = Field(..., description="Yacht identifier (uppercase, alphanumeric, _, -)")
    yacht_id_hash: str = Field(..., description="SHA-256 hash of yacht_id (64 hex chars)")

    @validator('yacht_id')
    def validate_yacht_id(cls, v):
        if not re.match(r'^[A-Z0-9_-]+$', v):
            raise ValueError('yacht_id contains invalid characters')
        if len(v) > 50:
            raise ValueError('yacht_id too long (max 50 characters)')
        return v

    @validator('yacht_id_hash')
    def validate_hash(cls, v):
        if not re.match(r'^[a-f0-9]{64}$', v):
            raise ValueError('yacht_id_hash must be 64-character hex string')
        return v


class RegisterResponse(BaseModel):
    """Response from POST /register"""
    success: bool
    message: str
    activation_link: Optional[str] = None
    error: Optional[str] = None
    errors: Optional[List[str]] = None


class CheckActivationResponse(BaseModel):
    """Response from POST /check-activation/:yacht_id"""
    status: str  # "pending" | "active" | "already_retrieved" | "error"
    message: Optional[str] = None
    shared_secret: Optional[str] = None
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    error: Optional[str] = None


class ActivateResponse(BaseModel):
    """Response from GET /activate/:yacht_id"""
    success: bool
    message: str
    yacht_id: Optional[str] = None
    error: Optional[str] = None


class ErrorResponse(BaseModel):
    """Generic error response"""
    success: bool = False
    error: str
    message: str
    errors: Optional[List[str]] = None

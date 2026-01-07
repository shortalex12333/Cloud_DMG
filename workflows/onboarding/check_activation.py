"""
POST /check-activation/:yacht_id - Activation Status Polling
Converted from n8n Signature_Installer_Cloud.json
"""
import os
from typing import Dict, Any
from core.validation.yacht_id import validate_yacht_id
from core.database.fleet_registry import lookup_status, mark_credentials_retrieved
from core.validation.schemas import CheckActivationResponse, ErrorResponse


def handle_check_activation(yacht_id: str) -> Dict[str, Any]:
    """
    Check activation status and return credentials (ONE TIME ONLY).

    Workflow:
    1. Validate yacht_id parameter
    2. Lookup yacht status
    3. If not active: return "pending" status
    4. If already retrieved: return "already_retrieved" status
    5. If active and not retrieved: return credentials and mark as retrieved

    Converted from n8n nodes:
    - "Validate Check Parameter"
    - "Lookup Status"
    - "Check Status"
    - "Should Mark Retrieved?"
    - "Mark Credentials Retrieved"

    Args:
        yacht_id: The yacht identifier from URL parameter

    Returns:
        CheckActivationResponse or ErrorResponse
    """
    # Step 1: Validate yacht_id
    is_valid, errors = validate_yacht_id(yacht_id)

    if not is_valid:
        return ErrorResponse(
            error="invalid_yacht_id",
            message="Invalid yacht ID",
            errors=errors
        ).dict()

    # Step 2: Lookup yacht status
    registration = lookup_status(yacht_id)

    if not registration:
        return ErrorResponse(
            error="yacht_not_found",
            message="Yacht not found"
        ).dict()

    # Step 3: Check activation status
    if not registration.get("active"):
        # Yacht is registered but not yet activated
        return CheckActivationResponse(
            status="pending",
            message="Waiting for owner activation"
        ).dict()

    # Step 4: Check if credentials already retrieved
    if registration.get("credentials_retrieved"):
        return CheckActivationResponse(
            status="already_retrieved",
            message="Credentials have already been retrieved"
        ).dict()

    # Step 5: Return credentials ONE TIME ONLY
    shared_secret = registration.get("shared_secret")

    if not shared_secret:
        return ErrorResponse(
            error="missing_secret",
            message="Yacht is active but shared_secret was not generated"
        ).dict()

    # Get Supabase credentials from environment
    supabase_url = os.getenv("SUPABASE_URL", "https://qvzmkaamzaqxpzbewjxe.supabase.co")
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "")

    # Mark credentials as retrieved (one-time enforcement)
    try:
        mark_credentials_retrieved(yacht_id)
    except Exception as e:
        print(f"Warning: Failed to mark credentials as retrieved: {e}")

    return CheckActivationResponse(
        status="active",
        message="Yacht activated. Credentials returned (one-time only).",
        shared_secret=shared_secret,
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key
    ).dict()

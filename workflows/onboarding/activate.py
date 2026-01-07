"""
GET /activate/:yacht_id - Buyer Activation Handler
Converted from n8n Signature_Installer_Cloud.json
"""
import html
from typing import Dict, Any, Tuple
from core.validation.yacht_id import validate_yacht_id
from core.database.fleet_registry import lookup_for_activation, activate_yacht
from core.security.audit_logger import log_activation_attempt


def generate_success_page(yacht_id: str) -> str:
    """
    Generate success HTML page after activation.

    Converted from n8n node: "Generate Success Page1"

    Args:
        yacht_id: The yacht identifier (will be HTML-escaped)

    Returns:
        HTML string
    """
    yacht_id_safe = html.escape(yacht_id)

    return f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Yacht Activated</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; }}
    .container {{ background: white; border-radius: 16px; padding: 48px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; max-width: 500px; animation: slideIn 0.5s ease-out; }}
    @keyframes slideIn {{ from {{ opacity: 0; transform: translateY(30px); }} to {{ opacity: 1; transform: translateY(0); }} }}
    .icon {{ font-size: 72px; margin-bottom: 24px; }}
    h1 {{ color: #333; margin-bottom: 16px; font-size: 32px; }}
    p {{ color: #666; font-size: 18px; line-height: 1.6; margin-bottom: 12px; }}
    .yacht-id {{ font-family: 'Courier New', monospace; background: #f0f0f0; padding: 12px 20px; border-radius: 8px; display: inline-block; margin: 20px 0; font-weight: bold; color: #0066cc; }}
    .success {{ color: #10b981; font-weight: 600; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="icon">⚓</div>
    <h1>Yacht Activated!</h1>
    <p class="success">Your yacht has been successfully activated.</p>
    <div class="yacht-id">{yacht_id_safe}</div>
    <p>Your yacht is now authorized to communicate with Celeste7 Cloud.</p>
    <p style="margin-top: 32px; font-size: 14px; color: #999;">You can close this window.</p>
  </div>
</body>
</html>'''


def generate_error_page(yacht_id: str, error_message: str) -> str:
    """
    Generate error HTML page.

    Args:
        yacht_id: The yacht identifier (will be HTML-escaped)
        error_message: Error message to display

    Returns:
        HTML string
    """
    yacht_id_safe = html.escape(yacht_id)
    error_safe = html.escape(error_message)

    return f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Activation Error</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); display: flex; align-items: center; justify-content: center; min-height: 100vh; margin: 0; padding: 20px; }}
    .container {{ background: white; border-radius: 16px; padding: 48px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); text-align: center; max-width: 500px; }}
    .icon {{ font-size: 72px; margin-bottom: 24px; }}
    h1 {{ color: #dc2626; margin-bottom: 16px; font-size: 32px; }}
    p {{ color: #666; font-size: 18px; line-height: 1.6; margin-bottom: 12px; }}
    .yacht-id {{ font-family: 'Courier New', monospace; background: #f0f0f0; padding: 12px 20px; border-radius: 8px; display: inline-block; margin: 20px 0; font-weight: bold; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="icon">⚠️</div>
    <h1>Activation Error</h1>
    <p>{error_safe}</p>
    <div class="yacht-id">{yacht_id_safe}</div>
    <p style="margin-top: 32px; font-size: 14px; color: #999;">Please contact support if this issue persists.</p>
  </div>
</body>
</html>'''


def handle_activate(yacht_id: str, http_request=None) -> Tuple[str, int]:
    """
    Handle buyer activation request (from email link).

    Workflow:
    1. Validate yacht_id parameter
    2. Check if yacht already activated
    3. Activate yacht (set active=true, generate shared_secret)
    4. Return success HTML page

    Converted from n8n nodes:
    - "Webhook: GET /activate/:yacht_id1"
    - "Validate yacht_id Parameter1"
    - "Lookup for Activation1"
    - "Can Activate?1"
    - "Activate Yacht1"
    - "Generate Success Page1"
    - "Respond Success Page1"

    Args:
        yacht_id: The yacht identifier from URL parameter

    Returns:
        Tuple of (html_content, http_status_code)
    """
    # Step 1: Validate yacht_id
    is_valid, errors = validate_yacht_id(yacht_id)

    if not is_valid:
        error_msg = "; ".join(errors) if errors else "Invalid yacht ID"
        return generate_error_page(yacht_id, error_msg), 400

    # Step 2: Check if already activated
    already_active = lookup_for_activation(yacht_id)

    if already_active:
        return generate_error_page(
            yacht_id,
            "This yacht has already been activated."
        ), 400

    # Step 3: Activate yacht
    try:
        activated_yacht = activate_yacht(yacht_id)

        if not activated_yacht:
            return generate_error_page(
                yacht_id,
                "Failed to activate yacht. Yacht may not exist in registry."
            ), 500

    except Exception as e:
        client_ip = http_request.client.host if http_request and http_request.client else "unknown"
        request_id = getattr(http_request.state, 'request_id', 'unknown') if http_request else "unknown"

        log_activation_attempt(yacht_id, client_ip, request_id, success=False)

        return generate_error_page(
            yacht_id,
            "An error occurred during activation. Please try again."
        ), 500

    # Step 4: Log and return success page
    client_ip = http_request.client.host if http_request and http_request.client else "unknown"
    request_id = getattr(http_request.state, 'request_id', 'unknown') if http_request else "unknown"

    log_activation_attempt(yacht_id, client_ip, request_id, success=True)

    return generate_success_page(yacht_id), 200

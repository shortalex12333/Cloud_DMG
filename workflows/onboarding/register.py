"""
POST /register - Yacht Registration Endpoint
Converted from n8n Signature_Installer_Cloud.json
"""
from typing import Dict, Any
from core.validation.yacht_id import validate_registration_input
from core.validation.email import validate_email, get_email_error_message
from core.database.fleet_registry import lookup_yacht, update_registration_timestamp
from core.validation.schemas import RegisterRequest, RegisterResponse, ErrorResponse
from core.email.sender import send_activation_email
from core.security.audit_logger import app_logger, log_registration_attempt
import html


def escape_html(text: str) -> str:
    """HTML escape for XSS protection"""
    return html.escape(text)


def prepare_activation_email(yacht_id: str, buyer_email: str) -> Dict[str, Any]:
    """
    Prepare activation email with HTML and plain text versions.

    Converted from n8n node: "Prepare Email (XSS-Safe)"

    Args:
        yacht_id: The yacht identifier (will be HTML-escaped)
        buyer_email: Recipient email address

    Returns:
        Dict with email data (to, subject, html, text, activation_link)
    """
    yacht_id_safe = escape_html(yacht_id)
    activation_link = f"https://api.celeste7.ai/webhook/activate/{yacht_id}"

    html_body = f'''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f5f5; padding: 40px; }}
    .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 12px; padding: 40px; box-shadow: 0 2px 12px rgba(0,0,0,0.1); }}
    .header {{ text-align: center; margin-bottom: 30px; }}
    .logo {{ font-size: 32px; font-weight: bold; color: #0066cc; }}
    h2 {{ color: #333; margin-bottom: 20px; }}
    .yacht-name {{ color: #0066cc; font-weight: bold; }}
    .button {{ display: inline-block; background: #0066cc; color: white; padding: 14px 32px; text-decoration: none; border-radius: 6px; font-weight: 500; margin: 20px 0; }}
    .code {{ font-family: "Courier New", monospace; background: #f0f0f0; padding: 8px 12px; border-radius: 4px; display: inline-block; margin: 10px 0; }}
    .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">⚓ Celeste7</div>
    </div>
    <h2>Yacht Registration Confirmation</h2>
    <p>Your yacht <span class="yacht-name">{yacht_id_safe}</span> is requesting activation.</p>
    <p>Click the button below to activate your yacht:</p>
    <div style="text-align: center;">
      <a href="{activation_link}" class="button">Activate Yacht</a>
    </div>
    <p>Or copy this link:</p>
    <div class="code">{activation_link}</div>
    <div class="footer">
      <p>Yacht ID: <span class="code">{yacht_id_safe}</span></p>
      <p>If you did not request this, please ignore this email.</p>
    </div>
  </div>
</body>
</html>'''

    text_body = f'''Yacht Registration Confirmation

Your yacht {yacht_id} is requesting activation.

Activation link: {activation_link}

Yacht ID: {yacht_id}

If you did not request this activation, please ignore this email.'''

    return {
        "to": buyer_email,
        "subject": f"Activate Your Yacht: {yacht_id_safe}",
        "html": html_body,
        "text": text_body,
        "activation_link": activation_link
    }


def handle_register(request: RegisterRequest, http_request=None) -> Dict[str, Any]:
    """
    Handle yacht registration request.

    Workflow:
    1. Validate input (yacht_id, yacht_id_hash)
    2. Lookup yacht in fleet_registry
    3. Validate buyer_email exists and is valid
    4. Update registered_at timestamp
    5. Prepare activation email
    6. Send email (TODO: implement email sending)
    7. Return success response with activation_link

    Args:
        request: RegisterRequest with yacht_id and yacht_id_hash

    Returns:
        RegisterResponse or ErrorResponse
    """
    # Step 1: Validate input
    is_valid, sanitized, errors = validate_registration_input(
        request.yacht_id,
        request.yacht_id_hash
    )

    if not is_valid:
        return ErrorResponse(
            error="validation_error",
            message="Invalid registration data",
            errors=errors
        ).dict()

    # Step 2: Lookup yacht
    yacht = lookup_yacht(sanitized["yacht_id"], sanitized["yacht_id_hash"])

    if not yacht:
        return ErrorResponse(
            error="yacht_not_found",
            message="Yacht not found or credentials invalid"
        ).dict()

    # Step 3: Validate buyer_email
    buyer_email = yacht.get("buyer_email")
    email_valid, error_code = validate_email(buyer_email)

    if not email_valid:
        return ErrorResponse(
            error=error_code,
            message=get_email_error_message(error_code)
        ).dict()

    # Step 4: Update registration timestamp
    try:
        update_registration_timestamp(sanitized["yacht_id"])
    except Exception as e:
        # Non-blocking error - continue even if timestamp update fails
        app_logger.warning("registration_timestamp_update_failed", extra={
            "yacht_id": sanitized["yacht_id"],
            "error": str(e),
            "error_type": type(e).__name__,
        })

    # Step 5: Prepare activation email
    email_data = prepare_activation_email(sanitized["yacht_id"], buyer_email)

    # Step 6: Send email via Microsoft Graph API
    try:
        email_result = send_activation_email(
            to=email_data["to"],
            subject=email_data["subject"],
            html=email_data["html"],
            text=email_data["text"]
        )

        if email_result.get("success"):
            app_logger.info("activation_email_sent", extra={
                "yacht_id": sanitized["yacht_id"],
                "recipient": buyer_email,
                "method": email_result.get("method", "unknown"),
            })
        else:
            app_logger.warning("activation_email_failed", extra={
                "yacht_id": sanitized["yacht_id"],
                "recipient": buyer_email,
                "error": email_result.get("error"),
                "activation_link": email_data['activation_link'],
            })
            # Don't fail registration if email fails - return success anyway
    except Exception as e:
        app_logger.error("activation_email_exception", extra={
            "yacht_id": sanitized["yacht_id"],
            "recipient": buyer_email,
            "error": str(e),
            "error_type": type(e).__name__,
            "activation_link": email_data['activation_link'],
        })
        # Don't fail registration if email fails

    # Step 7: Log and return success response
    client_ip = http_request.client.host if http_request and http_request.client else "unknown"
    request_id = getattr(http_request.state, 'request_id', 'unknown') if http_request else "unknown"

    log_registration_attempt(sanitized["yacht_id"], client_ip, request_id, success=True)

    return RegisterResponse(
        success=True,
        message="Registration successful. Activation email sent.",
        activation_link=email_data["activation_link"]
    ).dict()

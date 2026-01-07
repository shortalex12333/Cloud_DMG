"""
Email validation module
Converted from n8n Signature_Installer_Cloud.json "Validate Buyer Email" node
"""
import re
from typing import Tuple


def validate_email(email: str) -> Tuple[bool, str]:
    """
    Validate email format.

    Basic validation:
    - Must contain @ symbol
    - Must have characters before and after @
    - Must have domain with at least one dot

    Args:
        email: The email address to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "no_buyer_email"

    # Basic email regex
    email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
    if not re.match(email_regex, email):
        return False, "invalid_buyer_email"

    return True, ""


def get_email_error_message(error_code: str) -> str:
    """
    Get user-friendly error message for email validation errors.

    Args:
        error_code: Error code from validate_email()

    Returns:
        Human-readable error message
    """
    messages = {
        "no_buyer_email": "This yacht has no buyer email configured. Please contact support.",
        "invalid_buyer_email": "Buyer email is invalid. Please contact support."
    }
    return messages.get(error_code, "Email validation failed")

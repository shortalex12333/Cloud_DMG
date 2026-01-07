"""
Yacht ID validation module
Converted from n8n Signature_Installer_Cloud.json "Validate Input" node
"""
import re
from typing import Tuple, List


def validate_yacht_id(yacht_id: str) -> Tuple[bool, List[str]]:
    """
    Validate yacht_id format.

    Rules:
    - Must be a non-empty string
    - Only uppercase letters, numbers, underscore, hyphen allowed
    - Maximum 50 characters

    Args:
        yacht_id: The yacht identifier to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if not yacht_id or not isinstance(yacht_id, str):
        errors.append("yacht_id is required and must be a string")
        return False, errors

    if not re.match(r'^[A-Z0-9_-]+$', yacht_id):
        errors.append("yacht_id contains invalid characters (only A-Z, 0-9, _, - allowed)")

    if len(yacht_id) > 50:
        errors.append("yacht_id too long (max 50 characters)")

    return len(errors) == 0, errors


def validate_yacht_id_hash(yacht_id_hash: str) -> Tuple[bool, List[str]]:
    """
    Validate yacht_id_hash format.

    Rules:
    - Must be a non-empty string
    - Must be exactly 64 hexadecimal characters (SHA-256)

    Args:
        yacht_id_hash: The SHA-256 hash to validate

    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []

    if not yacht_id_hash or not isinstance(yacht_id_hash, str):
        errors.append("yacht_id_hash is required and must be a string")
        return False, errors

    if not re.match(r'^[a-f0-9]{64}$', yacht_id_hash):
        errors.append("yacht_id_hash must be a valid 64-character hex string (SHA-256)")

    return len(errors) == 0, errors


def validate_registration_input(yacht_id: str, yacht_id_hash: str) -> Tuple[bool, dict, List[str]]:
    """
    Validate complete registration input (yacht_id + yacht_id_hash).

    Args:
        yacht_id: The yacht identifier
        yacht_id_hash: The SHA-256 hash of yacht_id

    Returns:
        Tuple of (is_valid, sanitized_data, list_of_errors)
    """
    all_errors = []

    # Validate yacht_id
    yacht_id_valid, yacht_id_errors = validate_yacht_id(yacht_id)
    all_errors.extend(yacht_id_errors)

    # Validate yacht_id_hash
    hash_valid, hash_errors = validate_yacht_id_hash(yacht_id_hash)
    all_errors.extend(hash_errors)

    if all_errors:
        return False, {}, all_errors

    return True, {
        "yacht_id": yacht_id,
        "yacht_id_hash": yacht_id_hash
    }, []

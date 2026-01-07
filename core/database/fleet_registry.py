"""
Fleet registry database operations
Converted from n8n Signature_Installer_Cloud.json SQL queries
"""
from typing import Optional, Dict, Any
from .client import get_db
import secrets


def lookup_yacht(yacht_id: str, yacht_id_hash: str) -> Optional[Dict[str, Any]]:
    """
    Lookup yacht by yacht_id and yacht_id_hash.

    Converted from n8n node: "Lookup Yacht"
    SQL: SELECT yacht_id, yacht_id_hash, buyer_email, active, credentials_retrieved
         FROM fleet_registry
         WHERE yacht_id = ... AND yacht_id_hash = ...

    Args:
        yacht_id: The yacht identifier
        yacht_id_hash: SHA-256 hash of yacht_id

    Returns:
        Yacht record or None if not found
    """
    db = get_db()
    response = db.table("fleet_registry").select(
        "yacht_id, yacht_id_hash, buyer_email, active, credentials_retrieved"
    ).eq("yacht_id", yacht_id).eq("yacht_id_hash", yacht_id_hash).limit(1).execute()

    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


def update_registration_timestamp(yacht_id: str) -> Dict[str, Any]:
    """
    Update registered_at timestamp to NOW().

    Converted from n8n node: "Update Registration Timestamp"
    SQL: UPDATE fleet_registry SET registered_at = NOW() WHERE yacht_id = ...

    Args:
        yacht_id: The yacht identifier

    Returns:
        Updated yacht record
    """
    db = get_db()
    from datetime import datetime, timezone

    response = db.table("fleet_registry").update({
        "registered_at": datetime.now(timezone.utc).isoformat()
    }).eq("yacht_id", yacht_id).execute()

    return response.data[0] if response.data else {}


def lookup_status(yacht_id: str) -> Optional[Dict[str, Any]]:
    """
    Lookup yacht status for activation polling.

    Converted from n8n node: "Lookup Status"
    SQL: SELECT yacht_id, yacht_id_hash, shared_secret, active, credentials_retrieved, activated_at
         FROM fleet_registry WHERE yacht_id = ...

    Args:
        yacht_id: The yacht identifier

    Returns:
        Yacht status record or None if not found
    """
    db = get_db()
    response = db.table("fleet_registry").select(
        "yacht_id, yacht_id_hash, shared_secret, active, credentials_retrieved, activated_at"
    ).eq("yacht_id", yacht_id).limit(1).execute()

    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


def mark_credentials_retrieved(yacht_id: str) -> None:
    """
    Mark that yacht has retrieved its credentials (one-time enforcement).

    Converted from n8n node: "Mark Credentials Retrieved"
    SQL: UPDATE fleet_registry SET credentials_retrieved = true WHERE yacht_id = ...

    Args:
        yacht_id: The yacht identifier
    """
    db = get_db()
    db.table("fleet_registry").update({
        "credentials_retrieved": True
    }).eq("yacht_id", yacht_id).execute()


def lookup_for_activation(yacht_id: str) -> Optional[Dict[str, Any]]:
    """
    Lookup yacht for activation (must not already be active).

    Converted from n8n node: "Lookup for Activation1"
    SQL: SELECT * FROM fleet_registry WHERE yacht_id = ... AND active = true

    Args:
        yacht_id: The yacht identifier

    Returns:
        Yacht record if already active, None if can be activated
    """
    db = get_db()
    response = db.table("fleet_registry").select("*").eq(
        "yacht_id", yacht_id
    ).eq("active", True).limit(1).execute()

    if response.data and len(response.data) > 0:
        return response.data[0]
    return None


def activate_yacht(yacht_id: str) -> Dict[str, Any]:
    """
    Activate yacht and generate shared_secret.

    Converted from n8n node: "Activate Yacht1"
    SQL: UPDATE fleet_registry
         SET active = true, activated_at = NOW(), shared_secret = encode(gen_random_bytes(32), 'hex')
         WHERE yacht_id = ...

    Args:
        yacht_id: The yacht identifier

    Returns:
        Updated yacht record with shared_secret
    """
    db = get_db()
    from datetime import datetime, timezone

    # Generate 256-bit (32 bytes) shared secret as hex string (64 characters)
    shared_secret = secrets.token_hex(32)

    response = db.table("fleet_registry").update({
        "active": True,
        "activated_at": datetime.now(timezone.utc).isoformat(),
        "shared_secret": shared_secret
    }).eq("yacht_id", yacht_id).execute()

    return response.data[0] if response.data else {}


def cleanup_abandoned_registrations() -> list:
    """
    Delete registrations older than 7 days that were never activated.

    Converted from n8n node: "Cleanup Abandoned Registrations"
    SQL: DELETE FROM fleet_registry
         WHERE active = false AND registered_at IS NOT NULL
         AND registered_at < NOW() - INTERVAL '7 days'

    Returns:
        List of deleted yacht_ids
    """
    db = get_db()
    from datetime import datetime, timedelta, timezone

    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    response = db.table("fleet_registry").delete().eq(
        "active", False
    ).lt("registered_at", cutoff_date).execute()

    return [record["yacht_id"] for record in response.data] if response.data else []

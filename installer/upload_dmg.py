#!/usr/bin/env python3
"""
Upload built DMG to Supabase Storage.

Usage:
    python upload_dmg.py --dmg-path /path/to/CelesteOS-YACHT_001.dmg --yacht-id YACHT_001
"""

import os
import sys
import argparse
import hashlib
from pathlib import Path

# Supabase configuration
SUPABASE_URL = "https://qvzmkaamzaqxpzbewjxe.supabase.co"
SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")


def upload_dmg(dmg_path: Path, yacht_id: str) -> str:
    """Upload DMG to Supabase Storage."""
    import requests
    
    if not SERVICE_KEY:
        raise ValueError("SUPABASE_SERVICE_ROLE_KEY environment variable required")
    
    if not dmg_path.exists():
        raise FileNotFoundError(f"DMG not found: {dmg_path}")
    
    # Calculate hash
    sha256 = hashlib.sha256(dmg_path.read_bytes()).hexdigest()
    print(f"Uploading: {dmg_path.name}")
    print(f"SHA256:    {sha256[:16]}...")
    print(f"Size:      {dmg_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Upload path: installers/dmg/{yacht_id}/CelesteOS-{yacht_id}.dmg
    storage_path = f"dmg/{yacht_id}/{dmg_path.name}"
    
    url = f"{SUPABASE_URL}/storage/v1/object/installers/{storage_path}"
    
    headers = {
        "Authorization": f"Bearer {SERVICE_KEY}",
        "apikey": SERVICE_KEY,
        "Content-Type": "application/octet-stream",
        "x-upsert": "true",  # Overwrite if exists
    }
    
    with open(dmg_path, "rb") as f:
        resp = requests.post(url, headers=headers, data=f)
    
    if resp.status_code in (200, 201):
        print(f"Uploaded to: {storage_path}")
        return storage_path
    else:
        raise Exception(f"Upload failed: {resp.status_code} - {resp.text}")


def create_download_link(yacht_id: str, token: str, expires_hours: int = 168) -> str:
    """Create download link in database."""
    import requests
    import hashlib
    
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    
    url = f"{SUPABASE_URL}/rest/v1/download_links"
    headers = {
        "Authorization": f"Bearer {SERVICE_KEY}",
        "apikey": SERVICE_KEY,
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    
    from datetime import datetime, timedelta
    expires_at = (datetime.utcnow() + timedelta(hours=expires_hours)).isoformat() + "Z"
    
    data = {
        "yacht_id": yacht_id,
        "token_hash": token_hash,
        "expires_at": expires_at,
    }
    
    resp = requests.post(url, headers=headers, json=data)
    
    if resp.status_code in (200, 201):
        download_url = f"{SUPABASE_URL}/functions/v1/download?token={token}"
        print(f"Download link: {download_url}")
        return download_url
    else:
        raise Exception(f"Failed to create download link: {resp.text}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload DMG to Supabase Storage")
    parser.add_argument("--dmg-path", required=True, help="Path to DMG file")
    parser.add_argument("--yacht-id", required=True, help="Yacht ID")
    parser.add_argument("--create-link", action="store_true", help="Create download link")
    
    args = parser.parse_args()
    
    dmg_path = Path(args.dmg_path)
    
    try:
        storage_path = upload_dmg(dmg_path, args.yacht_id)
        
        if args.create_link:
            import secrets
            token = secrets.token_hex(32)
            create_download_link(args.yacht_id, token)
        
        print("\nUpload complete")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

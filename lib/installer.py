"""
CelesteOS Installation Orchestrator
====================================
Handles the complete installation lifecycle.

States:
    UNREGISTERED -> PENDING_ACTIVATION -> ACTIVE -> OPERATIONAL

Transitions:
    UNREGISTERED: Fresh install, no credentials
        -> POST /register with yacht_id + yacht_id_hash
        -> Cloud sends activation email
        -> State becomes PENDING_ACTIVATION

    PENDING_ACTIVATION: Waiting for owner to click email link
        -> Poll POST /check-activation
        -> Returns 'pending' until owner activates
        -> Once activated, returns shared_secret ONE TIME
        -> Store in Keychain
        -> State becomes ACTIVE

    ACTIVE: Has shared_secret, can authenticate
        -> All API calls signed with HMAC-SHA256
        -> State becomes OPERATIONAL after first successful sync

    OPERATIONAL: Fully operational
        -> Normal operation, periodic health checks
"""

import os
import json
import time
import requests
from pathlib import Path
from enum import Enum
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

from .crypto import CryptoIdentity, compute_yacht_hash


class InstallState(Enum):
    """Installation state machine."""
    UNREGISTERED = "unregistered"
    PENDING_ACTIVATION = "pending_activation"
    ACTIVE = "active"
    OPERATIONAL = "operational"
    ERROR = "error"


@dataclass
class InstallConfig:
    """Installation configuration embedded in DMG."""
    yacht_id: str
    yacht_id_hash: str
    api_endpoint: str  # Supabase for check-activation, verify-credentials
    n8n_endpoint: str = "https://api.celeste7.ai/webhook"  # n8n for registration
    version: str = "1.0.0"
    build_timestamp: int = 0

    @classmethod
    def load_embedded(cls) -> 'InstallConfig':
        """Load config embedded in application bundle."""
        import sys

        # Determine if running in PyInstaller bundle
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            # Running in PyInstaller bundle
            # Resources are bundled in _MEIPASS/Resources/
            bundle_dir = Path(sys._MEIPASS)
            bundle_path = bundle_dir / 'Resources' / 'install_manifest.json'
        else:
            # Running in development or as normal Python script
            # Try relative to this file first
            bundle_path = Path(__file__).parent.parent / 'Resources' / 'install_manifest.json'

            if not bundle_path.exists():
                # Development fallback
                bundle_path = Path.home() / '.celesteos' / 'install_manifest.json'

        if not bundle_path.exists():
            raise FileNotFoundError(
                f"Installation manifest not found at {bundle_path}. "
                "This binary was not properly built or the manifest is missing."
            )

        try:
            with open(bundle_path) as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid manifest JSON: {e}")

        # Validate required fields
        required_fields = ['yacht_id', 'yacht_id_hash', 'api_endpoint']
        missing = [f for f in required_fields if f not in data]
        if missing:
            raise ValueError(f"Manifest missing required fields: {missing}")

        return cls(
            yacht_id=data['yacht_id'],
            yacht_id_hash=data['yacht_id_hash'],
            api_endpoint=data['api_endpoint'],
            n8n_endpoint=data.get('n8n_endpoint', 'https://api.celeste7.ai/webhook'),
            version=data.get('version', '1.0.0'),
            build_timestamp=data.get('build_timestamp', 0)
        )

    def verify_integrity(self) -> bool:
        """Verify manifest hasn't been tampered with."""
        expected_hash = compute_yacht_hash(self.yacht_id)
        return expected_hash == self.yacht_id_hash


class KeychainStore:
    """
    macOS Keychain integration for secure secret storage.

    Uses security(1) command for Keychain access.
    In production, use pyobjc-framework-Security for native API.
    """

    SERVICE_NAME = "com.celeste7.celesteos"

    @classmethod
    def store_secret(cls, yacht_id: str, shared_secret: str) -> bool:
        """
        Store shared_secret in Keychain.

        Args:
            yacht_id: Account name in Keychain
            shared_secret: Secret to store

        Returns:
            True if successful
        """
        import subprocess

        # Delete existing entry if present
        subprocess.run(
            ['security', 'delete-generic-password', '-s', cls.SERVICE_NAME, '-a', yacht_id],
            capture_output=True
        )

        # Add new entry
        result = subprocess.run(
            [
                'security', 'add-generic-password',
                '-s', cls.SERVICE_NAME,
                '-a', yacht_id,
                '-w', shared_secret,
                '-U'  # Update if exists
            ],
            capture_output=True
        )

        return result.returncode == 0

    @classmethod
    def retrieve_secret(cls, yacht_id: str) -> Optional[str]:
        """
        Retrieve shared_secret from Keychain.

        Args:
            yacht_id: Account name in Keychain

        Returns:
            shared_secret or None if not found
        """
        import subprocess

        result = subprocess.run(
            ['security', 'find-generic-password', '-s', cls.SERVICE_NAME, '-a', yacht_id, '-w'],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            return result.stdout.strip()
        return None

    @classmethod
    def delete_secret(cls, yacht_id: str) -> bool:
        """Delete secret from Keychain."""
        import subprocess

        result = subprocess.run(
            ['security', 'delete-generic-password', '-s', cls.SERVICE_NAME, '-a', yacht_id],
            capture_output=True
        )
        return result.returncode == 0


class InstallationOrchestrator:
    """
    Orchestrates the complete installation flow.

    This is the main entry point for installation operations.
    """

    # Polling configuration
    ACTIVATION_POLL_INTERVAL = 5  # seconds
    ACTIVATION_TIMEOUT = 3600  # 1 hour max wait

    def __init__(self, config: InstallConfig):
        self.config = config
        self.state = InstallState.UNREGISTERED
        self._crypto: Optional[CryptoIdentity] = None
        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': f'CelesteOS-Installer/{config.version}'
        })

    def initialize(self) -> InstallState:
        """
        Initialize installation state.

        Checks:
        1. Manifest integrity
        2. Existing credentials in Keychain
        3. Credential validity with server

        Returns:
            Current installation state
        """
        # Verify manifest integrity
        if not self.config.verify_integrity():
            self.state = InstallState.ERROR
            raise SecurityError("Installation manifest integrity check failed")

        # Check for existing credentials
        secret = KeychainStore.retrieve_secret(self.config.yacht_id)

        if secret:
            self._crypto = CryptoIdentity(self.config.yacht_id, secret)

            # Verify credentials are still valid
            if self._verify_credentials():
                self.state = InstallState.OPERATIONAL
            else:
                # Credentials invalid, need re-activation
                KeychainStore.delete_secret(self.config.yacht_id)
                self._crypto = None
                self.state = InstallState.UNREGISTERED
        else:
            self._crypto = CryptoIdentity(self.config.yacht_id)
            self.state = InstallState.UNREGISTERED

        return self.state

    def register(self) -> Tuple[bool, str]:
        """
        Register yacht with cloud.

        Sends yacht_id + yacht_id_hash to trigger activation email.

        Returns:
            (success, message)
        """
        if self.state not in [InstallState.UNREGISTERED, InstallState.ERROR]:
            return False, f"Cannot register from state: {self.state.value}"

        # Payload matches n8n workflow expected format
        payload = {
            'yacht_id': self.config.yacht_id,
            'yacht_id_hash': self.config.yacht_id_hash
        }

        try:
            # Use n8n endpoint for registration (sends activation email via Outlook)
            resp = self._session.post(
                f"{self.config.n8n_endpoint}/register",
                json=payload,
                timeout=30
            )

            if resp.status_code == 200:
                data = resp.json()
                if data.get('success'):
                    self.state = InstallState.PENDING_ACTIVATION
                    return True, data.get('message', 'Registration successful. Check email.')
                else:
                    return False, data.get('message', 'Registration failed')

            error = resp.json().get('message', resp.json().get('error', 'Unknown error'))
            return False, f"Registration failed: {error}"

        except requests.RequestException as e:
            return False, f"Network error: {e}"

    def poll_activation(self) -> Tuple[InstallState, Optional[str]]:
        """
        Poll for activation status.

        Returns:
            (new_state, shared_secret if activated)
        """
        if self.state != InstallState.PENDING_ACTIVATION:
            return self.state, None

        payload = {
            'yacht_id': self.config.yacht_id
        }

        try:
            resp = self._session.post(
                f"{self.config.api_endpoint}/functions/v1/check-activation",
                json=payload,
                timeout=30
            )

            if resp.status_code != 200:
                return self.state, None

            data = resp.json()
            status = data.get('status')

            if status == 'pending':
                return InstallState.PENDING_ACTIVATION, None

            elif status == 'active':
                shared_secret = data.get('shared_secret')

                if not shared_secret:
                    # Credentials already retrieved - this is a security event
                    self.state = InstallState.ERROR
                    return InstallState.ERROR, None

                # Store in Keychain immediately
                if KeychainStore.store_secret(self.config.yacht_id, shared_secret):
                    self._crypto = CryptoIdentity(self.config.yacht_id, shared_secret)
                    self.state = InstallState.ACTIVE
                    return InstallState.ACTIVE, shared_secret
                else:
                    self.state = InstallState.ERROR
                    return InstallState.ERROR, None

            elif status == 'already_retrieved':
                # Someone else got the credentials - security breach
                self.state = InstallState.ERROR
                return InstallState.ERROR, None

        except requests.RequestException:
            pass

        return self.state, None

    def wait_for_activation(self, callback=None) -> bool:
        """
        Block until activation completes or timeout.

        Args:
            callback: Optional function called each poll with (elapsed_seconds, state)

        Returns:
            True if activated successfully
        """
        start = time.time()

        while time.time() - start < self.ACTIVATION_TIMEOUT:
            state, secret = self.poll_activation()

            if callback:
                callback(time.time() - start, state)

            if state == InstallState.ACTIVE:
                return True

            if state == InstallState.ERROR:
                return False

            time.sleep(self.ACTIVATION_POLL_INTERVAL)

        return False

    def _verify_credentials(self) -> bool:
        """Verify stored credentials are still valid."""
        if not self._crypto or not self._crypto.has_secret:
            return False

        try:
            # Make authenticated request to health endpoint
            payload = {'action': 'verify'}
            headers = self._crypto.sign_request(payload)

            resp = self._session.post(
                f"{self.config.api_endpoint}/functions/v1/verify-credentials",
                json=payload,
                headers=headers,
                timeout=10
            )

            return resp.status_code == 200

        except requests.RequestException:
            return False

    def get_signed_headers(self, payload: Dict[str, Any]) -> Dict[str, str]:
        """Get HMAC-signed headers for an API request."""
        if not self._crypto or not self._crypto.has_secret:
            raise SecurityError("No credentials available for signing")

        return self._crypto.sign_request(payload)


class SecurityError(Exception):
    """Security-related errors during installation."""
    pass


# CLI Entry Point
def run_installation():
    """Run interactive installation from command line."""
    print("=" * 60)
    print("CelesteOS Installation")
    print("=" * 60)

    try:
        config = InstallConfig.load_embedded()
        print(f"Yacht ID: {config.yacht_id}")
        print(f"Version:  {config.version}")

        orchestrator = InstallationOrchestrator(config)
        state = orchestrator.initialize()

        print(f"State:    {state.value}")

        if state == InstallState.OPERATIONAL:
            print("\n✓ Already activated and operational")
            return True

        if state == InstallState.UNREGISTERED:
            print("\nRegistering with cloud...")
            success, message = orchestrator.register()
            print(f"  {message}")

            if not success:
                return False

        if orchestrator.state == InstallState.PENDING_ACTIVATION:
            print("\nWaiting for activation...")
            print("(Check email and click activation link)")

            def progress(elapsed, state):
                mins = int(elapsed // 60)
                secs = int(elapsed % 60)
                print(f"\r  Waiting... {mins:02d}:{secs:02d}", end='', flush=True)

            if orchestrator.wait_for_activation(callback=progress):
                print("\n\n✓ Activation successful!")
                print("  Credentials stored in Keychain")
                return True
            else:
                print("\n\n✗ Activation failed or timed out")
                return False

    except FileNotFoundError as e:
        print(f"\n✗ Error: {e}")
        return False

    except SecurityError as e:
        print(f"\n✗ Security Error: {e}")
        return False


if __name__ == '__main__':
    run_installation()

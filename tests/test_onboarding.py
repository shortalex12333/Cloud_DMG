"""
Unit tests for onboarding workflows
Tests the Python implementation against expected behavior
"""
import pytest
from unittest.mock import patch, MagicMock
from workflows.onboarding.register import handle_register
from workflows.onboarding.check_activation import handle_check_activation
from workflows.onboarding.activate import handle_activate
from core.validation.schemas import RegisterRequest


class TestRegisterEndpoint:
    """Tests for POST /register endpoint"""

    @patch('workflows.onboarding.register.lookup_yacht')
    @patch('workflows.onboarding.register.update_registration_timestamp')
    def test_register_success(self, mock_update_ts, mock_lookup):
        """Test successful registration"""
        # Mock database response
        mock_lookup.return_value = {
            "yacht_id": "TEST_YACHT_001",
            "yacht_id_hash": "a" * 64,
            "buyer_email": "test@example.com",
            "active": False
        }

        # Create request
        request = RegisterRequest(
            yacht_id="TEST_YACHT_001",
            yacht_id_hash="a" * 64
        )

        # Execute
        result = handle_register(request)

        # Assertions
        assert result["success"] is True
        assert "activation_link" in result
        assert "TEST_YACHT_001" in result["activation_link"]
        mock_lookup.assert_called_once()
        mock_update_ts.assert_called_once_with("TEST_YACHT_001")

    def test_register_invalid_yacht_id(self):
        """Test registration with invalid yacht_id format"""
        request = RegisterRequest(
            yacht_id="invalid!@#",  # Invalid characters
            yacht_id_hash="a" * 64
        )

        # This should raise validation error from Pydantic
        with pytest.raises(Exception):
            handle_register(request)

    def test_register_invalid_hash(self):
        """Test registration with invalid hash format"""
        # This should raise validation error from Pydantic
        with pytest.raises(Exception):
            RegisterRequest(
                yacht_id="TEST_YACHT_001",
                yacht_id_hash="short"  # Too short
            )

    @patch('workflows.onboarding.register.lookup_yacht')
    def test_register_yacht_not_found(self, mock_lookup):
        """Test registration when yacht doesn't exist"""
        mock_lookup.return_value = None

        request = RegisterRequest(
            yacht_id="TEST_YACHT_999",
            yacht_id_hash="a" * 64
        )

        result = handle_register(request)

        assert result["success"] is False
        assert result["error"] == "yacht_not_found"

    @patch('workflows.onboarding.register.lookup_yacht')
    def test_register_no_buyer_email(self, mock_lookup):
        """Test registration when buyer_email is missing"""
        mock_lookup.return_value = {
            "yacht_id": "TEST_YACHT_001",
            "yacht_id_hash": "a" * 64,
            "buyer_email": None,  # No email
            "active": False
        }

        request = RegisterRequest(
            yacht_id="TEST_YACHT_001",
            yacht_id_hash="a" * 64
        )

        result = handle_register(request)

        assert result["success"] is False
        assert result["error"] == "no_buyer_email"


class TestCheckActivationEndpoint:
    """Tests for POST /check-activation/:yacht_id endpoint"""

    @patch('workflows.onboarding.check_activation.lookup_status')
    def test_check_activation_pending(self, mock_lookup):
        """Test checking activation status when pending"""
        mock_lookup.return_value = {
            "yacht_id": "TEST_YACHT_001",
            "active": False,
            "credentials_retrieved": False
        }

        result = handle_check_activation("TEST_YACHT_001")

        assert result["status"] == "pending"
        assert "Waiting for owner activation" in result["message"]

    @patch('workflows.onboarding.check_activation.lookup_status')
    @patch('workflows.onboarding.check_activation.mark_credentials_retrieved')
    def test_check_activation_active_first_time(self, mock_mark, mock_lookup):
        """Test retrieving credentials for the first time"""
        mock_lookup.return_value = {
            "yacht_id": "TEST_YACHT_001",
            "active": True,
            "credentials_retrieved": False,
            "shared_secret": "a" * 64
        }

        result = handle_check_activation("TEST_YACHT_001")

        assert result["status"] == "active"
        assert result["shared_secret"] == "a" * 64
        assert "supabase_url" in result
        mock_mark.assert_called_once_with("TEST_YACHT_001")

    @patch('workflows.onboarding.check_activation.lookup_status')
    def test_check_activation_already_retrieved(self, mock_lookup):
        """Test attempting to retrieve credentials again"""
        mock_lookup.return_value = {
            "yacht_id": "TEST_YACHT_001",
            "active": True,
            "credentials_retrieved": True,
            "shared_secret": "a" * 64
        }

        result = handle_check_activation("TEST_YACHT_001")

        assert result["status"] == "already_retrieved"
        assert "shared_secret" not in result

    @patch('workflows.onboarding.check_activation.lookup_status')
    def test_check_activation_not_found(self, mock_lookup):
        """Test checking status for non-existent yacht"""
        mock_lookup.return_value = None

        result = handle_check_activation("NONEXISTENT")

        assert result["success"] is False
        assert result["error"] == "yacht_not_found"


class TestActivateEndpoint:
    """Tests for GET /activate/:yacht_id endpoint"""

    @patch('workflows.onboarding.activate.lookup_for_activation')
    @patch('workflows.onboarding.activate.activate_yacht')
    def test_activate_success(self, mock_activate, mock_lookup):
        """Test successful yacht activation"""
        mock_lookup.return_value = None  # Not already active
        mock_activate.return_value = {
            "yacht_id": "TEST_YACHT_001",
            "active": True,
            "shared_secret": "a" * 64
        }

        html, status = handle_activate("TEST_YACHT_001")

        assert status == 200
        assert "Yacht Activated!" in html
        assert "TEST_YACHT_001" in html
        mock_activate.assert_called_once_with("TEST_YACHT_001")

    @patch('workflows.onboarding.activate.lookup_for_activation')
    def test_activate_already_active(self, mock_lookup):
        """Test activating yacht that's already active"""
        mock_lookup.return_value = {"yacht_id": "TEST_YACHT_001", "active": True}

        html, status = handle_activate("TEST_YACHT_001")

        assert status == 400
        assert "already been activated" in html

    def test_activate_invalid_yacht_id(self):
        """Test activation with invalid yacht_id"""
        html, status = handle_activate("invalid!@#")

        assert status == 400
        assert "Error" in html or "error" in html


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

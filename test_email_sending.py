#!/usr/bin/env python3
"""
Test Email Sending with Microsoft Graph API
"""
from dotenv import load_dotenv
import os

load_dotenv()

from core.email.sender import send_activation_email

def test_email():
    """Test sending a real activation email"""
    print("=" * 70)
    print("📧 Testing Email Sending via Microsoft Graph API")
    print("=" * 70)
    print()

    # Check credentials
    required = ["AZURE_TENANT_ID", "AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET", "SENDER_EMAIL"]
    missing = [key for key in required if not os.getenv(key)]

    if missing:
        print("❌ Missing credentials:")
        for key in missing:
            print(f"   - {key}")
        print("\nPlease add these to .env file")
        return False

    print("✅ Credentials loaded:")
    print(f"   Tenant ID: {os.getenv('AZURE_TENANT_ID')[:20]}...")
    print(f"   Client ID: {os.getenv('AZURE_CLIENT_ID')[:20]}...")
    print(f"   Sender: {os.getenv('SENDER_EMAIL')}")
    print()

    # Test email
    test_recipient = os.getenv("SENDER_EMAIL")  # Send to self for testing
    print(f"📨 Sending test email to: {test_recipient}")
    print()

    result = send_activation_email(
        to=test_recipient,
        subject="Test: Yacht Activation Email",
        html="""
        <h2>Test Email</h2>
        <p>This is a test of the yacht activation email system.</p>
        <p>If you receive this, email sending is working!</p>
        <a href="https://api.celeste7.ai/webhook/activate/TEST_YACHT">Activate Yacht</a>
        """,
        text="Test email - if you receive this, email sending is working!"
    )

    print()
    print("=" * 70)
    print("RESULT:")
    print("=" * 70)

    if result.get("success"):
        print("✅ Email sent successfully!")
        print(f"   Check {test_recipient} for the test email")
        return True
    else:
        print("❌ Email failed to send")
        print(f"   Error: {result.get('error')}")
        print()
        print("🔍 Common issues:")
        print("   1. Azure app needs 'Mail.Send' application permission")
        print("   2. Admin consent required for Mail.Send permission")
        print("   3. Sender email must exist in the tenant")
        print()
        print("📝 To fix:")
        print("   1. Go to https://portal.azure.com")
        print("   2. Azure AD > App registrations > CelesteOS")
        print("   3. API Permissions > Add permission")
        print("   4. Microsoft Graph > Application permissions > Mail.Send")
        print("   5. Grant admin consent")
        return False

if __name__ == "__main__":
    success = test_email()
    exit(0 if success else 1)

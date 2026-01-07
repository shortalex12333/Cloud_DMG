"""
Email Sender Module - Unified Interface
Tries multiple email sending methods in order:
1. Microsoft Graph API (if configured with Mail.Send permission)
2. SMTP (if SMTP credentials provided)
3. Fallback: Print activation link to console
"""
import os
import requests
from typing import Dict, Any, Optional
import json


class EmailSender:
    """Handles email sending via Microsoft Graph API"""

    def __init__(self):
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.sender_email = os.getenv("SENDER_EMAIL")

        if not all([self.tenant_id, self.client_id, self.client_secret, self.sender_email]):
            raise ValueError("Missing required email credentials in .env file")

    def get_access_token(self) -> str:
        """
        Get access token using client credentials flow
        This requires Mail.Send application permission in Azure AD
        """
        token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "https://graph.microsoft.com/.default",
            "grant_type": "client_credentials"
        }

        response = requests.post(token_url, data=data)

        if response.status_code != 200:
            raise Exception(f"Failed to get access token: {response.status_code} - {response.text}")

        return response.json()["access_token"]

    def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: str
    ) -> Dict[str, Any]:
        """
        Send email using Microsoft Graph API

        Args:
            to: Recipient email address
            subject: Email subject
            html: HTML body
            text: Plain text body

        Returns:
            Dict with success status and message
        """
        try:
            # Get access token
            access_token = self.get_access_token()

            # Prepare email message
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": html
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": to
                            }
                        }
                    ]
                },
                "saveToSentItems": "true"
            }

            # Send email via Graph API
            send_url = f"https://graph.microsoft.com/v1.0/users/{self.sender_email}/sendMail"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }

            response = requests.post(send_url, headers=headers, json=message)

            if response.status_code in [200, 202]:
                return {
                    "success": True,
                    "message": f"Email sent to {to}"
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to send email: {response.status_code} - {response.text}"
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


def send_activation_email(to: str, subject: str, html: str, text: str) -> Dict[str, Any]:
    """
    Unified function to send activation email
    Tries multiple methods in order:
    1. Microsoft Graph API (requires Mail.Send application permission)
    2. SMTP (requires SMTP_USER and SMTP_PASSWORD)
    3. Fallback: Returns activation link for manual sending

    Args:
        to: Recipient email address
        subject: Email subject
        html: HTML body
        text: Plain text body (fallback)

    Returns:
        Dict with success status and method used
    """
    # Extract activation link from HTML for fallback
    import re
    activation_link_match = re.search(r'https://api\.celeste7\.ai/webhook/activate/[A-Z0-9_-]+', html)
    activation_link = activation_link_match.group(0) if activation_link_match else None

    # Method 1: Try Microsoft Graph API
    if all([os.getenv("AZURE_TENANT_ID"), os.getenv("AZURE_CLIENT_ID"), os.getenv("AZURE_CLIENT_SECRET")]):
        try:
            sender = EmailSender()
            result = sender.send_email(to, subject, html, text)
            if result.get("success"):
                result["method"] = "Microsoft Graph API"
                return result
            else:
                print(f"[EMAIL] Graph API failed: {result.get('error')}")
        except Exception as e:
            print(f"[EMAIL] Graph API exception: {e}")

    # Method 2: Try SMTP
    if all([os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD")]):
        try:
            from core.email.smtp_sender import send_activation_email_smtp
            result = send_activation_email_smtp(to, subject, html, text)
            if result.get("success"):
                result["method"] = "SMTP"
                return result
            else:
                print(f"[EMAIL] SMTP failed: {result.get('error')}")
        except Exception as e:
            print(f"[EMAIL] SMTP exception: {e}")

    # Method 3: Fallback - Return link for manual sending
    return {
        "success": False,
        "method": "manual_fallback",
        "error": "No email service configured",
        "activation_link": activation_link,
        "message": f"Email sending not configured. Activation link: {activation_link}"
    }

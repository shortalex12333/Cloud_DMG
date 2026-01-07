"""
SMTP Email Sender - Fallback for Microsoft Graph API
Sends activation emails using Office 365 SMTP
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any


class SMTPSender:
    """Handles email sending via SMTP"""

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp-mail.outlook.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.sender_email = os.getenv("SENDER_EMAIL", self.smtp_user)
        self.sender_name = os.getenv("SENDER_NAME", "Celeste7 Yacht Onboarding")

        if not all([self.smtp_user, self.smtp_password]):
            raise ValueError("Missing SMTP_USER or SMTP_PASSWORD in .env file")

    def send_email(
        self,
        to: str,
        subject: str,
        html: str,
        text: str
    ) -> Dict[str, Any]:
        """
        Send email using SMTP

        Args:
            to: Recipient email address
            subject: Email subject
            html: HTML body
            text: Plain text body

        Returns:
            Dict with success status and message
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = to
            msg['Subject'] = subject

            # Attach both plain text and HTML versions
            part1 = MIMEText(text, 'plain')
            part2 = MIMEText(html, 'html')
            msg.attach(part1)
            msg.attach(part2)

            # Connect to SMTP server and send
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.sender_email, to, msg.as_string())

            return {
                "success": True,
                "message": f"Email sent to {to} via SMTP"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"SMTP error: {str(e)}"
            }


def send_activation_email_smtp(to: str, subject: str, html: str, text: str) -> Dict[str, Any]:
    """
    Convenience function to send activation email via SMTP

    Args:
        to: Recipient email address
        subject: Email subject
        html: HTML body
        text: Plain text body

    Returns:
        Dict with success status
    """
    sender = SMTPSender()
    return sender.send_email(to, subject, html, text)

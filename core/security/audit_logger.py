"""
Military-Grade Audit Logging
Structured JSON logs for forensic analysis and compliance
"""
import logging
import sys
from pythonjsonlogger import jsonlogger


class SecurityAuditFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter for security events.

    Includes:
    - Timestamp (ISO 8601)
    - Log level
    - Message
    - Request ID (for correlation)
    - Client IP
    - User agent
    - Custom fields
    """
    def add_fields(self, log_record, record, message_dict):
        super(SecurityAuditFormatter, self).add_fields(log_record, record, message_dict)

        # Always include these fields
        log_record['timestamp'] = record.created
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        log_record['event'] = record.getMessage()


# Create security logger
security_logger = logging.getLogger('celeste7.security')
security_logger.setLevel(logging.INFO)

# Console handler with JSON formatting
console_handler = logging.StreamHandler(sys.stdout)
formatter = SecurityAuditFormatter(
    '%(timestamp)s %(level)s %(event)s %(request_id)s %(client_ip)s'
)
console_handler.setFormatter(formatter)
security_logger.addHandler(console_handler)

# Prevent duplicate logs from root logger
security_logger.propagate = False


# Application logger (for business logic, not security events)
app_logger = logging.getLogger('celeste7.app')
app_logger.setLevel(logging.INFO)

app_handler = logging.StreamHandler(sys.stdout)
app_formatter = SecurityAuditFormatter(
    '%(timestamp)s %(level)s %(message)s'
)
app_handler.setFormatter(app_formatter)
app_logger.addHandler(app_handler)
app_logger.propagate = False


# Convenience functions for common security events
def log_registration_attempt(yacht_id: str, client_ip: str, request_id: str, success: bool):
    """Log yacht registration attempt"""
    if success:
        security_logger.info("yacht_registration_success", extra={
            "yacht_id": yacht_id,
            "client_ip": client_ip,
            "request_id": request_id,
        })
    else:
        security_logger.warning("yacht_registration_failed", extra={
            "yacht_id": yacht_id,
            "client_ip": client_ip,
            "request_id": request_id,
        })


def log_activation_attempt(yacht_id: str, client_ip: str, request_id: str, success: bool):
    """Log yacht activation attempt"""
    if success:
        security_logger.info("yacht_activation_success", extra={
            "yacht_id": yacht_id,
            "client_ip": client_ip,
            "request_id": request_id,
        })
    else:
        security_logger.warning("yacht_activation_failed", extra={
            "yacht_id": yacht_id,
            "client_ip": client_ip,
            "request_id": request_id,
        })


def log_credential_retrieval(yacht_id: str, client_ip: str, request_id: str, status: str):
    """Log credential retrieval attempt"""
    security_logger.info("credential_retrieval", extra={
        "yacht_id": yacht_id,
        "client_ip": client_ip,
        "request_id": request_id,
        "status": status,  # "success", "already_retrieved", "pending"
    })


def log_rate_limit_exceeded(endpoint: str, client_ip: str, limit: str):
    """Log rate limit violations (potential attack)"""
    security_logger.warning("rate_limit_exceeded", extra={
        "endpoint": endpoint,
        "client_ip": client_ip,
        "limit": limit,
        "severity": "high",  # Rate limit violations indicate potential attack
    })


def log_suspicious_activity(activity_type: str, details: dict):
    """Log suspicious activity for security team investigation"""
    security_logger.warning("suspicious_activity", extra={
        "activity_type": activity_type,
        "severity": "critical",
        **details
    })

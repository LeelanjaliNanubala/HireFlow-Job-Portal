"""Helper to write audit records."""
from .models import AuditLog


def log_action(actor, action, target='', details=''):
    return AuditLog.objects.create(actor=actor, action=action, target=str(target)[:200], details=details)

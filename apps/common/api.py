"""Shared REST API helpers: consistent errors and permission classes."""
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import permissions
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import exception_handler

from .exceptions import ServiceError


def error_response(message, code, http_status, details=None):
    return Response(
        {'error': {'status': http_status, 'code': code, 'message': message, 'details': details}},
        status=http_status,
    )


def api_exception_handler(exc, context):
    """Every API error has the same JSON shape: {"error": {status, code, message, details}}."""
    if isinstance(exc, ServiceError):
        return error_response(exc.message, exc.code, exc.status)
    if isinstance(exc, DjangoValidationError):
        return error_response('Validation failed.', 'invalid', 400, exc.messages)

    response = exception_handler(exc, context)
    if response is None:
        return None  # Unexpected error: Django will return a 500 page.

    data = response.data
    if isinstance(exc, ValidationError):
        message, code, details = 'Validation failed.', 'invalid', data
    else:
        message = data.get('detail', 'Request failed.') if isinstance(data, dict) else 'Request failed.'
        code = exc.get_codes() if hasattr(exc, 'get_codes') else 'error'
        if not isinstance(code, str):
            code = 'error'
        details = None
    response.data = {
        'error': {'status': response.status_code, 'code': code, 'message': str(message), 'details': details}
    }
    return response


class IsCandidate(permissions.BasePermission):
    message = 'Only candidates can perform this action.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.role == 'candidate')


class IsRecruiterWithCompany(permissions.BasePermission):
    message = 'Only recruiters linked to a company can perform this action.'

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.role == 'recruiter'):
            return False
        profile = getattr(user, 'recruiter_profile', None)
        return bool(profile and profile.company_id)

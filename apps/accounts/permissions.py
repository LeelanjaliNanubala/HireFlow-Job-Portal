"""Server-side role checks. Hiding a button is NOT security - these decorators are."""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect


def role_required(*roles):
    """Allow only logged-in users whose role is in `roles`; others get a 403 page."""

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return login_required(_wrapped)

    return decorator


candidate_required = role_required('candidate')
admin_required = role_required('admin')


def recruiter_required(view_func):
    """Recruiter who is linked to a company. Sets request.company for the view."""

    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        profile = getattr(request.user, 'recruiter_profile', None)
        if profile is None or profile.company_id is None:
            messages.warning(request, 'Your recruiter account is not linked to a company yet. '
                                      'Please contact an administrator.')
            return redirect('home')
        request.recruiter_profile = profile
        request.company = profile.company
        return view_func(request, *args, **kwargs)

    return role_required('recruiter')(_wrapped)


def recruiter_company_id(user):
    """Company id of a recruiter, or None."""
    if not user.is_authenticated or user.role != 'recruiter':
        return None
    profile = getattr(user, 'recruiter_profile', None)
    return profile.company_id if profile else None

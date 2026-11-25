"""Small helpers used by several apps."""
from django.utils.http import url_has_allowed_host_and_scheme


def safe_next(request, default):
    """Return the ?next= / POST next value only if it points to this website."""
    target = request.POST.get('next') or request.GET.get('next')
    if target and url_has_allowed_host_and_scheme(
        target, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return target
    return default

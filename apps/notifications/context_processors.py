from .models import Notification


def notifications(request):
    """Adds the unread notification count to every template (used by the navbar bell)."""
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        return {'unread_notification_count': Notification.objects.filter(user=user, is_read=False).count()}
    return {}

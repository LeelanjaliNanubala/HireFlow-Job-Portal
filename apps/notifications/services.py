"""Create in-app notifications (and optionally send email when EMAIL_ENABLED=True)."""
from django.conf import settings
from django.core.mail import send_mail

from .models import Notification


def notify(user, title, message, notification_type=Notification.Type.SYSTEM, link=''):
    notification = Notification.objects.create(user=user, title=title, message=message,
                                               notification_type=notification_type, link=link)
    if settings.EMAIL_NOTIFICATIONS_ENABLED and user.email:
        send_mail(f'HireFlow: {title}', message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=True)
    return notification


def notify_company_recruiters(company, title, message, notification_type=Notification.Type.APPLICATION, link=''):
    """Notify every recruiter that belongs to the company."""
    for profile in company.recruiters.select_related('user'):
        notify(profile.user, title, message, notification_type, link)

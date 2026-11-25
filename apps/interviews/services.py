"""Interview scheduling rules."""
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.applications.services import Status, change_status
from apps.common.exceptions import ServiceError
from apps.notifications.models import Notification
from apps.notifications.services import notify

from .models import Interview

# An interview can be scheduled when the application is in one of these statuses.
INTERVIEWABLE = (Status.SHORTLISTED, Status.INTERVIEW_SCHEDULED, Status.INTERVIEW_COMPLETED)
NOTIFY_FIELDS = {'scheduled_at', 'mode', 'meeting_details', 'status', 'duration_minutes', 'interviewer_name'}


def _candidate_link():
    return reverse('interviews:mine')


@transaction.atomic
def schedule_interview(*, application, actor, scheduled_at, mode, meeting_details='', interviewer_name='',
                       duration_minutes=30):
    if application.status not in INTERVIEWABLE:
        raise ServiceError('Shortlist the candidate before scheduling an interview.', 'invalid_status', 400)
    if scheduled_at <= timezone.now():
        raise ServiceError('The interview must be scheduled in the future.', 'invalid_time', 400)
    if mode == Interview.Mode.ONLINE and not meeting_details:
        raise ServiceError('Add a meeting link for an online interview.', 'missing_meeting_details', 400)

    interview = Interview.objects.create(
        application=application, round_number=application.interviews.count() + 1, scheduled_at=scheduled_at,
        mode=mode, meeting_details=meeting_details, interviewer_name=interviewer_name,
        duration_minutes=duration_minutes, created_by=actor)
    if application.status != Status.INTERVIEW_SCHEDULED:
        change_status(application=application, new_status=Status.INTERVIEW_SCHEDULED, actor=actor,
                      note=f'Interview round {interview.round_number} scheduled.')
    notify(application.candidate.user, 'Interview scheduled',
           f'Interview for {application.job.title} on '
           f'{timezone.localtime(scheduled_at):%d %b %Y at %H:%M}.',
           Notification.Type.INTERVIEW, _candidate_link())
    return interview


@transaction.atomic
def update_interview(*, interview, actor, **fields):
    changed = set()
    for name, value in fields.items():
        if getattr(interview, name) != value:
            changed.add(name)
            setattr(interview, name, value)
    interview.save()

    application = interview.application
    if ('status' in changed and interview.status == Interview.Status.COMPLETED
            and application.status == Status.INTERVIEW_SCHEDULED
            and not application.interviews.filter(status=Interview.Status.SCHEDULED).exists()):
        change_status(application=application, new_status=Status.INTERVIEW_COMPLETED, actor=actor,
                      note='Interview completed.')
    if changed & NOTIFY_FIELDS:
        notify(application.candidate.user, 'Interview updated',
               f'Your interview for {application.job.title} was updated. Please check the details.',
               Notification.Type.INTERVIEW, _candidate_link())
    return interview

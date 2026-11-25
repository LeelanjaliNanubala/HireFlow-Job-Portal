"""Application business rules. Views and the REST API both call these functions."""
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.common.exceptions import ServiceError
from apps.jobs.models import Job
from apps.notifications.models import Notification
from apps.notifications.services import notify, notify_company_recruiters

from .models import ApplicationHistory, JobApplication

Status = JobApplication.Status

# Allowed status changes (current status -> possible next statuses).
TRANSITIONS = {
    Status.SUBMITTED: [Status.UNDER_REVIEW, Status.SHORTLISTED, Status.REJECTED, Status.WITHDRAWN],
    Status.UNDER_REVIEW: [Status.SHORTLISTED, Status.REJECTED, Status.WITHDRAWN],
    Status.SHORTLISTED: [Status.INTERVIEW_SCHEDULED, Status.REJECTED, Status.WITHDRAWN],
    Status.INTERVIEW_SCHEDULED: [Status.INTERVIEW_COMPLETED, Status.REJECTED, Status.WITHDRAWN],
    Status.INTERVIEW_COMPLETED: [Status.SELECTED, Status.REJECTED, Status.INTERVIEW_SCHEDULED, Status.WITHDRAWN],
    Status.SELECTED: [],
    Status.REJECTED: [],
    Status.WITHDRAWN: [],
}

# Statuses a recruiter may choose by hand. "Interview Scheduled" is set automatically when an
# interview is scheduled, and "Withdrawn" can only be chosen by the candidate.
RECRUITER_SETTABLE = [Status.UNDER_REVIEW, Status.SHORTLISTED, Status.INTERVIEW_COMPLETED,
                      Status.SELECTED, Status.REJECTED]


def recruiter_next_statuses(application):
    """(value, label) pairs the recruiter can move this application to right now."""
    allowed = [s for s in TRANSITIONS[application.status] if s in RECRUITER_SETTABLE]
    return [(s.value, s.label) for s in allowed]


@transaction.atomic
def apply_to_job(*, candidate, job_id, resume_id, cover_letter=''):
    """Create an application, its first history row and the notifications - all or nothing."""
    job = Job.objects.select_related('company').filter(pk=job_id).first()
    if job is None:
        raise ServiceError('Job not found.', 'job_not_found', 404)
    if not job.is_open:
        raise ServiceError('This job is not open for applications (closed, unpublished or expired).',
                           'job_not_open', 400)
    resume = candidate.resumes.filter(pk=resume_id).first()
    if resume is None:
        raise ServiceError('Choose one of your own uploaded resumes.', 'invalid_resume', 400)
    if JobApplication.objects.filter(job=job, candidate=candidate).exists():
        raise ServiceError('You have already applied for this job.', 'duplicate_application', 409)

    try:
        with transaction.atomic():  # savepoint: the database unique constraint is the final safety net
            application = JobApplication.objects.create(job=job, candidate=candidate, resume=resume,
                                                        cover_letter=cover_letter.strip())
    except IntegrityError:
        raise ServiceError('You have already applied for this job.', 'duplicate_application', 409)

    ApplicationHistory.objects.create(application=application, changed_by=candidate.user, old_status='',
                                      new_status=Status.SUBMITTED, note='Application submitted.')
    notify(candidate.user, 'Application submitted',
           f'You applied for {job.title} at {job.company.name}.', Notification.Type.APPLICATION,
           reverse('applications:detail', args=[application.pk]))
    notify_company_recruiters(job.company, 'New application',
                              f'{candidate.user.full_name or candidate.user.email} applied for {job.title}.',
                              Notification.Type.APPLICATION, reverse('applications:review', args=[application.pk]))
    return application


@transaction.atomic
def change_status(*, application, new_status, actor, note=''):
    """Move an application to a new status, record history and notify the candidate."""
    application = JobApplication.objects.select_for_update().select_related(
        'job__company', 'candidate__user').get(pk=application.pk)
    old_status = application.status
    if new_status not in Status.values:
        raise ServiceError('Unknown application status.', 'invalid_status', 400)
    if new_status == old_status:
        raise ServiceError('The application already has this status.', 'same_status', 400)
    if new_status not in [s.value for s in TRANSITIONS[old_status]]:
        raise ServiceError(f'An application that is "{application.get_status_display()}" '
                           f'cannot be changed to "{Status(new_status).label}".', 'invalid_transition', 400)

    application.status = new_status
    application.save(update_fields=['status', 'updated_at'])
    ApplicationHistory.objects.create(application=application, changed_by=actor, old_status=old_status,
                                      new_status=new_status, note=note.strip())
    notify(application.candidate.user, 'Application status updated',
           f'Your application for {application.job.title} is now: {Status(new_status).label}.',
           Notification.Type.STATUS, reverse('applications:detail', args=[application.pk]))
    return application


def can_manage_application(user, application):
    """True if the user is a recruiter of the company that owns the job."""
    profile = getattr(user, 'recruiter_profile', None)
    return bool(user.is_authenticated and user.role == 'recruiter' and profile
                and profile.company_id == application.job.company_id)

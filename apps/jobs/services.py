"""Job business logic: search, skills and status changes."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.candidates.services import get_or_create_skill
from apps.common.exceptions import ServiceError

from .models import Job, JobSkill

# Which status changes are allowed.
JOB_TRANSITIONS = {
    Job.Status.DRAFT: [Job.Status.PUBLISHED, Job.Status.CLOSED],
    Job.Status.PUBLISHED: [Job.Status.PAUSED, Job.Status.CLOSED],
    Job.Status.PAUSED: [Job.Status.PUBLISHED, Job.Status.CLOSED],
    Job.Status.CLOSED: [Job.Status.PUBLISHED],
}

SORT_OPTIONS = {
    'newest': ('-published_at', '-id'),
    'deadline': ('deadline', '-id'),
    'salary': ('-salary_max', '-id'),
    'title': ('title', '-id'),
}


def search_jobs(params):
    """Search public jobs. `params` is request.GET or request.query_params."""
    qs = Job.objects.public().select_related('company').prefetch_related('job_skills__skill')

    keyword = (params.get('q') or '').strip()
    if keyword:
        qs = qs.filter(
            Q(title__icontains=keyword) | Q(description__icontains=keyword)
            | Q(company__name__icontains=keyword) | Q(skills__name__icontains=keyword)
        ).distinct()

    location = (params.get('location') or '').strip()
    if location:
        qs = qs.filter(location__icontains=location)

    employment_type = (params.get('employment_type') or '').strip()
    if employment_type in Job.EmploymentType.values:
        qs = qs.filter(employment_type=employment_type)

    experience = (params.get('experience') or '').strip()
    if experience.isdigit():
        years = int(experience)
        qs = qs.filter(experience_min__lte=years, experience_max__gte=years)

    sort = SORT_OPTIONS.get(params.get('sort'), SORT_OPTIONS['newest'])
    return qs.order_by(*sort)


def parse_skill_names(text):
    """'Python, django ,MySQL' -> ['Python', 'django', 'MySQL'] (no duplicates)."""
    seen, names = set(), []
    for part in (text or '').split(','):
        name = ' '.join(part.split())
        if name and name.lower() not in seen:
            seen.add(name.lower())
            names.append(name[:60])
    return names


@transaction.atomic
def set_job_skills(job, names):
    """Make the job's skills exactly match `names`."""
    wanted = {}
    for name in names:
        skill = get_or_create_skill(name)
        wanted[skill.pk] = skill
    JobSkill.objects.filter(job=job).exclude(skill_id__in=wanted.keys()).delete()
    existing = set(JobSkill.objects.filter(job=job).values_list('skill_id', flat=True))
    for skill_id in wanted:
        if skill_id not in existing:
            JobSkill.objects.create(job=job, skill_id=skill_id)


@transaction.atomic
def change_job_status(job, new_status, actor=None):
    """Publish, pause, close or reopen a job, following JOB_TRANSITIONS."""
    if new_status not in Job.Status.values:
        raise ServiceError('Unknown job status.', 'invalid_status', 400)
    if new_status == job.status:
        return job
    if new_status not in JOB_TRANSITIONS[job.status]:
        raise ServiceError(f'A {job.get_status_display().lower()} job cannot become {new_status}.',
                           'invalid_transition', 400)
    if new_status == Job.Status.PUBLISHED:
        if not job.company.is_verified:
            raise ServiceError('Your company must be verified by an administrator before you can publish jobs.',
                               'company_not_verified', 403)
        if job.deadline < timezone.localdate():
            raise ServiceError('Change the deadline to a future date before publishing.', 'deadline_passed', 400)
        job.published_at = job.published_at or timezone.now()
        job.closed_at = None
    if new_status == Job.Status.CLOSED:
        job.closed_at = timezone.now()
    job.status = new_status
    job.save()
    return job

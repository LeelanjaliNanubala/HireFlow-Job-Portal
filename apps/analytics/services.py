"""Dashboard numbers and chart data. Everything is calculated from real database records."""
import datetime
from collections import Counter

from django.contrib.auth import get_user_model
from django.db.models import Count
from django.utils import timezone

from apps.applications.models import JobApplication
from apps.companies.models import Company
from apps.interviews.models import Interview
from apps.jobs.models import Job

Status = JobApplication.Status


def _choice_chart(queryset, field, choices, label):
    """Counts per choice (including zeros) in the format charts.js expects."""
    counts = dict(queryset.values_list(field).annotate(total=Count('id')).order_by())
    return {
        'labels': [text for _, text in choices],
        'values': [counts.get(value, 0) for value, _ in choices],
        'label': label,
    }


def _daily_chart(queryset, field, label, days=14):
    """Records per day for the last `days` days (grouped in Python so any database/time zone works)."""
    today = timezone.localdate()
    start = today - datetime.timedelta(days=days - 1)
    start_dt = timezone.make_aware(datetime.datetime.combine(start, datetime.time.min))
    counter = Counter(timezone.localtime(value).date()
                      for value in queryset.filter(**{f'{field}__gte': start_dt}).values_list(field, flat=True))
    labels, values = [], []
    for offset in range(days):
        day = start + datetime.timedelta(days=offset)
        labels.append(day.strftime('%d %b'))
        values.append(counter.get(day, 0))
    return {'labels': labels, 'values': values, 'label': label}


def candidate_dashboard(profile):
    applications = JobApplication.objects.filter(candidate=profile)
    now = timezone.now()
    upcoming = (Interview.objects.filter(application__candidate=profile, status=Interview.Status.SCHEDULED,
                                         scheduled_at__gte=now)
                .select_related('application__job__company').order_by('scheduled_at'))
    return {
        'stats': {
            'total': applications.count(),
            'under_review': applications.filter(status=Status.UNDER_REVIEW).count(),
            'shortlisted': applications.filter(status=Status.SHORTLISTED).count(),
            'upcoming_interviews': upcoming.count(),
        },
        'recent_applications': applications.select_related('job__company')[:5],
        'upcoming_interviews': upcoming[:5],
        'status_chart': _choice_chart(applications, 'status', Status.choices, 'Applications'),
        'completeness': profile.completeness(),
    }


def recruiter_dashboard(company):
    jobs = Job.objects.filter(company=company)
    applications = JobApplication.objects.filter(job__company=company)
    now = timezone.now()
    per_job = jobs.annotate(total=Count('applications')).filter(total__gt=0).order_by('-total')[:6]
    return {
        'stats': {
            'total_jobs': jobs.count(),
            'active_jobs': jobs.filter(status=Job.Status.PUBLISHED).count(),
            'total_applicants': applications.count(),
            'shortlisted': applications.filter(status=Status.SHORTLISTED).count(),
            'interviews_scheduled': Interview.objects.filter(
                application__job__company=company, status=Interview.Status.SCHEDULED,
                scheduled_at__gte=now).count(),
            'selected': applications.filter(status=Status.SELECTED).count(),
        },
        'status_chart': _choice_chart(applications, 'status', Status.choices, 'Applications'),
        'per_job_chart': {'labels': [job.title[:28] for job in per_job],
                          'values': [job.total for job in per_job], 'label': 'Applicants'},
        'daily_chart': _daily_chart(applications, 'applied_at', 'New applications'),
        'recent_applications': applications.select_related('job', 'candidate__user')[:6],
    }


def admin_dashboard():
    User = get_user_model()
    applications = JobApplication.objects.all()
    return {
        'stats': {
            'total_users': User.objects.count(),
            'total_candidates': User.objects.filter(role='candidate').count(),
            'total_recruiters': User.objects.filter(role='recruiter').count(),
            'total_companies': Company.objects.count(),
            'pending_companies': Company.objects.filter(
                verification_status=Company.Verification.PENDING).count(),
            'total_jobs': Job.objects.count(),
            'total_applications': applications.count(),
            'total_interviews': Interview.objects.count(),
        },
        'users_chart': _choice_chart(User.objects.all(), 'role', User.Role.choices, 'Users'),
        'jobs_chart': _choice_chart(Job.objects.all(), 'status', Job.Status.choices, 'Jobs'),
        'status_chart': _choice_chart(applications, 'status', Status.choices, 'Applications'),
        'type_chart': _choice_chart(Job.objects.all(), 'employment_type', Job.EmploymentType.choices, 'Jobs'),
        'daily_chart': _daily_chart(applications, 'applied_at', 'New applications'),
        'top_companies': Company.objects.annotate(total=Count('jobs__applications')).order_by('-total')[:5],
    }

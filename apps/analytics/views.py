"""Recruiter dashboard and the platform administrator dashboard (separate from /django-admin/)."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.audit import log_action
from apps.accounts.models import AuditLog
from apps.accounts.permissions import admin_required, recruiter_required
from apps.applications.models import JobApplication
from apps.common.utils import safe_next
from apps.companies.models import Company
from apps.jobs.models import Job
from apps.jobs.services import change_job_status
from apps.notifications.models import Notification
from apps.notifications.services import notify_company_recruiters

from . import services

User = get_user_model()


@recruiter_required
def recruiter_dashboard(request):
    data = services.recruiter_dashboard(request.company)
    return render(request, 'recruiter/dashboard.html', {'company': request.company, **data})


# ------------------------------------------------------------------ admin dashboard
@admin_required
def admin_dashboard(request):
    return render(request, 'admin_dashboard/dashboard.html', {'section': 'dashboard', **services.admin_dashboard()})


@admin_required
def admin_analytics(request):
    return render(request, 'admin_dashboard/analytics.html', {'section': 'analytics', **services.admin_dashboard()})


@admin_required
def admin_users(request):
    qs = User.objects.all().order_by('-created_at')
    role = request.GET.get('role', '')
    query = request.GET.get('q', '').strip()
    if role in User.Role.values:
        qs = qs.filter(role=role)
    if query:
        qs = qs.filter(Q(email__icontains=query) | Q(full_name__icontains=query))
    page_obj = Paginator(qs, 15).get_page(request.GET.get('page'))
    return render(request, 'admin_dashboard/users.html', {
        'section': 'users', 'page_obj': page_obj, 'roles': User.Role.choices, 'role': role, 'q': query})


@admin_required
@require_POST
def admin_user_toggle(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user.pk == request.user.pk:
        messages.error(request, 'You cannot deactivate your own account.')
    else:
        user.is_active = not user.is_active
        user.save(update_fields=['is_active'])
        log_action(request.user, 'user_activated' if user.is_active else 'user_deactivated', user.email)
        messages.success(request, f'{user.email} is now {"active" if user.is_active else "deactivated"}.')
    return redirect(safe_next(request, 'analytics:admin_users'))


@admin_required
def admin_companies(request):
    qs = Company.objects.annotate(job_total=Count('jobs', distinct=True)).order_by('-created_at')
    status = request.GET.get('status', '')
    if status in Company.Verification.values:
        qs = qs.filter(verification_status=status)
    page_obj = Paginator(qs, 12).get_page(request.GET.get('page'))
    return render(request, 'admin_dashboard/companies.html', {
        'section': 'companies', 'page_obj': page_obj, 'status': status,
        'statuses': Company.Verification.choices})



@admin_required
@require_POST
@transaction.atomic
def admin_company_review(request, pk):
    company = get_object_or_404(Company, pk=pk)
    decision = request.POST.get('decision')
    note = request.POST.get('note', '').strip()

    if decision not in Company.Verification.values:
        messages.error(request, 'Invalid decision.')
        return redirect('analytics:admin_companies')

    company.verification_status = decision
    company.verification_note = note
    company.verified_at = (
        timezone.now()
        if decision == Company.Verification.VERIFIED
        else None
        )
    company.save()

    # Automatically publish eligible draft jobs when company is verified.
    published_count = 0

    if decision == Company.Verification.VERIFIED:
        draft_jobs = Job.objects.filter(
            company=company,
            status=Job.Status.DRAFT,
            deadline__gte=timezone.localdate(),
        ).select_related('company')

        for job in draft_jobs:
            change_job_status(
                job,
                Job.Status.PUBLISHED,
                actor=request.user,
            )
            published_count += 1

    log_action(request.user, f'company_{decision}', company.name, note)

    notify_company_recruiters(
        company,
        'Company verification update',
        f'Your company "{company.name}" is now: '
        f'{company.get_verification_status_display()}.'
        + (f' Note: {note}' if note else ''),
        Notification.Type.COMPANY,
    )

    if decision == Company.Verification.VERIFIED:
        messages.success(
            request,
            f'{company.name} verified successfully. '
            f'{published_count} eligible draft job(s) automatically published.'
        )
    else:
        messages.success(request, f'{company.name} marked as {decision}.')

    return redirect('analytics:admin_companies')



@admin_required
def admin_jobs(request):
    qs = Job.objects.select_related('company').annotate(applicant_count=Count('applications')).order_by('-created_at')
    status = request.GET.get('status', '')
    query = request.GET.get('q', '').strip()
    if status in Job.Status.values:
        qs = qs.filter(status=status)
    if query:
        qs = qs.filter(Q(title__icontains=query) | Q(company__name__icontains=query))
    page_obj = Paginator(qs, 12).get_page(request.GET.get('page'))
    return render(request, 'admin_dashboard/jobs.html', {
        'section': 'jobs', 'page_obj': page_obj, 'status': status, 'q': query, 'statuses': Job.Status.choices})


@admin_required
@require_POST
def admin_job_moderate(request, pk):
    job = get_object_or_404(Job, pk=pk)
    action = request.POST.get('action')
    note = request.POST.get('note', '').strip()
    if action == 'hide':
        job.is_hidden_by_admin, job.moderation_note = True, note
    elif action == 'unhide':
        job.is_hidden_by_admin, job.moderation_note = False, ''
    elif action == 'feature':
        job.is_featured = True
    elif action == 'unfeature':
        job.is_featured = False
    else:
        messages.error(request, 'Unknown action.')
        return redirect('analytics:admin_jobs')
    job.save()
    log_action(request.user, f'job_{action}', f'{job.title} (#{job.pk})', note)
    messages.success(request, f'Job updated ({action}).')
    return redirect(safe_next(request, 'analytics:admin_jobs'))


@admin_required
def admin_applications(request):
    qs = JobApplication.objects.select_related('job__company', 'candidate__user').order_by('-applied_at')
    status = request.GET.get('status', '')
    query = request.GET.get('q', '').strip()
    if status in JobApplication.Status.values:
        qs = qs.filter(status=status)
    if query:
        qs = qs.filter(Q(job__title__icontains=query) | Q(candidate__user__email__icontains=query)
                       | Q(candidate__user__full_name__icontains=query))
    page_obj = Paginator(qs, 15).get_page(request.GET.get('page'))
    return render(request, 'admin_dashboard/applications.html', {
        'section': 'applications', 'page_obj': page_obj, 'status': status, 'q': query,
        'statuses': JobApplication.Status.choices})


@admin_required
def admin_audit(request):
    qs = AuditLog.objects.select_related('actor')
    query = request.GET.get('q', '').strip()
    if query:
        qs = qs.filter(Q(action__icontains=query) | Q(target__icontains=query) | Q(details__icontains=query))
    page_obj = Paginator(qs, 20).get_page(request.GET.get('page'))
    return render(request, 'admin_dashboard/audit.html', {'section': 'audit', 'page_obj': page_obj, 'q': query})

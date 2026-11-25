"""Applying, tracking and reviewing applications."""
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.permissions import candidate_required, recruiter_required
from apps.candidates.services import get_profile
from apps.common.exceptions import ServiceError
from apps.jobs.models import Job

from .forms import ApplyForm, StatusUpdateForm
from .models import JobApplication
from .services import TRANSITIONS, Status, apply_to_job, change_status, recruiter_next_statuses


# ------------------------------------------------------------------ candidate
@candidate_required
@require_POST
def apply(request, job_id):
    profile = get_profile(request.user)
    job = get_object_or_404(Job, pk=job_id)
    form = ApplyForm(request.POST, candidate=profile)
    if not form.is_valid():
        messages.error(request, 'Please choose a resume and check your cover letter.')
        return redirect(job.get_absolute_url())
    try:
        application = apply_to_job(candidate=profile, job_id=job.pk, resume_id=form.cleaned_data['resume'].pk,
                                   cover_letter=form.cleaned_data['cover_letter'])
    except ServiceError as error:
        messages.error(request, error.message)
        return redirect(job.get_absolute_url())
    messages.success(request, 'Application submitted. Good luck!')
    return redirect('applications:detail', pk=application.pk)


@candidate_required
def my_applications(request):
    profile = get_profile(request.user)
    qs = JobApplication.objects.filter(candidate=profile).select_related('job__company')
    status = request.GET.get('status', '')
    if status in Status.values:
        qs = qs.filter(status=status)
    page_obj = Paginator(qs, 10).get_page(request.GET.get('page'))
    return render(request, 'candidate/applications.html', {'page_obj': page_obj, 'status': status,
                                                           'statuses': Status.choices})


@candidate_required
def application_detail(request, pk):
    application = get_object_or_404(
        JobApplication.objects.select_related('job__company', 'resume'),
        pk=pk, candidate=get_profile(request.user))  # candidates only see their own applications
    return render(request, 'candidate/application_detail.html', {
        'application': application,
        'history': application.history.select_related('changed_by'),
        'interviews': application.interviews.all(),
        'can_withdraw': Status.WITHDRAWN in TRANSITIONS[application.status],
    })


@candidate_required
@require_POST
def withdraw(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, candidate=get_profile(request.user))
    try:
        change_status(application=application, new_status=Status.WITHDRAWN, actor=request.user,
                      note='Withdrawn by the candidate.')
        messages.success(request, 'Your application was withdrawn.')
    except ServiceError as error:
        messages.error(request, error.message)
    return redirect('applications:detail', pk=pk)


# ------------------------------------------------------------------ recruiter
@recruiter_required
def applicants(request, job_id):
    job = get_object_or_404(Job, pk=job_id, company=request.company)  # only your company's jobs
    qs = JobApplication.objects.filter(job=job).select_related('candidate__user')
    status = request.GET.get('status', '')
    if status in Status.values:
        qs = qs.filter(status=status)
    page_obj = Paginator(qs, 10).get_page(request.GET.get('page'))
    return render(request, 'recruiter/applicants.html', {'job': job, 'page_obj': page_obj, 'status': status,
                                                         'statuses': Status.choices})


@recruiter_required
def application_review(request, pk):
    application = get_object_or_404(
        JobApplication.objects.select_related('job__company', 'candidate__user', 'resume'),
        pk=pk, job__company=request.company)
    candidate = application.candidate
    choices = recruiter_next_statuses(application)
    return render(request, 'recruiter/application_review.html', {
        'application': application,
        'candidate': candidate,
        'educations': candidate.educations.all(),
        'experiences': candidate.experiences.all(),
        'candidate_skills': candidate.candidate_skills.select_related('skill'),
        'history': application.history.select_related('changed_by'),
        'interviews': application.interviews.all(),
        'status_form': StatusUpdateForm(choices=choices),
        'has_next_statuses': bool(choices),
        'can_schedule': application.status in (Status.SHORTLISTED, Status.INTERVIEW_SCHEDULED,
                                               Status.INTERVIEW_COMPLETED),
    })


@recruiter_required
@require_POST
def update_status(request, pk):
    application = get_object_or_404(JobApplication, pk=pk, job__company=request.company)
    form = StatusUpdateForm(request.POST, choices=recruiter_next_statuses(application))
    if not form.is_valid():
        messages.error(request, 'Please choose a valid next status.')
        return redirect('applications:review', pk=pk)
    try:
        change_status(application=application, new_status=form.cleaned_data['new_status'],
                      actor=request.user, note=form.cleaned_data['note'])
        messages.success(request, 'Application status updated.')
    except ServiceError as error:
        messages.error(request, error.message)
    return redirect('applications:review', pk=pk)

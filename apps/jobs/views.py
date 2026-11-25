"""Public job pages (home, search, details) and recruiter job management."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.permissions import recruiter_company_id, recruiter_required
from apps.applications.forms import ApplyForm
from apps.applications.models import JobApplication
from apps.candidates.models import SavedJob
from apps.common.exceptions import ServiceError
from apps.companies.models import Company

from .forms import JobForm
from .models import Job
from .services import change_job_status, search_jobs, set_job_skills


def home(request):
    base = Job.objects.public().select_related('company').prefetch_related('job_skills__skill')
    featured = base.filter(is_featured=True).order_by('-published_at', '-id')[:6]
    latest = base.order_by('-published_at', '-id')[:6]
    User = get_user_model()
    stats = {
        'jobs': Job.objects.public().count(),
        'companies': Company.objects.filter(verification_status=Company.Verification.VERIFIED).count(),
        'candidates': User.objects.filter(role='candidate').count(),
    }
    top_locations = (Job.objects.public().values('location').annotate(total=Count('id')).order_by('-total')[:6])
    return render(request, 'public/home.html', {'featured': featured, 'latest': latest, 'stats': stats,
                                                'top_locations': top_locations})


def job_list(request):
    page_obj = Paginator(search_jobs(request.GET), 9).get_page(request.GET.get('page'))
    return render(request, 'public/job_list.html', {
        'page_obj': page_obj,
        'total': page_obj.paginator.count,
        'params': request.GET,
        'employment_types': Job.EmploymentType.choices,
    })


def job_detail(request, pk):
    job = get_object_or_404(Job.objects.select_related('company').prefetch_related('job_skills__skill'), pk=pk)
    user = request.user
    is_preview = False
    if not job.is_open:
        # Closed/draft/hidden jobs are visible only to the owning company's recruiters and admins.
        if user.is_authenticated and (user.role == 'admin' or recruiter_company_id(user) == job.company_id):
            is_preview = True
        else:
            raise Http404

    context = {'job': job, 'is_preview': is_preview, 'can_apply': False}
    if user.is_authenticated and user.role == 'candidate' and job.is_open:
        from apps.candidates.services import get_profile
        profile = get_profile(user)
        context.update({
            'can_apply': True,
            'resume_count': profile.resumes.count(),
            'already_applied': JobApplication.objects.filter(job=job, candidate=profile).first(),
            'is_saved': SavedJob.objects.filter(job=job, candidate=profile).exists(),
            'apply_form': ApplyForm(candidate=profile),
        })
    return render(request, 'public/job_detail.html', context)


# ------------------------------------------------------------------ recruiter
@recruiter_required
def manage_list(request):
    qs = (Job.objects.filter(company=request.company)
          .annotate(applicant_count=Count('applications')).order_by('-created_at'))
    status = request.GET.get('status', '')
    if status in Job.Status.values:
        qs = qs.filter(status=status)
    page_obj = Paginator(qs, 10).get_page(request.GET.get('page'))
    return render(request, 'recruiter/job_list.html', {'page_obj': page_obj, 'status': status,
                                                       'statuses': Job.Status.choices, 'company': request.company})


@recruiter_required
def job_create(request):
    form = JobForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        job = form.save(commit=False)
        job.company = request.company
        job.created_by = request.user
        job.status = Job.Status.DRAFT
        job.save()
        set_job_skills(job, form.cleaned_data['skills'])
        messages.success(request, 'Job saved as a draft. Publish it when you are ready.')
        return redirect('jobs:manage')
    return render(request, 'generic_form.html', {
        'page_title': 'Post a job', 'heading': 'Post a new job', 'form': form,
        'subtitle': 'Describe the role. You can publish it after saving.',
        'submit_label': 'Save job', 'cancel_url': 'jobs:manage'})


@recruiter_required
def job_edit(request, pk):
    job = get_object_or_404(Job, pk=pk, company=request.company)  # other companies' jobs -> 404
    form = JobForm(request.POST or None, instance=job)
    if request.method == 'POST' and form.is_valid():
        job = form.save()
        set_job_skills(job, form.cleaned_data['skills'])
        messages.success(request, 'Job updated.')
        return redirect('jobs:manage')
    return render(request, 'generic_form.html', {
        'page_title': 'Edit job', 'heading': f'Edit: {job.title}', 'form': form,
        'submit_label': 'Save changes', 'cancel_url': 'jobs:manage'})


@recruiter_required
@require_POST
def job_status(request, pk):
    job = get_object_or_404(Job, pk=pk, company=request.company)
    try:
        change_job_status(job, request.POST.get('status', ''), actor=request.user)
        messages.success(request, f'Job is now {job.get_status_display().lower()}.')
    except ServiceError as error:
        messages.error(request, error.message)
    return redirect('jobs:manage')

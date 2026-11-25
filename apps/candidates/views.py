"""Candidate pages: dashboard, profile, education, experience, skills, resumes, saved jobs."""
import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.accounts.permissions import candidate_required
from apps.analytics.services import candidate_dashboard
from apps.common.utils import safe_next
from apps.jobs.models import Job

from .forms import CandidateProfileForm, EducationForm, ExperienceForm, ResumeUploadForm, SkillForm
from .models import CandidateSkill, Education, Resume, SavedJob, WorkExperience
from .services import can_download_resume, get_or_create_skill, get_profile


@candidate_required
def dashboard(request):
    profile = get_profile(request.user)
    return render(request, 'candidate/dashboard.html', {'profile': profile, **candidate_dashboard(profile)})


@candidate_required
def profile_edit(request):
    profile = get_profile(request.user)
    form = CandidateProfileForm(request.POST or None, instance=profile)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Profile updated.')
        return redirect('candidates:profile')
    return render(request, 'candidate/profile.html', {'form': form, 'profile': profile,
                                                      'completeness': profile.completeness()})


# ---------------------------------------------------------------- education
@candidate_required
def education(request):
    profile = get_profile(request.user)
    form = EducationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.candidate = profile
        item.save()
        messages.success(request, 'Education added.')
        return redirect('candidates:education')
    return render(request, 'candidate/education.html', {'form': form, 'items': profile.educations.all()})


@candidate_required
@require_POST
def education_delete(request, pk):
    get_object_or_404(Education, pk=pk, candidate=get_profile(request.user)).delete()
    messages.success(request, 'Education removed.')
    return redirect('candidates:education')


# ---------------------------------------------------------------- experience
@candidate_required
def experience(request):
    profile = get_profile(request.user)
    form = ExperienceForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        item = form.save(commit=False)
        item.candidate = profile
        item.save()
        messages.success(request, 'Experience added.')
        return redirect('candidates:experience')
    return render(request, 'candidate/experience.html', {'form': form, 'items': profile.experiences.all()})


@candidate_required
@require_POST
def experience_delete(request, pk):
    get_object_or_404(WorkExperience, pk=pk, candidate=get_profile(request.user)).delete()
    messages.success(request, 'Experience removed.')
    return redirect('candidates:experience')


# ---------------------------------------------------------------- skills
@candidate_required
def skills(request):
    profile = get_profile(request.user)
    form = SkillForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        skill = get_or_create_skill(form.cleaned_data['skill_name'])
        CandidateSkill.objects.update_or_create(candidate=profile, skill=skill,
                                                defaults={'proficiency': form.cleaned_data['proficiency']})
        messages.success(request, f'Skill "{skill.name}" saved.')
        return redirect('candidates:skills')
    items = profile.candidate_skills.select_related('skill')
    return render(request, 'candidate/skills.html', {'form': form, 'items': items})


@candidate_required
@require_POST
def skill_remove(request, pk):
    get_object_or_404(CandidateSkill, pk=pk, candidate=get_profile(request.user)).delete()
    messages.success(request, 'Skill removed.')
    return redirect('candidates:skills')


# ---------------------------------------------------------------- resumes
@candidate_required
def resumes(request):
    profile = get_profile(request.user)
    form = ResumeUploadForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        upload = form.cleaned_data['file']
        resume = Resume(
            candidate=profile,
            file=upload,
            original_name=os.path.basename(upload.name)[:255],
            file_type=os.path.splitext(upload.name)[1].lower().lstrip('.'),
            file_size=upload.size,
            is_default=not profile.resumes.exists(),
        )
        resume.save()
        messages.success(request, 'Resume uploaded.')
        return redirect('candidates:resumes')
    return render(request, 'candidate/resumes.html', {'form': form, 'items': profile.resumes.all()})


@candidate_required
@require_POST
def resume_delete(request, pk):
    resume = get_object_or_404(Resume, pk=pk, candidate=get_profile(request.user))
    if resume.applications.exists():
        messages.error(request, 'This resume was used in a job application, so it cannot be deleted.')
        return redirect('candidates:resumes')
    was_default = resume.is_default
    resume.file.delete(save=False)
    resume.delete()
    if was_default:
        newest = get_profile(request.user).resumes.first()
        if newest:
            newest.is_default = True
            newest.save(update_fields=['is_default'])
    messages.success(request, 'Resume deleted.')
    return redirect('candidates:resumes')


@candidate_required
@require_POST
def resume_make_default(request, pk):
    profile = get_profile(request.user)
    resume = get_object_or_404(Resume, pk=pk, candidate=profile)
    with transaction.atomic():
        profile.resumes.update(is_default=False)
        resume.is_default = True
        resume.save(update_fields=['is_default'])
    messages.success(request, 'Default resume updated.')
    return redirect('candidates:resumes')


@login_required
def resume_download(request, pk):
    """The ONLY way to get a resume file: permissions are checked on the server."""
    resume = get_object_or_404(Resume.objects.select_related('candidate__user'), pk=pk)
    if not can_download_resume(request.user, resume):
        raise PermissionDenied
    try:
        handle = resume.file.open('rb')
    except FileNotFoundError:
        raise Http404('The resume file is missing.')
    return FileResponse(handle, as_attachment=True, filename=resume.original_name)


# ---------------------------------------------------------------- saved jobs
@candidate_required
def saved_jobs(request):
    profile = get_profile(request.user)
    qs = SavedJob.objects.filter(candidate=profile).select_related('job__company')
    page_obj = Paginator(qs, 10).get_page(request.GET.get('page'))
    return render(request, 'candidate/saved_jobs.html', {'page_obj': page_obj})


@candidate_required
@require_POST
def toggle_saved(request, job_id):
    profile = get_profile(request.user)
    job = get_object_or_404(Job.objects.public(), pk=job_id)
    saved, created = SavedJob.objects.get_or_create(candidate=profile, job=job)
    if not created:
        saved.delete()
        messages.success(request, 'Job removed from your saved list.')
    else:
        messages.success(request, 'Job saved.')
    return redirect(safe_next(request, job.get_absolute_url()))

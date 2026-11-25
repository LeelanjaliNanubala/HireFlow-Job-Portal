from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.accounts.permissions import candidate_required, recruiter_required
from apps.applications.models import JobApplication
from apps.applications.services import Status
from apps.candidates.services import get_profile
from apps.common.exceptions import ServiceError

from .forms import InterviewScheduleForm, InterviewUpdateForm
from .models import Interview
from .services import INTERVIEWABLE, schedule_interview, update_interview


@recruiter_required
def schedule(request, application_id):
    application = get_object_or_404(JobApplication.objects.select_related('job', 'candidate__user'),
                                    pk=application_id, job__company=request.company)
    if application.status not in INTERVIEWABLE:
        messages.error(request, 'Shortlist the candidate before scheduling an interview.')
        return redirect('applications:review', pk=application.pk)
    form = InterviewScheduleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            schedule_interview(application=application, actor=request.user, **form.cleaned_data)
        except ServiceError as error:
            form.add_error(None, error.message)
        else:
            messages.success(request, 'Interview scheduled and the candidate was notified.')
            return redirect('applications:review', pk=application.pk)
    return render(request, 'generic_form.html', {
        'page_title': 'Schedule interview',
        'heading': f'Schedule interview: {application.candidate.user.full_name}',
        'subtitle': f'Role: {application.job.title}',
        'form': form, 'submit_label': 'Schedule interview',
        'cancel_url': 'applications:review', 'cancel_args': [application.pk]})


@recruiter_required
def edit(request, pk):
    interview = get_object_or_404(Interview.objects.select_related('application__job', 'application__candidate__user'),
                                  pk=pk, application__job__company=request.company)
    form = InterviewUpdateForm(request.POST or None, instance=interview)
    if request.method == 'POST' and form.is_valid():
        data = {name: form.cleaned_data[name] for name in form.fields}
        interview = Interview.objects.get(pk=pk)  # fresh copy: the form changed the in-memory one
        update_interview(interview=interview, actor=request.user, **data)
        messages.success(request, 'Interview updated.')
        return redirect('applications:review', pk=interview.application_id)
    return render(request, 'generic_form.html', {
        'page_title': 'Interview feedback',
        'heading': f'Interview round {interview.round_number}: {interview.application.candidate.user.full_name}',
        'subtitle': 'Update the schedule, status and private feedback. Candidates cannot see the feedback.',
        'form': form, 'submit_label': 'Save interview',
        'cancel_url': 'applications:review', 'cancel_args': [interview.application_id]})


@candidate_required
def my_interviews(request):
    profile = get_profile(request.user)
    now = timezone.now()
    base = Interview.objects.filter(application__candidate=profile).select_related('application__job__company')
    upcoming = base.filter(scheduled_at__gte=now).exclude(status=Interview.Status.CANCELLED)
    past = base.exclude(pk__in=upcoming.values('pk')).order_by('-scheduled_at')
    return render(request, 'candidate/interviews.html', {'upcoming': upcoming, 'past': past})


@recruiter_required
def recruiter_list(request):
    now = timezone.now()
    base = Interview.objects.filter(application__job__company=request.company).select_related(
        'application__job', 'application__candidate__user')
    upcoming = base.filter(scheduled_at__gte=now, status=Interview.Status.SCHEDULED)
    page_obj = Paginator(base.order_by('-scheduled_at'), 10).get_page(request.GET.get('page'))
    return render(request, 'recruiter/interviews.html', {'upcoming': upcoming, 'page_obj': page_obj})

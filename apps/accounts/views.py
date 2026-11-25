"""Login, logout, registration, password reset and role-based redirect."""
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (LoginView, PasswordResetCompleteView, PasswordResetConfirmView,
                                       PasswordResetDoneView, PasswordResetView)
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from .forms import (CandidateRegistrationForm, HireFlowPasswordResetForm, HireFlowSetPasswordForm, LoginForm,
                    RecruiterRegistrationForm)
from .models import User


def role_home(user):
    """URL name of the dashboard that matches the user's role."""
    if user.role == User.Role.ADMIN:
        return 'analytics:admin_dashboard'
    if user.role == User.Role.RECRUITER:
        return 'analytics:recruiter_dashboard'
    return 'candidates:dashboard'


@login_required
def dashboard_redirect(request):
    return redirect(role_home(request.user))


class HireFlowLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


def register_candidate(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = CandidateRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Welcome to HireFlow! Complete your profile to start applying.')
        return redirect('candidates:profile')
    return render(request, 'accounts/register_candidate.html', {'form': form})


def register_recruiter(request):
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')
    form = RecruiterRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, 'Welcome to HireFlow! Complete your company profile. '
                                  'An administrator must verify your company before you can publish jobs.')
        return redirect('companies:edit')
    return render(request, 'accounts/register_recruiter.html', {'form': form})


class HireFlowPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/password_reset_email.txt'
    subject_template_name = 'accounts/password_reset_subject.txt'
    form_class = HireFlowPasswordResetForm
    success_url = reverse_lazy('accounts:password_reset_done')


class HireFlowPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class HireFlowPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    form_class = HireFlowSetPasswordForm
    success_url = reverse_lazy('accounts:password_reset_complete')


class HireFlowPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'

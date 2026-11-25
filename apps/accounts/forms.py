"""Login, registration and password reset forms."""
from django import forms
from django.contrib.auth import password_validation
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm
from django.core.exceptions import ValidationError

from apps.common.forms import BootstrapFormMixin

from .models import User
from .services import register_user


class LoginForm(BootstrapFormMixin, AuthenticationForm):
    username = forms.EmailField(
        label='Email address',
        widget=forms.EmailInput(attrs={'autofocus': True, 'autocomplete': 'email'}),
    )

    def clean_username(self):
        return self.cleaned_data['username'].lower()


class HireFlowPasswordResetForm(BootstrapFormMixin, PasswordResetForm):
    pass


class HireFlowSetPasswordForm(BootstrapFormMixin, SetPasswordForm):
    pass


class BaseRegistrationForm(BootstrapFormMixin, forms.ModelForm):
    role = None  # set by subclasses

    password1 = forms.CharField(label='Password', widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
                                help_text=password_validation.password_validators_help_text_html())
    password2 = forms.CharField(label='Confirm password',
                                widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    class Meta:
        model = User
        fields = ['full_name', 'email']

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('An account with this email already exists.')
        return email

    def clean(self):
        cleaned = super().clean()
        password1, password2 = cleaned.get('password1'), cleaned.get('password2')
        if password1 and password2:
            if password1 != password2:
                self.add_error('password2', 'The two passwords do not match.')
            else:
                try:
                    password_validation.validate_password(password1, User(email=cleaned.get('email', ''),
                                                                          full_name=cleaned.get('full_name', '')))
                except ValidationError as error:
                    self.add_error('password1', error)
        return cleaned


class CandidateRegistrationForm(BaseRegistrationForm):
    role = User.Role.CANDIDATE
    phone = forms.CharField(max_length=20, required=False)

    def save(self, commit=True):
        data = self.cleaned_data
        return register_user(role=self.role, full_name=data['full_name'], email=data['email'],
                             password=data['password1'], phone=data.get('phone', ''))


class RecruiterRegistrationForm(BaseRegistrationForm):
    role = User.Role.RECRUITER
    company_name = forms.CharField(max_length=200)
    designation = forms.CharField(max_length=100, required=False, help_text='For example: HR Manager')

    def save(self, commit=True):
        data = self.cleaned_data
        return register_user(role=self.role, full_name=data['full_name'], email=data['email'],
                             password=data['password1'], company_name=data['company_name'],
                             designation=data.get('designation', ''))

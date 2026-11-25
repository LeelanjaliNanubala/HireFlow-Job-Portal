import datetime

from django import forms

from apps.common.forms import BootstrapFormMixin

from .models import CandidateProfile, CandidateSkill, Education, WorkExperience
from .validators import validate_resume_file


class CandidateProfileForm(BootstrapFormMixin, forms.ModelForm):
    full_name = forms.CharField(max_length=150)

    class Meta:
        model = CandidateProfile
        fields = ['phone', 'location', 'headline', 'summary', 'portfolio_url', 'years_experience']
        widgets = {'summary': forms.Textarea(attrs={'rows': 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['full_name'].initial = self.instance.user.full_name
        self.order_fields(['full_name'] + list(self._meta.fields))

    def save(self, commit=True):
        profile = super().save(commit=False)
        profile.user.full_name = self.cleaned_data['full_name']
        if commit:
            profile.user.save(update_fields=['full_name'])
            profile.save()
        return profile


class EducationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Education
        fields = ['degree', 'institution', 'field_of_study', 'start_year', 'end_year', 'grade']

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('start_year'), cleaned.get('end_year')
        this_year = datetime.date.today().year
        if start and not 1950 <= start <= this_year + 1:
            self.add_error('start_year', 'Enter a valid year.')
        if start and end and end < start:
            self.add_error('end_year', 'End year cannot be before the start year.')
        return cleaned


class ExperienceForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = WorkExperience
        fields = ['job_title', 'company_name', 'location', 'start_date', 'end_date', 'is_current', 'description']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'end_date': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('start_date'), cleaned.get('end_date')
        if cleaned.get('is_current'):
            cleaned['end_date'] = None
        elif start and end and end < start:
            self.add_error('end_date', 'End date cannot be before the start date.')
        return cleaned


class SkillForm(BootstrapFormMixin, forms.Form):
    skill_name = forms.CharField(max_length=60, label='Skill')
    proficiency = forms.ChoiceField(choices=CandidateSkill.Proficiency.choices,
                                    initial=CandidateSkill.Proficiency.INTERMEDIATE)


class ResumeUploadForm(BootstrapFormMixin, forms.Form):
    file = forms.FileField(label='Resume file', help_text='PDF, DOC or DOCX, up to 5 MB.')

    def clean_file(self):
        upload = self.cleaned_data['file']
        validate_resume_file(upload)
        return upload

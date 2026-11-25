import datetime

from django import forms

from apps.common.forms import BootstrapFormMixin

from .models import Job
from .services import parse_skill_names


class JobForm(BootstrapFormMixin, forms.ModelForm):
    skills = forms.CharField(required=False, label='Required skills',
                             help_text='Separate skills with commas, for example: Python, Django, MySQL')

    class Meta:
        model = Job
        fields = ['title', 'description', 'responsibilities', 'location', 'employment_type',
                  'experience_min', 'experience_max', 'salary_min', 'salary_max', 'salary_currency', 'deadline']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 6}),
            'responsibilities': forms.Textarea(attrs={'rows': 4}),
            'deadline': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['skills'].initial = ', '.join(skill.name for skill in self.instance.skills.all())

    def clean_deadline(self):
        deadline = self.cleaned_data['deadline']
        if ('deadline' in self.changed_data or not self.instance.pk) and deadline < datetime.date.today():
            raise forms.ValidationError('The deadline cannot be in the past.')
        return deadline

    def clean_skills(self):
        names = parse_skill_names(self.cleaned_data.get('skills', ''))
        if len(names) > 25:
            raise forms.ValidationError('Please list at most 25 skills.')
        return names

    def clean(self):
        cleaned = super().clean()
        exp_min, exp_max = cleaned.get('experience_min'), cleaned.get('experience_max')
        if exp_min is not None and exp_max is not None and exp_min > exp_max:
            self.add_error('experience_max', 'Maximum experience must be greater than or equal to the minimum.')
        sal_min, sal_max = cleaned.get('salary_min'), cleaned.get('salary_max')
        if sal_min and sal_max and sal_min > sal_max:
            self.add_error('salary_max', 'Maximum salary must be greater than or equal to the minimum.')
        return cleaned

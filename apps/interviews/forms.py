from django import forms
from django.utils import timezone

from apps.common.forms import BootstrapFormMixin

from .models import Interview

DATETIME_FORMAT = '%Y-%m-%dT%H:%M'


class InterviewScheduleForm(BootstrapFormMixin, forms.ModelForm):
    scheduled_at = forms.DateTimeField(
        label='Date and time', input_formats=[DATETIME_FORMAT],
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}, format=DATETIME_FORMAT))

    class Meta:
        model = Interview
        fields = ['scheduled_at', 'duration_minutes', 'mode', 'meeting_details', 'interviewer_name']

    def clean_scheduled_at(self):
        value = self.cleaned_data['scheduled_at']
        if value <= timezone.now():
            raise forms.ValidationError('Choose a date and time in the future.')
        return value

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('mode') == Interview.Mode.ONLINE and not cleaned.get('meeting_details'):
            self.add_error('meeting_details', 'Add a meeting link for an online interview.')
        return cleaned


class InterviewUpdateForm(InterviewScheduleForm):
    """Edit schedule, status and feedback. Only recruiters of the company can open this form."""

    class Meta:
        model = Interview
        fields = ['scheduled_at', 'duration_minutes', 'mode', 'meeting_details', 'interviewer_name',
                  'status', 'rating', 'feedback']
        widgets = {'feedback': forms.Textarea(attrs={'rows': 4})}

    def clean_scheduled_at(self):
        return self.cleaned_data['scheduled_at']  # past dates are fine when recording an old interview

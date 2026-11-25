from django import forms

from apps.candidates.models import Resume
from apps.common.forms import BootstrapFormMixin


class ApplyForm(BootstrapFormMixin, forms.Form):
    resume = forms.ModelChoiceField(queryset=Resume.objects.none(), empty_label='Select a resume')
    cover_letter = forms.CharField(required=False, max_length=3000, label='Cover letter (optional)',
                                   widget=forms.Textarea(attrs={'rows': 4}))

    def __init__(self, *args, candidate=None, **kwargs):
        super().__init__(*args, **kwargs)
        if candidate is not None:
            self.fields['resume'].queryset = candidate.resumes.all()
            default = candidate.resumes.filter(is_default=True).first()
            if default:
                self.fields['resume'].initial = default.pk


class StatusUpdateForm(BootstrapFormMixin, forms.Form):
    new_status = forms.ChoiceField(choices=[], label='Move to')
    note = forms.CharField(required=False, max_length=1000, label='Note (optional)',
                           widget=forms.Textarea(attrs={'rows': 2}))

    def __init__(self, *args, choices=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['new_status'].choices = list(choices)

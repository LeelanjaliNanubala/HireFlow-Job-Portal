from django import forms

from apps.common.forms import BootstrapFormMixin

from .models import Company


class CompanyForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Company
        fields = ['name', 'website', 'industry', 'size', 'location', 'description']
        widgets = {'description': forms.Textarea(attrs={'rows': 5})}

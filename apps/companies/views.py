from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.permissions import recruiter_required
from apps.jobs.models import Job

from .forms import CompanyForm
from .models import Company


def company_detail(request, pk):
    """Public company profile with its open jobs."""
    company = get_object_or_404(Company, pk=pk)
    jobs = Job.objects.public().filter(company=company).prefetch_related('job_skills__skill')
    return render(request, 'public/company_detail.html', {'company': company, 'jobs': jobs})


@recruiter_required
def company_edit(request):
    """Recruiter edits their own company profile."""
    company = request.company
    form = CompanyForm(request.POST or None, instance=company)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Company profile updated.')
        return redirect('companies:edit')
    return render(request, 'recruiter/company_form.html', {'form': form, 'company': company})

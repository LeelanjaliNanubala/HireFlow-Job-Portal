from django.test import TestCase
from django.urls import reverse

from apps.common.factories import PASSWORD, make_job, make_recruiter

from .models import Company


class CompanyTests(TestCase):
    def test_public_company_page_lists_only_open_jobs(self):
        user, company = make_recruiter()
        make_job(company, user, title='Open job')
        make_job(company, user, title='Draft job', status='draft')
        response = self.client.get(reverse('companies:detail', args=[company.pk]))
        self.assertContains(response, 'Open job')
        self.assertNotContains(response, 'Draft job')

    def test_recruiter_can_edit_own_company(self):
        user, company = make_recruiter()
        self.client.login(username='recruiter@example.com', password=PASSWORD)
        response = self.client.post(reverse('companies:edit'), {'name': 'Renamed Corp', 'industry': 'IT'})
        self.assertRedirects(response, reverse('companies:edit'))
        company.refresh_from_db()
        self.assertEqual(company.name, 'Renamed Corp')

    def test_new_company_is_pending(self):
        self.assertEqual(Company.objects.create(name='X').verification_status, Company.Verification.PENDING)

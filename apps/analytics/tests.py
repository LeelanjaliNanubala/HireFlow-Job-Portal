from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import AuditLog
from apps.applications.services import apply_to_job
from apps.common.factories import (PASSWORD, TEST_MEDIA_ROOT, make_admin, make_candidate, make_job, make_recruiter,
                                   make_resume)
from apps.companies.models import Company


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class DashboardTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.rec_user, self.company = make_recruiter()
        self.job = make_job(self.company, self.rec_user)
        self.cand_user, self.profile = make_candidate()
        apply_to_job(candidate=self.profile, job_id=self.job.pk, resume_id=make_resume(self.profile).pk)

    def test_candidate_dashboard_uses_real_numbers(self):
        self.client.login(username='candidate@example.com', password=PASSWORD)
        response = self.client.get(reverse('candidates:dashboard'))
        self.assertEqual(response.context['stats']['total'], 1)
        self.assertEqual(sum(response.context['status_chart']['values']), 1)

    def test_recruiter_dashboard_numbers(self):
        self.client.login(username='recruiter@example.com', password=PASSWORD)
        stats = self.client.get(reverse('analytics:recruiter_dashboard')).context['stats']
        self.assertEqual((stats['total_jobs'], stats['active_jobs'], stats['total_applicants']), (1, 1, 1))

    def test_recruiter_does_not_see_other_company_data(self):
        make_recruiter(email='other@example.com', company_name='Other Co')
        self.client.login(username='other@example.com', password=PASSWORD)
        stats = self.client.get(reverse('analytics:recruiter_dashboard')).context['stats']
        self.assertEqual((stats['total_jobs'], stats['total_applicants']), (0, 0))

    def test_admin_dashboard_numbers(self):
        self.client.login(username='admin@example.com', password=PASSWORD)
        stats = self.client.get(reverse('analytics:admin_dashboard')).context['stats']
        self.assertEqual(stats['total_candidates'], 1)
        self.assertEqual(stats['total_recruiters'], 1)
        self.assertEqual(stats['total_applications'], 1)
        for name in ('admin_users', 'admin_companies', 'admin_jobs', 'admin_applications', 'admin_analytics',
                     'admin_audit'):
            self.assertEqual(self.client.get(reverse(f'analytics:{name}')).status_code, 200, name)


class AdminActionTests(TestCase):
    def setUp(self):
        make_admin()
        self.rec_user, self.company = make_recruiter(verified=False)
        self.client.login(username='admin@example.com', password=PASSWORD)

    def test_verify_company_is_audited_and_notifies(self):
        self.client.post(reverse('analytics:admin_company_review', args=[self.company.pk]),
                         {'decision': 'verified', 'note': 'Documents checked'})
        self.company.refresh_from_db()
        self.assertEqual(self.company.verification_status, Company.Verification.VERIFIED)
        self.assertIsNotNone(self.company.verified_at)
        self.assertTrue(AuditLog.objects.filter(action='company_verified').exists())
        self.assertTrue(self.rec_user.notifications.exists())

    def test_hide_job_removes_it_from_public_search(self):
        self.company.verification_status = 'verified'
        self.company.save()
        job = make_job(self.company, self.rec_user)
        self.client.post(reverse('analytics:admin_job_moderate', args=[job.pk]),
                         {'action': 'hide', 'note': 'Spam'})
        self.assertNotContains(self.client.get(reverse('jobs:list')), job.title)
        self.assertTrue(AuditLog.objects.filter(action='job_hide').exists())

    def test_admin_cannot_deactivate_self(self):
        admin = make_admin(email='second@example.com')
        self.client.post(reverse('analytics:admin_user_toggle', args=[admin.pk]))
        admin.refresh_from_db()
        self.assertFalse(admin.is_active)  # another admin CAN be deactivated
        me = make_admin(email='third@example.com')
        self.client.logout()
        self.client.login(username='third@example.com', password=PASSWORD)
        self.client.post(reverse('analytics:admin_user_toggle', args=[me.pk]))
        me.refresh_from_db()
        self.assertTrue(me.is_active)

    def test_non_admin_cannot_use_admin_actions(self):
        self.client.logout()
        self.client.login(username='recruiter@example.com', password=PASSWORD)
        response = self.client.post(reverse('analytics:admin_company_review', args=[self.company.pk]),
                                    {'decision': 'verified'})
        self.assertEqual(response.status_code, 403)

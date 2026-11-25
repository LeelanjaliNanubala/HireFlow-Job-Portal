import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.common.exceptions import ServiceError
from apps.common.factories import (PASSWORD, TEST_MEDIA_ROOT, make_candidate, make_job, make_recruiter,
                                   make_resume)
from apps.notifications.models import Notification

from .models import ApplicationHistory, JobApplication
from .services import apply_to_job, change_status


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ApplyTests(TestCase):
    def setUp(self):
        self.rec_user, self.company = make_recruiter()
        self.job = make_job(self.company, self.rec_user)
        self.cand_user, self.profile = make_candidate()
        self.resume = make_resume(self.profile)

    def test_apply_creates_application_history_and_notifications(self):
        app = apply_to_job(candidate=self.profile, job_id=self.job.pk, resume_id=self.resume.pk,
                           cover_letter='Hello')
        self.assertEqual(app.status, JobApplication.Status.SUBMITTED)
        history = ApplicationHistory.objects.get(application=app)
        self.assertEqual((history.old_status, history.new_status), ('', 'submitted'))
        self.assertTrue(Notification.objects.filter(user=self.cand_user).exists())
        self.assertTrue(Notification.objects.filter(user=self.rec_user).exists())

    def test_duplicate_application_blocked_by_service_and_database(self):
        apply_to_job(candidate=self.profile, job_id=self.job.pk, resume_id=self.resume.pk)
        with self.assertRaises(ServiceError) as ctx:
            apply_to_job(candidate=self.profile, job_id=self.job.pk, resume_id=self.resume.pk)
        self.assertEqual(ctx.exception.status, 409)
        with self.assertRaises(IntegrityError), transaction.atomic():
            JobApplication.objects.create(job=self.job, candidate=self.profile, resume=self.resume)

    def test_cannot_apply_to_closed_draft_or_expired_jobs(self):
        for kwargs in ({'status': 'closed'}, {'status': 'draft'},
                       {'deadline': datetime.date.today() - datetime.timedelta(days=1)}):
            job = make_job(self.company, self.rec_user, title='X', **kwargs)
            with self.assertRaises(ServiceError):
                apply_to_job(candidate=self.profile, job_id=job.pk, resume_id=self.resume.pk)

    def test_cannot_use_another_candidates_resume(self):
        _, other_profile = make_candidate(email='other@example.com')
        other_resume = make_resume(other_profile)
        with self.assertRaises(ServiceError):
            apply_to_job(candidate=self.profile, job_id=self.job.pk, resume_id=other_resume.pk)

    def test_web_apply_flow(self):
        self.client.login(username='candidate@example.com', password=PASSWORD)
        response = self.client.post(reverse('applications:apply', args=[self.job.pk]),
                                    {'resume': self.resume.pk, 'cover_letter': 'Hi'})
        app = JobApplication.objects.get()
        self.assertRedirects(response, reverse('applications:detail', args=[app.pk]))
        self.client.post(reverse('applications:apply', args=[self.job.pk]), {'resume': self.resume.pk})
        self.assertEqual(JobApplication.objects.count(), 1)

    def test_recruiter_cannot_apply(self):
        self.client.login(username='recruiter@example.com', password=PASSWORD)
        response = self.client.post(reverse('applications:apply', args=[self.job.pk]), {'resume': self.resume.pk})
        self.assertEqual(response.status_code, 403)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class StatusTests(TestCase):
    def setUp(self):
        self.rec_user, self.company = make_recruiter()
        self.job = make_job(self.company, self.rec_user)
        self.cand_user, self.profile = make_candidate()
        self.app = apply_to_job(candidate=self.profile, job_id=self.job.pk, resume_id=make_resume(self.profile).pk)

    def test_valid_transition_records_history_and_notifies(self):
        change_status(application=self.app, new_status='under_review', actor=self.rec_user, note='Looks good')
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'under_review')
        entry = self.app.history.first()
        self.assertEqual((entry.old_status, entry.new_status, entry.note), ('submitted', 'under_review', 'Looks good'))
        self.assertEqual(entry.changed_by, self.rec_user)
        self.assertTrue(Notification.objects.filter(user=self.cand_user, notification_type='status').exists())

    def test_invalid_transition_rejected(self):
        with self.assertRaises(ServiceError):
            change_status(application=self.app, new_status='selected', actor=self.rec_user)

    def test_terminal_status_cannot_change(self):
        change_status(application=self.app, new_status='rejected', actor=self.rec_user)
        with self.assertRaises(ServiceError):
            change_status(application=self.app, new_status='under_review', actor=self.rec_user)

    def test_recruiter_updates_status_through_web(self):
        self.client.login(username='recruiter@example.com', password=PASSWORD)
        self.client.post(reverse('applications:update_status', args=[self.app.pk]),
                         {'new_status': 'shortlisted', 'note': ''})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'shortlisted')

    def test_recruiter_cannot_set_withdrawn_or_interview_status_by_hand(self):
        self.client.login(username='recruiter@example.com', password=PASSWORD)
        for status in ('withdrawn', 'interview_scheduled'):
            self.client.post(reverse('applications:update_status', args=[self.app.pk]), {'new_status': status})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'submitted')

    def test_candidate_can_withdraw_own_application(self):
        self.client.login(username='candidate@example.com', password=PASSWORD)
        self.client.post(reverse('applications:withdraw', args=[self.app.pk]))
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'withdrawn')


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ApplicationPermissionTests(TestCase):
    def setUp(self):
        self.rec_user, self.company = make_recruiter()
        self.job = make_job(self.company, self.rec_user)
        self.cand_user, self.profile = make_candidate()
        self.app = apply_to_job(candidate=self.profile, job_id=self.job.pk, resume_id=make_resume(self.profile).pk)

    def test_other_company_recruiter_cannot_see_or_change_application(self):
        make_recruiter(email='evil@example.com', company_name='Evil Co')
        self.client.login(username='evil@example.com', password=PASSWORD)
        self.assertEqual(self.client.get(reverse('applications:review', args=[self.app.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('applications:applicants', args=[self.job.pk])).status_code, 404)
        self.client.post(reverse('applications:update_status', args=[self.app.pk]), {'new_status': 'rejected'})
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'submitted')

    def test_candidate_cannot_open_another_candidates_application(self):
        make_candidate(email='nosy@example.com')
        self.client.login(username='nosy@example.com', password=PASSWORD)
        self.assertEqual(self.client.get(reverse('applications:detail', args=[self.app.pk])).status_code, 404)

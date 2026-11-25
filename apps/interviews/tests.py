import datetime

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.applications.services import apply_to_job, change_status
from apps.common.exceptions import ServiceError
from apps.common.factories import (PASSWORD, TEST_MEDIA_ROOT, make_candidate, make_job, make_recruiter,
                                   make_resume)
from apps.notifications.models import Notification

from .models import Interview
from .services import schedule_interview, update_interview


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class InterviewTests(TestCase):
    def setUp(self):
        self.rec_user, self.company = make_recruiter()
        self.job = make_job(self.company, self.rec_user)
        self.cand_user, self.profile = make_candidate()
        self.app = apply_to_job(candidate=self.profile, job_id=self.job.pk, resume_id=make_resume(self.profile).pk)
        self.when = timezone.now() + datetime.timedelta(days=3)

    def _shortlist(self):
        change_status(application=self.app, new_status='shortlisted', actor=self.rec_user)
        self.app.refresh_from_db()

    def test_cannot_schedule_before_shortlisting(self):
        with self.assertRaises(ServiceError):
            schedule_interview(application=self.app, actor=self.rec_user, scheduled_at=self.when,
                               mode='online', meeting_details='https://meet.example.com/x')

    def test_schedule_sets_status_and_notifies_candidate(self):
        self._shortlist()
        interview = schedule_interview(application=self.app, actor=self.rec_user, scheduled_at=self.when,
                                       mode='online', meeting_details='https://meet.example.com/x')
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'interview_scheduled')
        self.assertEqual(interview.round_number, 1)
        self.assertTrue(Notification.objects.filter(user=self.cand_user, notification_type='interview').exists())

    def test_past_time_and_missing_link_rejected(self):
        self._shortlist()
        with self.assertRaises(ServiceError):
            schedule_interview(application=self.app, actor=self.rec_user,
                               scheduled_at=timezone.now() - datetime.timedelta(hours=1), mode='phone')
        with self.assertRaises(ServiceError):
            schedule_interview(application=self.app, actor=self.rec_user, scheduled_at=self.when, mode='online')

    def test_completing_interview_moves_application_forward(self):
        self._shortlist()
        interview = schedule_interview(application=self.app, actor=self.rec_user, scheduled_at=self.when,
                                       mode='phone')
        update_interview(interview=interview, actor=self.rec_user, status=Interview.Status.COMPLETED,
                         feedback='Strong', rating=5)
        self.app.refresh_from_db()
        self.assertEqual(self.app.status, 'interview_completed')

    def test_update_notifies_candidate(self):
        self._shortlist()
        interview = schedule_interview(application=self.app, actor=self.rec_user, scheduled_at=self.when,
                                       mode='phone')
        Notification.objects.all().delete()
        update_interview(interview=interview, actor=self.rec_user, scheduled_at=self.when + datetime.timedelta(days=1))
        self.assertTrue(Notification.objects.filter(user=self.cand_user, title='Interview updated').exists())

    def test_feedback_hidden_from_candidate_and_forbidden_to_other_company(self):
        self._shortlist()
        interview = schedule_interview(application=self.app, actor=self.rec_user, scheduled_at=self.when,
                                       mode='phone')
        update_interview(interview=interview, actor=self.rec_user, feedback='SECRET-FEEDBACK')
        self.client.login(username='candidate@example.com', password=PASSWORD)
        page = self.client.get(reverse('applications:detail', args=[self.app.pk]))
        self.assertNotContains(page, 'SECRET-FEEDBACK')
        self.assertNotContains(self.client.get(reverse('interviews:mine')), 'SECRET-FEEDBACK')
        self.assertEqual(self.client.get(reverse('interviews:edit', args=[interview.pk])).status_code, 403)
        self.client.logout()
        make_recruiter(email='other@example.com', company_name='Other Co')
        self.client.login(username='other@example.com', password=PASSWORD)
        self.assertEqual(self.client.get(reverse('interviews:edit', args=[interview.pk])).status_code, 404)

    def test_recruiter_schedule_page_works(self):
        self._shortlist()
        self.client.login(username='recruiter@example.com', password=PASSWORD)
        response = self.client.post(reverse('interviews:schedule', args=[self.app.pk]), {
            'scheduled_at': (timezone.localtime(self.when)).strftime('%Y-%m-%dT%H:%M'),
            'duration_minutes': 45, 'mode': 'online', 'meeting_details': 'https://meet.example.com/abc',
            'interviewer_name': 'Priya'})
        self.assertRedirects(response, reverse('applications:review', args=[self.app.pk]))
        self.assertEqual(Interview.objects.count(), 1)

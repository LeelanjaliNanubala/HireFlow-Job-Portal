"""REST API tests (run with: python manage.py test)."""
import datetime

from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.applications.services import apply_to_job, change_status
from apps.common.factories import (PASSWORD, TEST_MEDIA_ROOT, make_candidate, make_job, make_recruiter,
                                   make_resume)


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ApiTests(APITestCase):
    def setUp(self):
        self.rec_user, self.company = make_recruiter()
        self.job = make_job(self.company, self.rec_user)
        self.cand_user, self.profile = make_candidate()
        self.resume = make_resume(self.profile)

    def login(self, email):
        response = self.client.post('/api/auth/login/', {'email': email, 'password': PASSWORD}, format='json')
        self.assertEqual(response.status_code, 200)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + response.data['token'])

    # ------------------------------------------------------------ auth
    def test_register_login_logout(self):
        response = self.client.post('/api/auth/register/', {
            'role': 'candidate', 'full_name': 'New', 'email': 'new@example.com', 'password': PASSWORD},
            format='json')
        self.assertEqual(response.status_code, 201)
        self.assertIn('token', response.data)
        self.login('new@example.com')
        self.assertEqual(self.client.post('/api/auth/logout/').status_code, 200)
        self.assertEqual(self.client.get('/api/me/notifications/').status_code, 401)

    def test_bad_login_and_validation_error_shape(self):
        response = self.client.post('/api/auth/login/', {'email': 'x@example.com', 'password': 'bad'}, format='json')
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.data['error']['status'], 401)
        response = self.client.post('/api/auth/register/', {'role': 'recruiter', 'full_name': 'R',
                                                            'email': 'r@example.com', 'password': PASSWORD},
                                    format='json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['error']['code'], 'invalid')
        self.assertIn('company_name', response.data['error']['details'])

    # ------------------------------------------------------------ jobs
    def test_public_job_list_search_and_detail(self):
        make_job(self.company, self.rec_user, title='Hidden draft', status='draft')
        response = self.client.get('/api/jobs/', {'q': 'python'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['count'], 1)
        self.assertEqual(self.client.get(f'/api/jobs/{self.job.pk}/').status_code, 200)
        draft = make_job(self.company, self.rec_user, title='Secret', status='draft')
        self.assertEqual(self.client.get(f'/api/jobs/{draft.pk}/').status_code, 404)

    def test_recruiter_creates_and_patches_job(self):
        self.login('recruiter@example.com')
        payload = {'title': 'API Job', 'description': 'd', 'location': 'Pune', 'experience_min': 0,
                   'experience_max': 2, 'skills': ['Python', 'SQL'],
                   'deadline': (datetime.date.today() + datetime.timedelta(days=10)).isoformat()}
        response = self.client.post('/api/jobs/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'draft')
        self.assertEqual(sorted(response.data['skills']), ['Python', 'SQL'])
        patched = self.client.patch(f"/api/jobs/{response.data['id']}/", {'status': 'published'}, format='json')
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.data['status'], 'published')

    def test_candidate_cannot_create_job_and_other_company_cannot_patch(self):
        self.login('candidate@example.com')
        self.assertEqual(self.client.post('/api/jobs/', {}, format='json').status_code, 403)
        make_recruiter(email='other@example.com', company_name='Other')
        self.login('other@example.com')
        self.assertEqual(self.client.patch(f'/api/jobs/{self.job.pk}/', {'title': 'Hack'}, format='json').status_code, 403)

    # ------------------------------------------------------------ applications
    def test_apply_duplicate_and_list(self):
        self.login('candidate@example.com')
        body = {'job_id': self.job.pk, 'resume_id': self.resume.pk, 'cover_letter': 'Hi'}
        self.assertEqual(self.client.post('/api/applications/', body, format='json').status_code, 201)
        duplicate = self.client.post('/api/applications/', body, format='json')
        self.assertEqual(duplicate.status_code, 409)
        self.assertEqual(duplicate.data['error']['code'], 'duplicate_application')
        mine = self.client.get('/api/me/applications/')
        self.assertEqual(mine.data['count'], 1)

    def test_candidate_id_in_body_is_ignored(self):
        _, other = make_candidate(email='victim@example.com')
        self.login('candidate@example.com')
        self.client.post('/api/applications/', {'job_id': self.job.pk, 'resume_id': self.resume.pk,
                                                'candidate': other.pk}, format='json')
        from apps.applications.models import JobApplication
        self.assertEqual(JobApplication.objects.get().candidate, self.profile)

    def test_recruiter_lists_applicants_and_changes_status(self):
        app = apply_to_job(candidate=self.profile, job_id=self.job.pk, resume_id=self.resume.pk)
        self.login('recruiter@example.com')
        listing = self.client.get(f'/api/recruiter/jobs/{self.job.pk}/applications/')
        self.assertEqual(listing.data['count'], 1)
        ok = self.client.patch(f'/api/applications/{app.pk}/status/', {'status': 'shortlisted'}, format='json')
        self.assertEqual(ok.status_code, 200)
        bad = self.client.patch(f'/api/applications/{app.pk}/status/', {'status': 'withdrawn'}, format='json')
        self.assertEqual(bad.status_code, 400)
        bad = self.client.patch(f'/api/applications/{app.pk}/status/', {'status': 'selected'}, format='json')
        self.assertEqual(bad.status_code, 400)

    def test_other_company_recruiter_gets_403(self):
        app = apply_to_job(candidate=self.profile, job_id=self.job.pk, resume_id=self.resume.pk)
        make_recruiter(email='other@example.com', company_name='Other')
        self.login('other@example.com')
        self.assertEqual(self.client.get(f'/api/recruiter/jobs/{self.job.pk}/applications/').status_code, 403)
        self.assertEqual(self.client.patch(f'/api/applications/{app.pk}/status/', {'status': 'rejected'},
                                           format='json').status_code, 403)

    # ------------------------------------------------------------ interviews and notifications
    def test_schedule_interview_and_candidate_notification(self):
        app = apply_to_job(candidate=self.profile, job_id=self.job.pk, resume_id=self.resume.pk)
        change_status(application=app, new_status='shortlisted', actor=self.rec_user)
        self.login('recruiter@example.com')
        when = (timezone.now() + datetime.timedelta(days=2)).isoformat()
        response = self.client.post(f'/api/applications/{app.pk}/interviews/', {
            'scheduled_at': when, 'mode': 'online', 'meeting_details': 'https://meet.example.com/z'},
            format='json')
        self.assertEqual(response.status_code, 201)
        self.assertNotIn('feedback', response.data)
        self.login('candidate@example.com')
        notes = self.client.get('/api/me/notifications/')
        self.assertEqual(notes.status_code, 200)
        self.assertTrue(any(n['title'] == 'Interview scheduled' for n in notes.data['results']))

    def test_interview_before_shortlist_is_400(self):
        app = apply_to_job(candidate=self.profile, job_id=self.job.pk, resume_id=self.resume.pk)
        self.login('recruiter@example.com')
        when = (timezone.now() + datetime.timedelta(days=2)).isoformat()
        response = self.client.post(f'/api/applications/{app.pk}/interviews/',
                                    {'scheduled_at': when, 'mode': 'phone'}, format='json')
        self.assertEqual(response.status_code, 400)

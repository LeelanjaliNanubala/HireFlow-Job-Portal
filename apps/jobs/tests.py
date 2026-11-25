import datetime

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from apps.common.factories import PASSWORD, make_job, make_recruiter

from .models import Job
from .services import change_job_status, search_jobs
from apps.common.exceptions import ServiceError


class JobVisibilityTests(TestCase):
    def setUp(self):
        self.user, self.company = make_recruiter()

    def test_only_published_active_unexpired_verified_jobs_are_public(self):
        make_job(self.company, self.user, title='Visible')
        make_job(self.company, self.user, title='Draft', status='draft')
        make_job(self.company, self.user, title='Paused', status='paused')
        make_job(self.company, self.user, title='Closed', status='closed')
        make_job(self.company, self.user, title='Expired', deadline=datetime.date.today() - datetime.timedelta(days=1))
        make_job(self.company, self.user, title='Hidden', is_hidden_by_admin=True)
        _, pending = make_recruiter(email='p@example.com', company_name='Pending Co', verified=False)
        make_job(pending, None, title='Unverified company')
        titles = list(Job.objects.public().values_list('title', flat=True))
        self.assertEqual(titles, ['Visible'])

    def test_database_check_constraint_on_experience(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            make_job(self.company, self.user, experience_min=5, experience_max=1)

    def test_non_public_job_detail_is_404_for_visitors_but_preview_for_owner(self):
        job = make_job(self.company, self.user, status='draft')
        self.assertEqual(self.client.get(job.get_absolute_url()).status_code, 404)
        self.client.login(username='recruiter@example.com', password=PASSWORD)
        self.assertEqual(self.client.get(job.get_absolute_url()).status_code, 200)


class JobSearchTests(TestCase):
    def setUp(self):
        user, company = make_recruiter()
        make_job(company, user, title='Django Developer', location='Hyderabad', experience_min=0, experience_max=2)
        make_job(company, user, title='Data Analyst', location='Mumbai', employment_type='contract',
                 experience_min=3, experience_max=6, salary_max=900000)
        make_job(company, user, title='Python Intern', location='Hyderabad', employment_type='internship')

    def test_keyword_location_type_and_experience_filters(self):
        self.assertEqual(search_jobs({'q': 'django'}).count(), 1)
        self.assertEqual(search_jobs({'location': 'hyder'}).count(), 2)
        self.assertEqual(search_jobs({'employment_type': 'contract'}).count(), 1)
        self.assertEqual(search_jobs({'experience': '4'}).count(), 1)

    def test_sorting_by_title(self):
        titles = [job.title for job in search_jobs({'sort': 'title'})]
        self.assertEqual(titles, sorted(titles))

    def test_search_page_and_pagination(self):
        user, company = make_recruiter(email='r2@example.com', company_name='Big Co')
        for number in range(12):
            make_job(company, user, title=f'Role {number}')
        response = self.client.get(reverse('jobs:list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['page_obj']), 9)
        self.assertEqual(len(self.client.get(reverse('jobs:list') + '?page=2').context['page_obj']), 6)


class RecruiterJobManagementTests(TestCase):
    def setUp(self):
        self.user, self.company = make_recruiter()
        self.client.login(username='recruiter@example.com', password=PASSWORD)

    def _payload(self, **extra):
        data = {'title': 'Backend Engineer', 'description': 'Write APIs', 'location': 'Pune',
                'employment_type': 'full_time', 'experience_min': 1, 'experience_max': 4, 'salary_currency': 'INR',
                'deadline': (datetime.date.today() + datetime.timedelta(days=20)).isoformat(),
                'skills': 'Python, Django, python'}
        data.update(extra)
        return data

    def test_create_job_is_draft_with_unique_skills(self):
        response = self.client.post(reverse('jobs:create'), self._payload())
        self.assertRedirects(response, reverse('jobs:manage'))
        job = Job.objects.get(title='Backend Engineer')
        self.assertEqual(job.status, Job.Status.DRAFT)
        self.assertEqual(job.skills.count(), 2)

    def test_invalid_experience_range_and_past_deadline_rejected(self):
        self.client.post(reverse('jobs:create'), self._payload(experience_min=9, experience_max=2))
        self.client.post(reverse('jobs:create'), self._payload(deadline='2000-01-01'))
        self.assertEqual(Job.objects.count(), 0)

    def test_publish_pause_close_flow(self):
        job = make_job(self.company, self.user, status='draft')
        for target in ('published', 'paused', 'published', 'closed'):
            self.client.post(reverse('jobs:status', args=[job.pk]), {'status': target})
            job.refresh_from_db()
            self.assertEqual(job.status, target)

    def test_unverified_company_cannot_publish(self):
        user, company = make_recruiter(email='u@example.com', company_name='Unverified', verified=False)
        job = make_job(company, user, status='draft')
        with self.assertRaises(ServiceError):
            change_job_status(job, 'published')

    def test_cannot_edit_another_companys_job(self):
        other_user, other_company = make_recruiter(email='o@example.com', company_name='Other')
        job = make_job(other_company, other_user)
        self.assertEqual(self.client.get(reverse('jobs:edit', args=[job.pk])).status_code, 404)
        self.client.post(reverse('jobs:status', args=[job.pk]), {'status': 'closed'})
        job.refresh_from_db()
        self.assertEqual(job.status, Job.Status.PUBLISHED)

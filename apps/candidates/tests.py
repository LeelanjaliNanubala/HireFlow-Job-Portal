from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.applications.models import JobApplication
from apps.common.factories import (PASSWORD, PDF_BYTES, TEST_MEDIA_ROOT, make_admin, make_candidate, make_job,
                                   make_recruiter, make_resume)

from .models import Resume


@override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
class ResumeTests(TestCase):
    def setUp(self):
        self.user, self.profile = make_candidate()
        self.client.login(username='candidate@example.com', password=PASSWORD)

    def test_valid_pdf_upload(self):
        upload = SimpleUploadedFile('my cv.pdf', PDF_BYTES, content_type='application/pdf')
        response = self.client.post(reverse('candidates:resumes'), {'file': upload})
        self.assertRedirects(response, reverse('candidates:resumes'))
        resume = Resume.objects.get()
        self.assertTrue(resume.is_default)
        self.assertEqual(resume.original_name, 'my cv.pdf')
        self.assertIn(f'candidate_{self.profile.pk}', resume.file.name)

    def test_wrong_extension_rejected(self):
        upload = SimpleUploadedFile('virus.exe', b'MZ....', content_type='application/octet-stream')
        self.client.post(reverse('candidates:resumes'), {'file': upload})
        self.assertEqual(Resume.objects.count(), 0)

    def test_fake_pdf_content_rejected(self):
        upload = SimpleUploadedFile('fake.pdf', b'this is not a pdf', content_type='application/pdf')
        self.client.post(reverse('candidates:resumes'), {'file': upload})
        self.assertEqual(Resume.objects.count(), 0)

    @override_settings(MAX_RESUME_SIZE_MB=1)
    def test_too_large_file_rejected(self):
        upload = SimpleUploadedFile('big.pdf', b'%PDF' + b'0' * (1024 * 1024 + 10), content_type='application/pdf')
        self.client.post(reverse('candidates:resumes'), {'file': upload})
        self.assertEqual(Resume.objects.count(), 0)

    def test_resume_file_has_no_public_url(self):
        resume = make_resume(self.profile)
        with self.assertRaises(ValueError):
            resume.file.url

    def test_owner_can_download(self):
        resume = make_resume(self.profile)
        response = self.client.get(reverse('candidates:resume_download', args=[resume.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), PDF_BYTES)

    def test_other_candidate_cannot_download(self):
        resume = make_resume(self.profile)
        make_candidate(email='other@example.com')
        self.client.logout()
        self.client.login(username='other@example.com', password=PASSWORD)
        self.assertEqual(self.client.get(reverse('candidates:resume_download', args=[resume.pk])).status_code, 403)

    def test_anonymous_cannot_download(self):
        resume = make_resume(self.profile)
        self.client.logout()
        self.assertEqual(self.client.get(reverse('candidates:resume_download', args=[resume.pk])).status_code, 302)

    def test_recruiter_download_requires_application_to_their_company(self):
        resume = make_resume(self.profile)
        owner, company = make_recruiter(email='owner@example.com', company_name='Owner Co')
        stranger, _ = make_recruiter(email='stranger@example.com', company_name='Stranger Co')
        job = make_job(company, owner)
        JobApplication.objects.create(job=job, candidate=self.profile, resume=resume)
        url = reverse('candidates:resume_download', args=[resume.pk])
        self.client.logout()
        self.client.login(username='stranger@example.com', password=PASSWORD)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.logout()
        self.client.login(username='owner@example.com', password=PASSWORD)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_can_download(self):
        resume = make_resume(self.profile)
        make_admin()
        self.client.logout()
        self.client.login(username='admin@example.com', password=PASSWORD)
        self.assertEqual(self.client.get(reverse('candidates:resume_download', args=[resume.pk])).status_code, 200)

    def test_resume_used_in_application_cannot_be_deleted(self):
        resume = make_resume(self.profile)
        owner, company = make_recruiter()
        JobApplication.objects.create(job=make_job(company, owner), candidate=self.profile, resume=resume)
        self.client.post(reverse('candidates:resume_delete', args=[resume.pk]))
        self.assertTrue(Resume.objects.filter(pk=resume.pk).exists())


class ProfileTests(TestCase):
    def setUp(self):
        self.user, self.profile = make_candidate()
        self.client.login(username='candidate@example.com', password=PASSWORD)

    def test_profile_update_changes_name(self):
        self.client.post(reverse('candidates:profile'), {'full_name': 'New Name', 'phone': '123',
                                                          'location': 'Pune', 'headline': 'Dev'})
        self.user.refresh_from_db()
        self.assertEqual(self.user.full_name, 'New Name')

    def test_add_education_experience_and_skill(self):
        self.client.post(reverse('candidates:education'), {'degree': 'BSc', 'institution': 'Uni',
                                                            'start_year': 2018, 'end_year': 2021})
        self.client.post(reverse('candidates:experience'), {'job_title': 'Dev', 'company_name': 'X',
                                                             'start_date': '2022-01-01', 'is_current': 'on'})
        self.client.post(reverse('candidates:skills'), {'skill_name': 'python', 'proficiency': 'advanced'})
        self.client.post(reverse('candidates:skills'), {'skill_name': 'Python', 'proficiency': 'expert'})
        self.assertEqual(self.profile.educations.count(), 1)
        self.assertEqual(self.profile.experiences.count(), 1)
        self.assertEqual(self.profile.candidate_skills.count(), 1)  # 'python' and 'Python' are one skill

    def test_education_end_before_start_rejected(self):
        self.client.post(reverse('candidates:education'), {'degree': 'BSc', 'institution': 'Uni',
                                                            'start_year': 2021, 'end_year': 2018})
        self.assertEqual(self.profile.educations.count(), 0)

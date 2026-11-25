"""Helper functions that create test data (used by the automated tests)."""
import atexit
import datetime
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import User
from apps.candidates.models import CandidateProfile, Resume
from apps.companies.models import Company, RecruiterProfile
from apps.jobs.models import Job

PASSWORD = 'Str0ng-Pass!word'
PDF_BYTES = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n'

# Resumes written during tests go to a temporary folder that is deleted afterwards.
TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix='hireflow_test_media_')
atexit.register(shutil.rmtree, TEST_MEDIA_ROOT, ignore_errors=True)


def make_candidate(email='candidate@example.com', name='Test Candidate'):
    user = User.objects.create_user(email=email, password=PASSWORD, full_name=name, role=User.Role.CANDIDATE)
    profile = CandidateProfile.objects.create(user=user)
    return user, profile


def make_recruiter(email='recruiter@example.com', company_name='Acme Corp', verified=True):
    company = Company.objects.create(
        name=company_name,
        verification_status=Company.Verification.VERIFIED if verified else Company.Verification.PENDING)
    user = User.objects.create_user(email=email, password=PASSWORD, full_name='Test Recruiter',
                                    role=User.Role.RECRUITER)
    RecruiterProfile.objects.create(user=user, company=company, designation='HR')
    return user, company


def make_admin(email='admin@example.com'):
    return User.objects.create_superuser(email=email, password=PASSWORD, full_name='Test Admin')


def make_job(company, user=None, **overrides):
    values = dict(title='Python Developer', description='Build things with Django.', location='Hyderabad',
                  employment_type=Job.EmploymentType.FULL_TIME, experience_min=0, experience_max=3,
                  deadline=datetime.date.today() + datetime.timedelta(days=30),
                  status=Job.Status.PUBLISHED, created_by=user)
    values.update(overrides)
    return Job.objects.create(company=company, **values)


def make_resume(profile, name='cv.pdf', content=PDF_BYTES):
    resume = Resume(candidate=profile, original_name=name, file_type='pdf', file_size=len(content),
                    is_default=not profile.resumes.exists())
    resume.file = SimpleUploadedFile(name, content, content_type='application/pdf')
    resume.save()
    return resume

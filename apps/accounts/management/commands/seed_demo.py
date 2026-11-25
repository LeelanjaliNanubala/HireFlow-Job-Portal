"""Create demo data:  python manage.py seed_demo

Creates demo users, a verified company, jobs and one application so every dashboard has data.
THESE ARE DEMO ACCOUNTS WITH KNOWN PASSWORDS - never run this on a real/production database.
"""
import datetime

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.applications.models import JobApplication
from apps.applications.services import apply_to_job, change_status
from apps.candidates.models import CandidateProfile, CandidateSkill, Education, Resume, WorkExperience
from apps.candidates.services import get_or_create_skill
from apps.companies.models import Company, RecruiterProfile
from apps.interviews.services import schedule_interview
from apps.jobs.models import Job
from apps.jobs.services import set_job_skills

ADMIN = ('admin@hireflow.test', 'Admin@12345')
RECRUITER = ('recruiter@hireflow.test', 'Recruiter@12345')
RECRUITER_2 = ('recruiter2@hireflow.test', 'Recruiter@12345')
CANDIDATE = ('candidate@hireflow.test', 'Candidate@12345')
CANDIDATE_2 = ('candidate2@hireflow.test', 'Candidate@12345')

MINIMAL_PDF = (b'%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n'
               b'3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 100]>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n')

JOBS = [
    ('Python Django Developer', 'Hyderabad', 'full_time', 1, 4, 600000, 1200000, True,
     ['Python', 'Django', 'MySQL', 'REST API'],
     'Build and maintain Django web applications and REST APIs for our recruitment products.',
     'Design database models\nWrite clean, tested code\nReview pull requests'),
    ('Frontend Developer (Bootstrap + JavaScript)', 'Bengaluru', 'full_time', 0, 2, 400000, 800000, True,
     ['HTML', 'CSS', 'JavaScript', 'Bootstrap'],
     'Create responsive user interfaces with HTML, CSS, Bootstrap and JavaScript.',
     'Build reusable components\nFix UI bugs\nImprove accessibility'),
    ('Data Analyst', 'Mumbai', 'contract', 2, 5, 500000, 900000, False,
     ['SQL', 'Excel', 'Python'], 'Turn recruitment data into clear insights and dashboards.',
     'Write SQL queries\nBuild charts\nPresent findings'),
    ('Software Engineering Intern', 'Remote', 'internship', 0, 0, 120000, 240000, False,
     ['Python', 'Git'], 'Learn on the job while building real features with a friendly team.',
     'Fix small bugs\nWrite tests\nDocument features'),
    ('QA Test Engineer', 'Hyderabad', 'full_time', 1, 3, 450000, 850000, False,
     ['Testing', 'Postman', 'SQL'], 'Test web applications and REST APIs and report defects clearly.',
     'Write test cases\nTest APIs with Postman\nReport bugs'),
]


class Command(BaseCommand):
    help = 'Create demo users, a verified company, jobs and a sample application.'

    @transaction.atomic
    def handle(self, *args, **options):
        if User.objects.filter(email=RECRUITER[0]).exists():
            self.stdout.write(self.style.WARNING('Demo data already exists. Nothing to do.'))
            return

        User.objects.create_superuser(email=ADMIN[0], password=ADMIN[1], full_name='Demo Admin')

        # Recruiter 1 with a VERIFIED company, recruiter 2 with a PENDING company (to try admin verification).
        rec = User.objects.create_user(email=RECRUITER[0], password=RECRUITER[1], full_name='Riya Recruiter',
                                       role=User.Role.RECRUITER)
        company = Company.objects.create(
            name='Acme Technologies', industry='Software', size=Company.Size.M, location='Hyderabad',
            website='https://example.com', description='Acme builds software that helps companies hire better.',
            verification_status=Company.Verification.VERIFIED, verified_at=timezone.now())
        RecruiterProfile.objects.create(user=rec, company=company, designation='Talent Acquisition Lead')

        rec2 = User.objects.create_user(email=RECRUITER_2[0], password=RECRUITER_2[1], full_name='Sam Second',
                                        role=User.Role.RECRUITER)
        company2 = Company.objects.create(name='Startup Labs', industry='Education', location='Pune')
        RecruiterProfile.objects.create(user=rec2, company=company2, designation='HR Manager')

        deadline = datetime.date.today() + datetime.timedelta(days=45)
        jobs = []
        for title, location, kind, exp_min, exp_max, sal_min, sal_max, featured, skills, desc, resp in JOBS:
            job = Job.objects.create(
                company=company, created_by=rec, title=title, description=desc, responsibilities=resp,
                location=location, employment_type=kind, experience_min=exp_min, experience_max=exp_max,
                salary_min=sal_min, salary_max=sal_max, deadline=deadline, status=Job.Status.PUBLISHED,
                published_at=timezone.now(), is_featured=featured)
            set_job_skills(job, skills)
            jobs.append(job)
        Job.objects.create(company=company2, created_by=rec2, title='Content Writer', description='Draft job',
                           location='Pune', deadline=deadline, status=Job.Status.DRAFT)

        # Candidates
        profiles = []
        for (email, password), name, headline in ((CANDIDATE, 'Chaitra Candidate', 'Python developer, 2 years experience'),
                                                  (CANDIDATE_2, 'Dev Second', 'Fresher interested in testing')):
            user = User.objects.create_user(email=email, password=password, full_name=name,
                                            role=User.Role.CANDIDATE)
            profile = CandidateProfile.objects.create(user=user, phone='9000000000', location='Hyderabad',
                                                      headline=headline, summary='Demo candidate profile.',
                                                      years_experience=2)
            Education.objects.create(candidate=profile, degree='B.Tech', institution='Demo University',
                                     field_of_study='Computer Science', start_year=2018, end_year=2022)
            WorkExperience.objects.create(candidate=profile, job_title='Junior Developer', company_name='Demo Soft',
                                          start_date=datetime.date(2022, 7, 1), is_current=True,
                                          description='Worked on web applications.')
            for skill_name in ('Python', 'Django', 'SQL'):
                CandidateSkill.objects.create(candidate=profile, skill=get_or_create_skill(skill_name))
            resume = Resume(candidate=profile, original_name='Demo_Resume.pdf', file_type='pdf',
                            file_size=len(MINIMAL_PDF), is_default=True)
            resume.file.save('Demo_Resume.pdf', ContentFile(MINIMAL_PDF), save=False)
            resume.save()
            profiles.append((profile, resume))

        # One application that is already shortlisted with an interview, one still under review.
        profile, resume = profiles[0]
        application = apply_to_job(candidate=profile, job_id=jobs[0].pk, resume_id=resume.pk,
                                   cover_letter='I would love to join Acme.')
        change_status(application=application, new_status=JobApplication.Status.SHORTLISTED, actor=rec,
                      note='Strong Django skills.')
        schedule_interview(application=application, actor=rec,
                           scheduled_at=timezone.now() + datetime.timedelta(days=3), mode='online',
                           meeting_details='https://meet.example.com/hireflow-demo', interviewer_name='Riya',
                           duration_minutes=45)
        profile2, resume2 = profiles[1]
        second = apply_to_job(candidate=profile2, job_id=jobs[4].pk, resume_id=resume2.pk)
        change_status(application=second, new_status=JobApplication.Status.UNDER_REVIEW, actor=rec)

        self.stdout.write(self.style.SUCCESS('Demo data created. Demo logins (password in brackets):'))
        for email, password in (ADMIN, RECRUITER, RECRUITER_2, CANDIDATE, CANDIDATE_2):
            self.stdout.write(f'  {email}   [{password}]')

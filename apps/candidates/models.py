"""Candidate profile, education, experience, skills, resumes and saved jobs."""
import os
import uuid

from django.conf import settings
from django.db import models

from .storage import get_private_storage


def resume_upload_path(instance, filename):
    """Random file name inside media_private/resumes/candidate_<id>/ (the original name is stored separately)."""
    extension = os.path.splitext(filename)[1].lower()
    return f'resumes/candidate_{instance.candidate_id}/{uuid.uuid4().hex}{extension}'


class CandidateProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='candidate_profile')
    phone = models.CharField(max_length=20, blank=True)
    location = models.CharField(max_length=120, blank=True)
    headline = models.CharField(max_length=160, blank=True, help_text='For example: Python developer with 2 years of experience')
    summary = models.TextField(blank=True)
    portfolio_url = models.URLField(blank=True)
    years_experience = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.full_name or self.user.email

    def completeness(self):
        """Profile completeness in percent (8 simple checks)."""
        checks = [
            bool(self.phone), bool(self.location), bool(self.headline), bool(self.summary),
            self.educations.exists(), self.experiences.exists(),
            self.candidate_skills.exists(), self.resumes.exists(),
        ]
        return int(sum(checks) * 100 / len(checks))


class Education(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='educations')
    degree = models.CharField(max_length=150)
    institution = models.CharField(max_length=200)
    field_of_study = models.CharField(max_length=150, blank=True)
    start_year = models.PositiveSmallIntegerField()
    end_year = models.PositiveSmallIntegerField(null=True, blank=True)
    grade = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['-start_year']
        verbose_name_plural = 'education'

    def __str__(self):
        return f'{self.degree} - {self.institution}'


class WorkExperience(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='experiences')
    job_title = models.CharField(max_length=150)
    company_name = models.CharField(max_length=200)
    location = models.CharField(max_length=120, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=False)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f'{self.job_title} at {self.company_name}'


class Skill(models.Model):
    name = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class CandidateSkill(models.Model):
    class Proficiency(models.TextChoices):
        BEGINNER = 'beginner', 'Beginner'
        INTERMEDIATE = 'intermediate', 'Intermediate'
        ADVANCED = 'advanced', 'Advanced'
        EXPERT = 'expert', 'Expert'

    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='candidate_skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='candidate_skills')
    proficiency = models.CharField(max_length=15, choices=Proficiency.choices, default=Proficiency.INTERMEDIATE)

    class Meta:
        ordering = ['skill__name']
        constraints = [models.UniqueConstraint(fields=['candidate', 'skill'], name='unique_skill_per_candidate')]

    def __str__(self):
        return f'{self.candidate} - {self.skill}'


class Resume(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='resumes')
    file = models.FileField(upload_to=resume_upload_path, storage=get_private_storage, max_length=255)
    original_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=10)
    file_size = models.PositiveIntegerField(default=0)
    is_default = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.original_name

    @property
    def size_display(self):
        return f'{self.file_size / 1024:.0f} KB' if self.file_size < 1024 * 1024 else f'{self.file_size / 1024 / 1024:.1f} MB'


class SavedJob(models.Model):
    candidate = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='saved_jobs')
    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, related_name='saved_by')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-saved_at']
        constraints = [models.UniqueConstraint(fields=['candidate', 'job'], name='unique_saved_job')]

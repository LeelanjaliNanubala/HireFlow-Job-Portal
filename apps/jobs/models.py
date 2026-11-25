"""Job postings and the skills they require."""
from django.conf import settings
from django.db import models
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone

from apps.companies.models import Company


class JobQuerySet(models.QuerySet):
    def public(self):
        """Jobs that candidates may see: published, not hidden, not expired, company verified."""
        return self.filter(
            status=Job.Status.PUBLISHED,
            is_hidden_by_admin=False,
            deadline__gte=timezone.localdate(),
            company__verification_status=Company.Verification.VERIFIED,
        )


class Job(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PUBLISHED = 'published', 'Published'
        PAUSED = 'paused', 'Paused'
        CLOSED = 'closed', 'Closed'

    class EmploymentType(models.TextChoices):
        FULL_TIME = 'full_time', 'Full-time'
        PART_TIME = 'part_time', 'Part-time'
        CONTRACT = 'contract', 'Contract'
        INTERNSHIP = 'internship', 'Internship'
        FREELANCE = 'freelance', 'Freelance'

    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='jobs')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='created_jobs')
    title = models.CharField(max_length=200)
    description = models.TextField()
    responsibilities = models.TextField(blank=True)
    location = models.CharField(max_length=120)
    employment_type = models.CharField(max_length=20, choices=EmploymentType.choices,
                                       default=EmploymentType.FULL_TIME)
    experience_min = models.PositiveSmallIntegerField(default=0)
    experience_max = models.PositiveSmallIntegerField(default=0)
    salary_min = models.PositiveIntegerField(null=True, blank=True)
    salary_max = models.PositiveIntegerField(null=True, blank=True)
    salary_currency = models.CharField(max_length=3, default='INR')
    deadline = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    is_featured = models.BooleanField(default=False)
    is_hidden_by_admin = models.BooleanField(default=False)
    moderation_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    skills = models.ManyToManyField('candidates.Skill', through='JobSkill', related_name='jobs')

    objects = JobQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'deadline']),
            models.Index(fields=['location']),
            models.Index(fields=['employment_type']),
            models.Index(fields=['title']),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(experience_min__lte=F('experience_max')),
                                   name='job_experience_min_lte_max'),
        ]

    def __str__(self):
        return f'{self.title} ({self.company})'

    def get_absolute_url(self):
        return reverse('jobs:detail', args=[self.pk])

    @property
    def is_open(self):
        return (self.status == self.Status.PUBLISHED and not self.is_hidden_by_admin
                and self.deadline >= timezone.localdate() and self.company.is_verified)

    @property
    def salary_display(self):
        if self.salary_min and self.salary_max:
            return f'{self.salary_currency} {self.salary_min:,} - {self.salary_max:,}'
        if self.salary_max or self.salary_min:
            return f'{self.salary_currency} {(self.salary_max or self.salary_min):,}'
        return 'Not disclosed'

    @property
    def experience_display(self):
        if self.experience_min == self.experience_max:
            return f'{self.experience_min} yrs'
        return f'{self.experience_min}-{self.experience_max} yrs'


class JobSkill(models.Model):
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='job_skills')
    skill = models.ForeignKey('candidates.Skill', on_delete=models.CASCADE, related_name='job_skills')
    is_required = models.BooleanField(default=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['job', 'skill'], name='unique_skill_per_job')]

    def __str__(self):
        return f'{self.job_id}:{self.skill}'

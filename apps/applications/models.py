"""Job applications and their status history."""
from django.conf import settings
from django.db import models


class JobApplication(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Submitted'
        UNDER_REVIEW = 'under_review', 'Under Review'
        SHORTLISTED = 'shortlisted', 'Shortlisted'
        INTERVIEW_SCHEDULED = 'interview_scheduled', 'Interview Scheduled'
        INTERVIEW_COMPLETED = 'interview_completed', 'Interview Completed'
        SELECTED = 'selected', 'Selected'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'

    job = models.ForeignKey('jobs.Job', on_delete=models.CASCADE, related_name='applications')
    candidate = models.ForeignKey('candidates.CandidateProfile', on_delete=models.CASCADE,
                                  related_name='applications')
    resume = models.ForeignKey('candidates.Resume', on_delete=models.PROTECT, related_name='applications')
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.SUBMITTED)
    cover_letter = models.TextField(blank=True)
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-applied_at']
        constraints = [
            # Database-level guard: one application per candidate per job.
            models.UniqueConstraint(fields=['job', 'candidate'], name='unique_application_per_candidate_job'),
        ]
        indexes = [models.Index(fields=['status']), models.Index(fields=['applied_at'])]

    def __str__(self):
        return f'{self.candidate} -> {self.job}'


class ApplicationHistory(models.Model):
    """Append-only trail: who changed the status, from what, to what, and when."""

    application = models.ForeignKey(JobApplication, on_delete=models.CASCADE, related_name='history')
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='+')
    old_status = models.CharField(max_length=25, blank=True)
    new_status = models.CharField(max_length=25)
    note = models.TextField(blank=True)
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-changed_at', '-id']
        verbose_name_plural = 'application history'

    def __str__(self):
        return f'{self.application_id}: {self.old_status} -> {self.new_status}'

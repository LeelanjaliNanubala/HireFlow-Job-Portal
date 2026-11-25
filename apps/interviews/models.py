from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Interview(models.Model):
    class Mode(models.TextChoices):
        ONLINE = 'online', 'Online (video call)'
        PHONE = 'phone', 'Phone'
        ONSITE = 'onsite', 'On-site'

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'
        NO_SHOW = 'no_show', 'No show'

    application = models.ForeignKey('applications.JobApplication', on_delete=models.CASCADE,
                                    related_name='interviews')
    round_number = models.PositiveSmallIntegerField(default=1)
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=30)
    mode = models.CharField(max_length=10, choices=Mode.choices, default=Mode.ONLINE)
    meeting_details = models.CharField(max_length=300, blank=True,
                                       help_text='Meeting link (online) or address (on-site)')
    interviewer_name = models.CharField(max_length=150, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.SCHEDULED)
    # Feedback is visible to recruiters of the company only - never shown to candidates.
    feedback = models.TextField(blank=True)
    rating = models.PositiveSmallIntegerField(null=True, blank=True,
                                              validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                   related_name='+')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_at']
        indexes = [models.Index(fields=['status', 'scheduled_at'])]

    def __str__(self):
        return f'Round {self.round_number} - application {self.application_id}'

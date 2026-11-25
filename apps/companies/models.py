"""Company and RecruiterProfile."""
from django.conf import settings
from django.db import models


class Company(models.Model):
    class Verification(models.TextChoices):
        PENDING = 'pending', 'Pending'
        VERIFIED = 'verified', 'Verified'
        REJECTED = 'rejected', 'Rejected'

    class Size(models.TextChoices):
        XS = '1-10', '1-10 employees'
        S = '11-50', '11-50 employees'
        M = '51-200', '51-200 employees'
        L = '201-500', '201-500 employees'
        XL = '500+', '500+ employees'

    name = models.CharField(max_length=200)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=100, blank=True)
    size = models.CharField(max_length=10, choices=Size.choices, blank=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=120, blank=True)
    verification_status = models.CharField(max_length=10, choices=Verification.choices,
                                           default=Verification.PENDING, db_index=True)
    verification_note = models.TextField(blank=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'companies'

    def __str__(self):
        return self.name

    @property
    def is_verified(self):
        return self.verification_status == self.Verification.VERIFIED


class RecruiterProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='recruiter_profile')
    company = models.ForeignKey(Company, null=True, blank=True, on_delete=models.SET_NULL, related_name='recruiters')
    designation = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.email} @ {self.company}'

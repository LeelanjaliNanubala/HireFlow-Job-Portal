from rest_framework import serializers

from .models import JobApplication


class ApplicationSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='job.title', read_only=True)
    company = serializers.CharField(source='job.company.name', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = JobApplication
        fields = ['id', 'job', 'job_title', 'company', 'resume', 'status', 'status_label', 'cover_letter',
                  'applied_at', 'updated_at']


class RecruiterApplicationSerializer(serializers.ModelSerializer):
    """What a recruiter sees about an applicant (no private resume URL)."""
    candidate_name = serializers.CharField(source='candidate.user.full_name', read_only=True)
    candidate_email = serializers.CharField(source='candidate.user.email', read_only=True)
    headline = serializers.CharField(source='candidate.headline', read_only=True)
    status_label = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = JobApplication
        fields = ['id', 'job', 'candidate_name', 'candidate_email', 'headline', 'resume', 'status',
                  'status_label', 'cover_letter', 'applied_at', 'updated_at']


class ApplyInputSerializer(serializers.Serializer):
    job_id = serializers.IntegerField()
    resume_id = serializers.IntegerField()
    cover_letter = serializers.CharField(required=False, allow_blank=True, max_length=3000)


class StatusInputSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=JobApplication.Status.choices)
    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)

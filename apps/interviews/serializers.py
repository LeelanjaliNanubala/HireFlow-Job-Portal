from django.utils import timezone
from rest_framework import serializers

from .models import Interview


class InterviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interview
        fields = ['id', 'application', 'round_number', 'scheduled_at', 'duration_minutes', 'mode',
                  'meeting_details', 'interviewer_name', 'status', 'created_at']
        read_only_fields = fields


class InterviewCreateSerializer(serializers.Serializer):
    scheduled_at = serializers.DateTimeField()
    duration_minutes = serializers.IntegerField(min_value=10, max_value=480, default=30)
    mode = serializers.ChoiceField(choices=Interview.Mode.choices)
    meeting_details = serializers.CharField(required=False, allow_blank=True, max_length=300)
    interviewer_name = serializers.CharField(required=False, allow_blank=True, max_length=150)

    def validate_scheduled_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError('The interview must be scheduled in the future.')
        return value

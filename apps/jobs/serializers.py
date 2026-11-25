import datetime

from rest_framework import serializers

from .models import Job


class JobSerializer(serializers.ModelSerializer):
    """Read-only representation of a job."""
    company = serializers.SerializerMethodField()
    skills = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = ['id', 'title', 'company', 'description', 'responsibilities', 'location', 'employment_type',
                  'experience_min', 'experience_max', 'salary_min', 'salary_max', 'salary_currency', 'deadline',
                  'status', 'skills', 'published_at', 'created_at', 'updated_at']

    def get_company(self, job):
        return {'id': job.company_id, 'name': job.company.name}

    def get_skills(self, job):
        return [job_skill.skill.name for job_skill in job.job_skills.all()]


class JobWriteSerializer(serializers.ModelSerializer):
    """Used by POST /api/jobs/ and PATCH /api/jobs/<id>/."""
    skills = serializers.ListField(child=serializers.CharField(max_length=60), required=False, allow_empty=True,
                                   max_length=25)
    status = serializers.ChoiceField(choices=Job.Status.choices, required=False)

    class Meta:
        model = Job
        fields = ['title', 'description', 'responsibilities', 'location', 'employment_type', 'experience_min',
                  'experience_max', 'salary_min', 'salary_max', 'salary_currency', 'deadline', 'skills', 'status']

    def _value(self, attrs, name):
        if name in attrs:
            return attrs[name]
        return getattr(self.instance, name, None) if self.instance else None

    def validate_deadline(self, value):
        if value < datetime.date.today() and (self.instance is None or value != self.instance.deadline):
            raise serializers.ValidationError('The deadline cannot be in the past.')
        return value

    def validate(self, attrs):
        exp_min, exp_max = self._value(attrs, 'experience_min'), self._value(attrs, 'experience_max')
        if exp_min is not None and exp_max is not None and exp_min > exp_max:
            raise serializers.ValidationError({'experience_max': 'Must be greater than or equal to experience_min.'})
        sal_min, sal_max = self._value(attrs, 'salary_min'), self._value(attrs, 'salary_max')
        if sal_min and sal_max and sal_min > sal_max:
            raise serializers.ValidationError({'salary_max': 'Must be greater than or equal to salary_min.'})
        return attrs

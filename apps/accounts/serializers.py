from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import User
from .services import register_user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name', 'role']


class RegisterSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=['candidate', 'recruiter'])
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    company_name = serializers.CharField(required=False, allow_blank=True, max_length=200)
    designation = serializers.CharField(required=False, allow_blank=True, max_length=100)

    def validate_email(self, value):
        value = value.strip().lower()
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('An account with this email already exists.')
        return value

    def validate(self, attrs):
        if attrs['role'] == 'recruiter' and not attrs.get('company_name'):
            raise serializers.ValidationError({'company_name': 'Company name is required for recruiters.'})
        try:
            password_validation.validate_password(attrs['password'])
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password': list(error.messages)})
        return attrs

    def create(self, validated_data):
        return register_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

"""Applications API."""
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import recruiter_company_id
from apps.candidates.services import get_profile
from apps.common.api import IsCandidate, IsRecruiterWithCompany
from apps.common.exceptions import ServiceError
from apps.jobs.models import Job

from .models import JobApplication
from .serializers import (ApplicationSerializer, ApplyInputSerializer, RecruiterApplicationSerializer,
                          StatusInputSerializer)
from .services import RECRUITER_SETTABLE, apply_to_job, change_status


class ApplicationCreateAPIView(APIView):
    """POST /api/applications/ - the candidate is taken from the login, never from the request body."""
    permission_classes = [IsCandidate]

    def post(self, request):
        serializer = ApplyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        application = apply_to_job(candidate=get_profile(request.user), job_id=data['job_id'],
                                   resume_id=data['resume_id'], cover_letter=data.get('cover_letter', ''))
        return Response(ApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


class MyApplicationsAPIView(APIView):
    """GET /api/me/applications/"""
    permission_classes = [IsCandidate]

    def get(self, request):
        qs = (JobApplication.objects.filter(candidate=get_profile(request.user))
              .select_related('job__company'))
        status_filter = request.query_params.get('status')
        if status_filter in JobApplication.Status.values:
            qs = qs.filter(status=status_filter)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(ApplicationSerializer(page, many=True).data)


class JobApplicationsAPIView(APIView):
    """GET /api/recruiter/jobs/<id>/applications/ - applicants of one of YOUR company's jobs."""
    permission_classes = [IsRecruiterWithCompany]

    def get(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        if job.company_id != recruiter_company_id(request.user):
            raise PermissionDenied('This job belongs to another company.')
        qs = JobApplication.objects.filter(job=job).select_related('candidate__user')
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(RecruiterApplicationSerializer(page, many=True).data)


class ApplicationStatusAPIView(APIView):
    """PATCH /api/applications/<id>/status/ - recruiter changes the status."""
    permission_classes = [IsRecruiterWithCompany]

    def patch(self, request, pk):
        application = get_object_or_404(JobApplication.objects.select_related('job'), pk=pk)
        if application.job.company_id != recruiter_company_id(request.user):
            raise PermissionDenied('This application belongs to another company.')
        serializer = StatusInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_status = serializer.validated_data['status']
        if new_status not in RECRUITER_SETTABLE:
            raise ServiceError('Recruiters cannot set this status directly. Interview Scheduled is set by '
                               'scheduling an interview; Withdrawn is set by the candidate.',
                               'status_not_allowed', 400)
        application = change_status(application=application, new_status=new_status, actor=request.user,
                                    note=serializer.validated_data.get('note', ''))
        return Response(RecruiterApplicationSerializer(application).data)

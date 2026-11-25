"""Jobs API: list/search, create, view and update."""
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import recruiter_company_id
from apps.common.api import IsRecruiterWithCompany

from .models import Job
from .serializers import JobSerializer, JobWriteSerializer
from .services import change_job_status, search_jobs, set_job_skills


def _fresh(job_id):
    return Job.objects.select_related('company').prefetch_related('job_skills__skill').get(pk=job_id)


class JobListCreateAPIView(APIView):
    """GET /api/jobs/ (public search)  |  POST /api/jobs/ (recruiter creates a draft job)."""

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsRecruiterWithCompany()]
        return [AllowAny()]

    def get(self, request):
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(search_jobs(request.query_params), request, view=self)
        return paginator.get_paginated_response(JobSerializer(page, many=True).data)

    @transaction.atomic
    def post(self, request):
        serializer = JobWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        skills = data.pop('skills', [])
        wanted_status = data.pop('status', Job.Status.DRAFT)
        job = Job.objects.create(company=request.user.recruiter_profile.company, created_by=request.user,
                                 status=Job.Status.DRAFT, **data)
        set_job_skills(job, skills)
        if wanted_status != Job.Status.DRAFT:
            change_job_status(job, wanted_status, actor=request.user)
        return Response(JobSerializer(_fresh(job.pk)).data, status=status.HTTP_201_CREATED)


class JobDetailAPIView(APIView):
    """GET /api/jobs/<id>/  |  PATCH /api/jobs/<id>/ (owner recruiter only)."""

    def get_permissions(self):
        if self.request.method == 'PATCH':
            return [IsAuthenticated(), IsRecruiterWithCompany()]
        return [AllowAny()]

    def get(self, request, pk):
        job = get_object_or_404(Job.objects.select_related('company').prefetch_related('job_skills__skill'), pk=pk)
        owner = request.user.is_authenticated and recruiter_company_id(request.user) == job.company_id
        if not job.is_open and not owner:
            return Response({'error': {'status': 404, 'code': 'not_found', 'message': 'Job not found.',
                                       'details': None}}, status=status.HTTP_404_NOT_FOUND)
        return Response(JobSerializer(job).data)

    @transaction.atomic
    def patch(self, request, pk):
        job = get_object_or_404(Job, pk=pk)
        if job.company_id != recruiter_company_id(request.user):
            raise PermissionDenied('You can only edit jobs that belong to your company.')
        serializer = JobWriteSerializer(job, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        data = dict(serializer.validated_data)
        skills = data.pop('skills', None)
        new_status = data.pop('status', None)
        for field, value in data.items():
            setattr(job, field, value)
        job.save()
        if skills is not None:
            set_job_skills(job, skills)
        if new_status:
            change_job_status(job, new_status, actor=request.user)
        return Response(JobSerializer(_fresh(job.pk)).data)

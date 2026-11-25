from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.permissions import recruiter_company_id
from apps.applications.models import JobApplication
from apps.common.api import IsRecruiterWithCompany

from .serializers import InterviewCreateSerializer, InterviewSerializer
from .services import schedule_interview


class InterviewCreateAPIView(APIView):
    """POST /api/applications/<id>/interviews/ - schedule an interview (recruiter of the owning company)."""
    permission_classes = [IsRecruiterWithCompany]

    def post(self, request, pk):
        application = get_object_or_404(JobApplication.objects.select_related('job', 'candidate__user'), pk=pk)
        if application.job.company_id != recruiter_company_id(request.user):
            raise PermissionDenied('This application belongs to another company.')
        serializer = InterviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        interview = schedule_interview(application=application, actor=request.user, **serializer.validated_data)
        return Response(InterviewSerializer(interview).data, status=status.HTTP_201_CREATED)

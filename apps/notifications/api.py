from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer


class MyNotificationsAPIView(APIView):
    """GET /api/me/notifications/ - the logged-in user's notifications (?unread=1 for unread only)."""

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        if request.query_params.get('unread') in ('1', 'true'):
            qs = qs.filter(is_read=False)
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(NotificationSerializer(page, many=True).data)

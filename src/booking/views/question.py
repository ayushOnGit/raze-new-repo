from rest_framework import viewsets
from django_filters.rest_framework import DjangoFilterBackend
from booking.models import Question
from booking.serializers.question import (
    AdminQuestionBaseSerializer,
    AdminQuestionDetailSerializer,
)
from base.helpers.api_permissions import AdminPermission


class AdminQuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = AdminQuestionBaseSerializer
    permission_classes = [AdminPermission]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ["event", "products"]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return AdminQuestionDetailSerializer
        return AdminQuestionBaseSerializer

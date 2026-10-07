from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from dojo.models import ActivityType, HourPool, TimeEntry
from dojo.hour_pool.api.serializers import (
    ActivityTypeSerializer,
    HourPoolDetailSerializer,
    HourPoolSerializer,
    TimeEntrySerializer,
)


class ActivityTypeViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ActivityType.objects.filter(is_active=True).order_by("name")
    serializer_class = ActivityTypeSerializer
    permission_classes = [IsAuthenticated]


class HourPoolViewSet(viewsets.ModelViewSet):
    queryset = HourPool.objects.select_related("product", "created_by").order_by("-created_at")
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return HourPoolDetailSerializer
        return HourPoolSerializer

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def get_queryset(self):
        qs = super().get_queryset()
        product_id = self.request.query_params.get("product")
        if product_id:
            qs = qs.filter(product_id=product_id)
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs


class TimeEntryViewSet(viewsets.ModelViewSet):
    queryset = TimeEntry.objects.select_related(
        "pool", "analyst", "activity_type", "pentest_project",
    ).order_by("-date", "-created_at")
    serializer_class = TimeEntrySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = super().get_queryset()
        pool_id = self.request.query_params.get("pool")
        if pool_id:
            qs = qs.filter(pool_id=pool_id)
        analyst_id = self.request.query_params.get("analyst")
        if analyst_id:
            qs = qs.filter(analyst_id=analyst_id)
        return qs

from rest_framework import permissions, viewsets

from dojo.executive_report.api.serializer import ExecutiveReportSerializer
from dojo.executive_report.models import ExecutiveReport


class ExecutiveReportViewSet(viewsets.ModelViewSet):
    queryset = (
        ExecutiveReport.objects
        .select_related('product', 'created_by')
        .prefetch_related('engagements')
        .order_by('-created_at')
    )
    serializer_class = ExecutiveReportSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['product', 'classification']
    search_fields = ['title', 'analyst_name', 'product__name']
    ordering_fields = ['created_at', 'period_start', 'period_end', 'title']

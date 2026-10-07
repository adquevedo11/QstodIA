from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from dojo.security_concept.api.serializer import SecurityConceptSerializer
from dojo.security_concept.models import SecurityConcept


class SecurityConceptViewSet(viewsets.ModelViewSet):
    queryset = SecurityConcept.objects.select_related('created_by').prefetch_related('findings').order_by('-created_at')
    serializer_class = SecurityConceptSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['risk_level', 'client']
    search_fields = ['title', 'reference', 'client']
    ordering_fields = ['created_at', 'risk_level', 'title']

    @action(detail=True, methods=['get'], url_path='findings')
    def findings_list(self, request, pk=None):
        concept = self.get_object()
        findings = concept.findings.values('id', 'title', 'severity', 'date')
        return Response(list(findings))

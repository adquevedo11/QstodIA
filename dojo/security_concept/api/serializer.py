from rest_framework import serializers

from dojo.security_concept.models import RISK_LEVEL_CHOICES, SecurityConcept


class SecurityConceptSerializer(serializers.ModelSerializer):
    risk_level_display = serializers.ChoiceField(
        choices=[c[0] for c in RISK_LEVEL_CHOICES], source='risk_level', read_only=True,
    )
    findings_count = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = SecurityConcept
        fields = [
            'id', 'reference', 'title', 'client', 'scope', 'context_text',
            'analysis', 'risk_level', 'risk_level_display', 'conclusion',
            'analyst_name', 'analyst_title', 'findings', 'findings_count',
            'created_by', 'created_by_name', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_findings_count(self, obj):
        return obj.findings.count()

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)

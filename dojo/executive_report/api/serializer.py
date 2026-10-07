from rest_framework import serializers

from dojo.executive_report.models import EXEC_REPORT_CLASSIFICATION, ExecutiveReport


class ExecutiveReportSerializer(serializers.ModelSerializer):
    classification_display = serializers.ChoiceField(
        choices=[c[0] for c in EXEC_REPORT_CLASSIFICATION], source='classification', read_only=True,
    )
    product_name = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    engagements_count = serializers.SerializerMethodField()

    class Meta:
        model = ExecutiveReport
        fields = [
            'id', 'product', 'product_name', 'engagements', 'engagements_count',
            'title', 'period_start', 'period_end',
            'classification', 'classification_display',
            'analyst_name', 'analyst_title',
            'executive_summary', 'recommendations', 'next_steps', 'conclusion',
            'sections', 'created_by', 'created_by_name', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_product_name(self, obj):
        return obj.product.name if obj.product_id else None

    def get_created_by_name(self, obj):
        if obj.created_by:
            return obj.created_by.get_full_name() or obj.created_by.username
        return None

    def get_engagements_count(self, obj):
        return obj.engagements.count()

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['created_by'] = request.user
        return super().create(validated_data)

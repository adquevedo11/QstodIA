from rest_framework import serializers

from dojo.models import ActivityType, HourPool, TimeEntry


class ActivityTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActivityType
        fields = ["id", "name", "description", "is_active"]


class TimeEntrySerializer(serializers.ModelSerializer):
    analyst_username = serializers.CharField(source="analyst.username", read_only=True)
    activity_name = serializers.CharField(source="activity_type.name", read_only=True)

    class Meta:
        model = TimeEntry
        fields = [
            "id", "pool", "date", "hours", "description",
            "analyst", "analyst_username", "activity_type", "activity_name",
            "pentest_project", "created_at",
        ]
        read_only_fields = ["created_at"]


class HourPoolSerializer(serializers.ModelSerializer):
    used_hours = serializers.SerializerMethodField()
    remaining_hours = serializers.SerializerMethodField()
    usage_pct = serializers.SerializerMethodField()

    class Meta:
        model = HourPool
        fields = [
            "id", "product", "name", "total_hours", "used_hours",
            "remaining_hours", "usage_pct", "alert_threshold_pct",
            "valid_from", "valid_until", "status", "notes",
            "created_at", "created_by",
        ]
        read_only_fields = ["created_at", "created_by"]

    def get_used_hours(self, obj):
        from django.db.models import Sum  # noqa: PLC0415
        return obj.time_entries.aggregate(total=Sum("hours"))["total"] or 0

    def get_remaining_hours(self, obj):
        return obj.total_hours - self.get_used_hours(obj)

    def get_usage_pct(self, obj):
        used = self.get_used_hours(obj)
        return round(used / obj.total_hours * 100, 1) if obj.total_hours else 0


class HourPoolDetailSerializer(HourPoolSerializer):
    time_entries = TimeEntrySerializer(many=True, read_only=True)

    class Meta(HourPoolSerializer.Meta):
        fields = HourPoolSerializer.Meta.fields + ["time_entries"]

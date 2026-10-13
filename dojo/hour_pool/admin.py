from django.contrib import admin

from dojo.hour_pool.models import ActivityType, HourPool, TimeEntry


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active"]
    search_fields = ["name"]


@admin.register(HourPool)
class HourPoolAdmin(admin.ModelAdmin):
    list_display = ["name", "product", "total_hours", "valid_from", "valid_until", "status", "created_by"]
    list_filter = ["status"]
    search_fields = ["name", "product__name"]
    date_hierarchy = "created_at"


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ["date", "hours", "pool", "pentest_project", "activity_type", "analyst"]
    list_filter = ["activity_type"]
    search_fields = ["description", "pool__name"]
    date_hierarchy = "date"

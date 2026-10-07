from django.contrib import admin

from dojo.hour_pool.models import ActivityType, HourPool, TimeEntry


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active"]
    search_fields = ["name"]


@admin.register(HourPool)
class HourPoolAdmin(admin.ModelAdmin):
    list_display = ["name", "product", "total_hours", "start_date", "end_date", "is_active", "created_by"]
    list_filter = ["is_active"]
    search_fields = ["name", "product__name"]
    date_hierarchy = "created_at"


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ["date", "hours", "hour_pool", "pentest_project", "activity_type", "created_by"]
    list_filter = ["activity_type"]
    search_fields = ["description", "hour_pool__name"]
    date_hierarchy = "date"

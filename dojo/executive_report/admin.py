from django.contrib import admin

from dojo.executive_report.models import ExecutiveReport


@admin.register(ExecutiveReport)
class ExecutiveReportAdmin(admin.ModelAdmin):
    list_display = ["title", "product", "classification", "period_start", "period_end", "created_at", "created_by"]
    list_filter = ["classification"]
    search_fields = ["title", "product__name"]
    date_hierarchy = "created_at"

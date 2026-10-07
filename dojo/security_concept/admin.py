from django.contrib import admin

from dojo.security_concept.models import SecurityConcept


@admin.register(SecurityConcept)
class SecurityConceptAdmin(admin.ModelAdmin):
    list_display = ["reference", "title", "client", "risk_level", "created_at", "created_by"]
    list_filter = ["risk_level"]
    search_fields = ["reference", "title", "client"]
    date_hierarchy = "created_at"

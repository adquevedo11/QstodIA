from django.urls import re_path

from dojo.security_concept.ui import views

urlpatterns = [
    re_path(r"^security-concept/$",
        views.security_concept, name="security_concept"),
    re_path(r"^security-concept/historial/$",
        views.security_concept_list, name="security_concept_list"),
    re_path(r"^security-concept/(?P<pk>\d+)/$",
        views.security_concept_view, name="security_concept_view"),
    re_path(r"^security-concept/(?P<pk>\d+)/eliminar/$",
        views.security_concept_delete, name="security_concept_delete"),
]

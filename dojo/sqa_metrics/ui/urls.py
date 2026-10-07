from django.urls import re_path
from dojo.sqa_metrics.ui import views

urlpatterns = [
    re_path(r"^metricas-sqa/$", views.sqa_metrics, name="sqa_metrics"),
]

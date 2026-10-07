from django.urls import re_path
from dojo.go_live_readiness import views

urlpatterns = [
    re_path(r'^engagement/(?P<eid>\d+)/go-live-readiness/$', views.go_live_readiness_view, name='go_live_readiness'),
    re_path(r'^engagement/(?P<eid>\d+)/go-live-readiness/data/$', views.go_live_readiness_data, name='go_live_readiness_data'),
    re_path(r'^engagement/(?P<eid>\d+)/go-live-readiness/pdf/$', views.go_live_readiness_pdf, name='go_live_readiness_pdf'),
]

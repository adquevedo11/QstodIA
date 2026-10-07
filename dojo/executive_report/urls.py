from django.urls import re_path

from dojo.executive_report import views

urlpatterns = [
    re_path(r'^informe-ejecutivo/$', views.executive_report_list, name='executive_report_list'),
    re_path(r'^informe-ejecutivo/nuevo/$', views.executive_report_new, name='executive_report_new'),
    re_path(r'^informe-ejecutivo/(?P<pk>\d+)/$', views.executive_report_view, name='executive_report_view'),
    re_path(r'^informe-ejecutivo/(?P<pk>\d+)/eliminar/$', views.executive_report_delete, name='executive_report_delete'),
    re_path(r'^informe-ejecutivo/engagements/$', views.executive_report_engagements, name='executive_report_engagements'),
    re_path(r'^informe-ejecutivo/generar-resumen/$', views.executive_report_generate_summary, name='executive_report_generate_summary'),
    re_path(r'^informe-ejecutivo/generar-ia/$', views.executive_report_generate_ia, name='executive_report_generate_ia'),
]

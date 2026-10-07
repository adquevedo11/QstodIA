from django.urls import re_path
from dojo.hour_pool.ui import views

urlpatterns = [
    re_path(r'^horas/$',                                              views.hour_pool_list,         name='hour_pool_list'),
    re_path(r'^horas/producto/(?P<product_id>\d+)/nueva/$',          views.hour_pool_new,          name='hour_pool_new'),
    re_path(r'^horas/(?P<pk>\d+)/$',                                  views.hour_pool_detail,       name='hour_pool_detail'),
    re_path(r'^horas/(?P<pk>\d+)/editar/$',                           views.hour_pool_edit,         name='hour_pool_edit'),
    re_path(r'^horas/(?P<pk>\d+)/eliminar/$',                         views.hour_pool_delete,       name='hour_pool_delete'),
    re_path(r'^horas/(?P<pk>\d+)/reporte/$',                          views.hour_pool_report_pdf,   name='hour_pool_report_pdf'),
    re_path(r'^horas/(?P<pool_id>\d+)/registrar/$',                   views.time_entry_add,         name='time_entry_add'),
    re_path(r'^horas/registro/(?P<pk>\d+)/eliminar/$',                views.time_entry_delete,      name='time_entry_delete'),
    re_path(r'^horas/tipos-actividad/$',                              views.activity_type_list,     name='activity_type_list'),
    re_path(r'^horas/tipos-actividad/(?P<pk>\d+)/eliminar/$',         views.activity_type_delete,   name='activity_type_delete'),
]

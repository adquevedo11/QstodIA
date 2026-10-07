from dojo.executive_report.api import path
from dojo.executive_report.api.views import ExecutiveReportViewSet


def add_executive_report_urls(router):
    router.register(path, ExecutiveReportViewSet, basename="executive-report")
    return router

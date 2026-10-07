from dojo.hour_pool.api import path
from dojo.hour_pool.api.views import ActivityTypeViewSet, HourPoolViewSet, TimeEntryViewSet


def add_hour_pool_urls(router):
    router.register(path, HourPoolViewSet, basename="hour-pool")
    router.register(f"{path}-activities", ActivityTypeViewSet, basename="activity-type")
    router.register(f"{path}-entries", TimeEntryViewSet, basename="time-entry")
    return router

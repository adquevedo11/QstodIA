from dojo.security_concept.api import path
from dojo.security_concept.api.views import SecurityConceptViewSet


def add_security_concept_urls(router):
    router.register(path, SecurityConceptViewSet, basename="security-concept")
    return router

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def active_llm_config(request):
    from dojo.llm_config.models import LLMConfig
    config = LLMConfig.get_active()
    if not config:
        return Response({"detail": "No hay configuración LLM activa."}, status=404)
    return Response({
        "provider": config.provider,
        "model_name": config.model_name,
        "api_key": config.api_key,
        "base_url": config.base_url,
        "api_version": config.api_version,
        "deployment_name": config.deployment_name,
    })

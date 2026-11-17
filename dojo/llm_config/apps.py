from django.apps import AppConfig


class LLMConfigAppConfig(AppConfig):
    name = "dojo.llm_config"
    label = "llm_config"
    verbose_name = "LLM Config"

    def ready(self):
        import dojo.llm_config.admin  # noqa: PLC0415 -- admin registration

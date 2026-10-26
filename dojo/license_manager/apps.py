from django.apps import AppConfig


class LicenseManagerConfig(AppConfig):
    name = "dojo.license_manager"
    label = "license_manager"
    verbose_name = "License Manager"

    def ready(self):
        import dojo.license_manager.admin  # noqa: PLC0415 -- admin registration

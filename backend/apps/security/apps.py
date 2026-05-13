from django.apps import AppConfig


class SecurityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.security"
    label = "security"

    def ready(self):
        """Import bootstrap module to initialize TNEENWH on app startup."""
        # DISABLED: TNEENWH bootstrap blocks server startup in dev
        # from apps.security.otp import tneenwh_bootstrap  # noqa: F401
        pass

"""App configuration for the News Application."""

from django.apps import AppConfig


class NewsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "news"
    verbose_name = "News Publication"

    def ready(self):
        # Imported for signal registration.
        import news.signals  # noqa: F401

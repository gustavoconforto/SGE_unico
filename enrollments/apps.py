from django.apps import AppConfig


class EnrollmentsConfig(AppConfig):
    name = "enrollments"
    verbose_name = "Contratos"

    def ready(self):
        # Importa o módulo de sinais para registrá-los
        from . import signals  # noqa: F401

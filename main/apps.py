from django.apps import AppConfig


class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        # Implicitly connect signal handlers decorated with @receiver.
        from . import signals

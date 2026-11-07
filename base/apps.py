from django.apps import AppConfig


class BaseConfig(AppConfig):
    name = "base"

    def ready(self):
        # Django 6.1's blank select option has no pt-BR translation yet.
        from django.db.models import fields

        fields.BLANK_CHOICE_LABEL = "Selecione…"

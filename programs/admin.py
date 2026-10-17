from django.contrib import admin

from programs.models import Program


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin): ...

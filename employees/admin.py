from django.contrib import admin

from .models import Employee, EmployeeRoleType


# Register your models here.
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    ...
@admin.register(EmployeeRoleType)
class EEmployeeRoleTypeAdmin(admin.ModelAdmin):
    ...

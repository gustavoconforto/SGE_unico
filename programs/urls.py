from django.urls import path

from programs.views import (
    program_add_view,
    program_delete_view,
    program_edit_view,
    program_list_view,
)

app_name = "programs"

urlpatterns = [
    path("list/", program_list_view, name="program_list"),
    path("add/", program_add_view, name="program_add"),
    path("edit/<int:pk>/", program_edit_view, name="program_edit"),
    path("delete/<int:pk>/", program_delete_view, name="program_delete"),
]

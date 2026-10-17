from django.urls import path

from programs.views import (
    ProgramCreateView,
    ProgramDeleteView,
    ProgramListView,
    ProgramUpdateView,
)

app_name = "programs"

urlpatterns = [
    path("list/", ProgramListView.as_view(), name="program_list"),
    path("add/", ProgramCreateView.as_view(), name="program_add"),
    path("edit/<int:pk>/", ProgramUpdateView.as_view(), name="program_edit"),
    path("delete/<int:pk>/", ProgramDeleteView.as_view(), name="program_delete"),
]

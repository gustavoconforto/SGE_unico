from django.urls import path

from grades.views import (
    SubjectCreateView,
    SubjectDeleteView,
    SubjectListView,
    SubjectUpdateView,
)

app_name = "grades"

urlpatterns = [
    path("subjects/list/", SubjectListView.as_view(), name="subject_list"),
    path("subjects/add/", SubjectCreateView.as_view(), name="subject_add"),
    path("subjects/edit/<int:pk>/", SubjectUpdateView.as_view(), name="subject_edit"),
    path(
        "subjects/delete/<int:pk>/", SubjectDeleteView.as_view(), name="subject_delete"
    ),
]

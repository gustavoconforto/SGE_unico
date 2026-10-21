from django.urls import path

from grades.views import (
    ExamTypeCreateView,
    ExamTypeDeleteView,
    ExamTypeListView,
    ExamTypeUpdateView,
    GradeEntryOptionsView,
    GradeEntryView,
    GradeLevelSubjectCreateView,
    GradeLevelSubjectDeleteView,
    GradeLevelSubjectListView,
    GradeLevelSubjectTeachersView,
    GradeLevelSubjectUpdateView,
    ReportCardView,
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
    path("exam_types/list/", ExamTypeListView.as_view(), name="exam_type_list"),
    path("exam_types/add/", ExamTypeCreateView.as_view(), name="exam_type_add"),
    path(
        "exam_types/edit/<int:pk>/",
        ExamTypeUpdateView.as_view(),
        name="exam_type_edit",
    ),
    path(
        "exam_types/delete/<int:pk>/",
        ExamTypeDeleteView.as_view(),
        name="exam_type_delete",
    ),
    path(
        "grade_level_subjects/list/",
        GradeLevelSubjectListView.as_view(),
        name="grade_level_subject_list",
    ),
    path(
        "grade_level_subjects/add/",
        GradeLevelSubjectCreateView.as_view(),
        name="grade_level_subject_add",
    ),
    path(
        "grade_level_subjects/teachers/",
        GradeLevelSubjectTeachersView.as_view(),
        name="grade_level_subject_teachers",
    ),
    path(
        "grade_level_subjects/edit/<int:pk>/",
        GradeLevelSubjectUpdateView.as_view(),
        name="grade_level_subject_edit",
    ),
    path(
        "grade_level_subjects/delete/<int:pk>/",
        GradeLevelSubjectDeleteView.as_view(),
        name="grade_level_subject_delete",
    ),
    path("entry/", GradeEntryView.as_view(), name="grade_entry"),
    path("entry/options/", GradeEntryOptionsView.as_view(), name="grade_entry_options"),
    path("report_card/<int:pk>/", ReportCardView.as_view(), name="report_card"),
]

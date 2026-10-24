from django.urls import path

from lessons.views import (
    LectureDayView,
    LectureDeleteView,
    LectureListView,
    LectureUpdateView,
    TimetableUpdateView,
    TimetableView,
)

app_name = "lessons"

urlpatterns = [
    path("timetable/", TimetableView.as_view(), name="timetable"),
    path(
        "timetable/edit/<int:pk>/",
        TimetableUpdateView.as_view(),
        name="timetable_edit",
    ),
    path("lectures/list/", LectureListView.as_view(), name="lecture_list"),
    path("lectures/day/", LectureDayView.as_view(), name="lecture_day"),
    path("lectures/edit/<int:pk>/", LectureUpdateView.as_view(), name="lecture_edit"),
    path(
        "lectures/delete/<int:pk>/",
        LectureDeleteView.as_view(),
        name="lecture_delete",
    ),
]

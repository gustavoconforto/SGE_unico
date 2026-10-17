from django.urls import path

from classes.views import (
    ClassCreateView,
    ClassDeleteView,
    ClassListView,
    ClassUpdateView,
)

app_name = "classes"

urlpatterns = [
    path("list/", ClassListView.as_view(), name="class_list"),
    path("add/", ClassCreateView.as_view(), name="class_add"),
    path("edit/<int:pk>/", ClassUpdateView.as_view(), name="class_edit"),
    path("delete/<int:pk>/", ClassDeleteView.as_view(), name="class_delete"),
]

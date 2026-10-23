from django.urls import path

from q_and_a.views import (
    QandACreateView,
    QandADeleteView,
    QandAListView,
    QandAUpdateView,
)

app_name = "q_and_a"

urlpatterns = [
    path("list/", QandAListView.as_view(), name="q_and_a_list"),
    path("add/", QandACreateView.as_view(), name="q_and_a_add"),
    path("edit/<int:pk>/", QandAUpdateView.as_view(), name="q_and_a_edit"),
    path("delete/<int:pk>/", QandADeleteView.as_view(), name="q_and_a_delete"),
]

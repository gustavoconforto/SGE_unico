from django.urls import path

from base.views import (
    group_add_view,
    group_delete_view,
    group_edit_view,
    group_list_view,
    login_view,
    main_view,
    permission_add_view,
    permission_delete_view,
    permission_edit_view,
    permission_list_view,
    user_add_view,
    user_delete_view,
    user_edit_view,
    user_list_view,
)

app_name = "base"

urlpatterns = [
    path("", main_view, name="main"),
    path("login/", login_view, name="main"),
    path("users/", user_list_view, name="user_list"),
    path("users/add/", user_add_view, name="user_add"),
    path("users/edit/<int:pk>/", user_edit_view, name="user_edit"),
    path("users/delete/<int:pk>/", user_delete_view, name="user_delete"),
    path("groups/", group_list_view, name="group_list"),
    path("groups/add/", group_add_view, name="group_add"),
    path("groups/edit/<int:pk>/", group_edit_view, name="group_edit"),
    path("groups/delete/<int:pk>/", group_delete_view, name="group_delete"),
    path("permissions/", permission_list_view, name="permission_list"),
    path("permissions/add/", permission_add_view, name="permission_add"),
    path(
        "permissions/edit/<int:pk>/",
        permission_edit_view,
        name="permission_edit",
    ),
    path(
        "permissions/delete/<int:pk>/",
        permission_delete_view,
        name="permission_delete",
    ),
]

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="login/login.html", redirect_authenticated_user=True
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("base.urls")),
    path("employees/", include("employees.urls")),
    path("programs/", include("programs.urls")),
    path("enrollments/", include("enrollments.urls")),
    path("students/", include("students.urls")),
    path("classes/", include("classes.urls")),
    path("accounts/", include("accounts.urls")),
    path("billing/", include("billing.urls")),
    path("departments/", include("departments.urls")),
    path("grades/", include("grades.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

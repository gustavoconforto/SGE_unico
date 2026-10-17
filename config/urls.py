from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("base.urls")),
    path("employees/", include("employees.urls")),
    path("programs/", include("programs.urls")),
    path("enrollments/", include("enrollments.urls")),
    path("students/", include("students.urls")),
    path("classes/", include("classes.urls")),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )

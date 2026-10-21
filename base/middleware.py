from django.contrib.auth import middleware
from django.http import HttpResponse


class LoginRequiredMiddleware(middleware.LoginRequiredMiddleware):
    """Require login on every view not marked with @login_not_required.

    htmx follows a 302 and swaps the login page into the target element, so
    htmx requests get an HX-Redirect for a full-page navigation instead.
    """

    def handle_no_permission(self, request, view_func):
        response = super().handle_no_permission(request, view_func)
        if request.headers.get("HX-Request") == "true":
            return HttpResponse(headers={"HX-Redirect": response.url})
        return response

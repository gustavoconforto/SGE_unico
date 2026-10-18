from functools import reduce
from operator import or_

from django.db.models import Q


def apply_search(queryset, query, search_fields):
    """Filter queryset with icontains over search_fields (OR between fields)."""
    query = (query or "").strip()
    if not query or not search_fields:
        return queryset
    conditions = [Q(**{f"{field}__icontains": query}) for field in search_fields]
    return queryset.filter(reduce(or_, conditions))


def is_htmx_partial(request):
    """True for htmx requests that expect only a fragment (not history restores)."""
    return (
        request.headers.get("HX-Request") == "true"
        and request.headers.get("HX-History-Restore-Request") != "true"
    )


class HtmxSearchMixin:
    """ListView mixin: filters by ?q= and returns only the partial on htmx requests."""

    search_fields = ()
    partial_template_name = None

    def get_search_query(self):
        return self.request.GET.get("q", "").strip()

    def get_queryset(self):
        queryset = super().get_queryset()
        return apply_search(queryset, self.get_search_query(), self.search_fields)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["q"] = self.get_search_query()
        return context

    def get_template_names(self):
        if self.partial_template_name and is_htmx_partial(self.request):
            return [self.partial_template_name]
        return super().get_template_names()


class HtmxFilterMixin(HtmxSearchMixin):
    """HtmxSearchMixin plus a filter form bound to request.GET.

    Each non-empty cleaned value is applied as ``filter_lookups[name]=value``
    (defaults to the field name). Define ``filter_<name>(queryset, value)`` on
    the view for filters that are not a plain lookup.
    """

    filter_form_class = None
    filter_lookups = {}

    def get_filter_form(self):
        if not hasattr(self, "_filter_form"):
            self._filter_form = self.filter_form_class(self.request.GET or None)
        return self._filter_form

    def apply_filters(self, queryset):
        form = self.get_filter_form()
        if not form.is_bound or not form.is_valid():
            return queryset
        for name, value in form.cleaned_data.items():
            if value in (None, "", [], ()):
                continue
            custom = getattr(self, f"filter_{name}", None)
            if custom:
                queryset = custom(queryset, value)
            else:
                queryset = queryset.filter(**{self.filter_lookups.get(name, name): value})
        return queryset

    def get_queryset(self):
        return self.apply_filters(super().get_queryset())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.get_filter_form()
        return context

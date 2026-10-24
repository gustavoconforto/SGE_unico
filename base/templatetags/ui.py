from django import template

from utils.format.number_values import format_cpf

register = template.Library()

# URL segments that belong to the resource whose list sits next to them:
# /accounts/suppliers/edit/3/ is still the "Fornecedores" screen.
RESOURCE_ACTIONS = {"add", "edit", "delete", "detail"}


@register.simple_tag(takes_context=True)
def nav_active(context, url):
    """True when the current page is the menu entry at ``url`` or one of its
    add/edit/delete/detail pages."""
    request = context.get("request")
    if request is None:
        return False
    path = request.path
    if path == url:
        return True
    prefix = url.removesuffix("list/")
    if not path.startswith(prefix):
        return False
    first_segment = path[len(prefix) :].split("/", 1)[0]
    return first_segment in RESOURCE_ACTIONS or first_segment.isdigit()


@register.filter
def document(value):
    """Formats stored CPF (11 digits) or CNPJ (14 digits); anything else as is."""
    value = value or ""
    if len(value) == 11 and value.isdigit():
        return format_cpf(value)
    if len(value) == 14 and value.isdigit():
        return f"{value[:2]}.{value[2:5]}.{value[5:8]}/{value[8:12]}-{value[12:]}"
    return value


@register.filter
def person_kind(value):
    """'Pessoa física' for a CPF, 'Pessoa jurídica' for a CNPJ, '' otherwise."""
    return {11: "Pessoa física", 14: "Pessoa jurídica"}.get(len(value or ""), "")


@register.filter
def active_filter_count(form):
    """Number of filter fields with a value, for the "Filtros" button."""
    if not form or not form.is_bound:
        return 0
    return sum(1 for field in form if field.value() not in (None, "", []))

from django import template
from django.urls import reverse
from urllib.parse import urlencode

register = template.Library()


@register.simple_tag(takes_context=True)
def url_with(context, view_name, *args, **kwargs):
    """
    Build a URL with query parameters.

    Usage:
        {% url_with 'view_name' param1=value1 param2=value2 %}
        {% url_with 'view_name' household=selected_household.id as my_url %}

    Examples:
        {% url_with 'home' household=selected_household.id %}
        -> /home/?household=123

        {% url_with 'chore_detail' chore.id household=h.id status='active' %}
        -> /chores/456/?household=123&status=active
    """
    # Separate URL args from query params
    # Positional args go to the URL, kwargs with non-None values become query params
    query_params = {k: v for k, v in kwargs.items() if v is not None}

    # Build base URL
    url = reverse(view_name, args=args)

    # Append query string if there are params
    if query_params:
        url = f"{url}?{urlencode(query_params)}"

    return url

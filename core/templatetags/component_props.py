from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag(takes_context=True)
def validate_props(context, required='', optional=''):
    """
    Validate component props in DEBUG mode only.

    Usage in component templates:
        {% load component_props %}
        {% validate_props required="label" optional="variant,size,href,type,icon" %}

    Args:
        required: Comma-separated list of required prop names
        optional: Comma-separated list of optional prop names (for documentation)

    Raises:
        TemplateSyntaxError: In DEBUG mode, if a required prop is missing
    """
    if not settings.DEBUG:
        return ''

    required_props = [p.strip() for p in required.split(',') if p.strip()]

    missing = []
    for prop in required_props:
        value = context.get(prop)
        if value is None or value == '':
            missing.append(prop)

    if missing:
        raise template.TemplateSyntaxError(
            f"Component missing required props: {', '.join(missing)}"
        )

    return ''

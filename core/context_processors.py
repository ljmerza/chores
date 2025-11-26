from django.conf import settings


def contact_email(request):
    """
    Inject a contact email address for use in templates.
    """
    return {'CONTACT_EMAIL': getattr(settings, 'CONTACT_EMAIL', '')}

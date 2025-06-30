from django import template
from app.models import Apps

register = template.Library()

@register.simple_tag
def get_app_status(url_keyword):
    try:
        app = Apps.objects.get(url_keyword=url_keyword)
        return {
            'is_temporarily_disabled': app.is_temporarily_disabled,
            'exists': True
        }
    except Apps.DoesNotExist:
        return {
            'is_temporarily_disabled': False,
            'exists': False
        } 
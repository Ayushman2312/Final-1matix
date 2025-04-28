from django import template

register = template.Library()

@register.filter
def getattribute(obj, attr):
    """
    Gets an attribute of an object dynamically from a string name
    Usage: {{ object|getattribute:"attribute_name" }}
    """
    if hasattr(obj, attr):
        return getattr(obj, attr)
    return None 
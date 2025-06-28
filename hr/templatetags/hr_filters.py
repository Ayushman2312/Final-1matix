from django import template
import json
from django.core.serializers import serialize
from django.db.models.query import QuerySet

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiplies the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def divide(value, arg):
    """Divides the value by the argument"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

@register.filter(name='to_json')
def to_json(data):
    """
    Serializes an object to JSON.
    Handles querysets and other data types.
    """
    if isinstance(data, QuerySet):
        # The 'serialize' function returns a string of JSON data
        return serialize('json', data)
    
    # For other data types, use the standard json.dumps
    # It's good practice to handle potential serialization errors
    try:
        return json.dumps(data)
    except TypeError:
        # You might want to return an empty JSON object or a specific error string
        return json.dumps({}) 
from django.conf import settings
from rest_framework.permissions import BasePermission

class AllowOnlyCorsOrigin(BasePermission):
    """
    Custom permission to only allow access to requests from origins
    specified in the CORS_ALLOWED_ORIGINS setting.
    """
    message = "Access from your origin is not allowed."

    def has_permission(self, request, view):
        # Allow OPTIONS requests for CORS preflight, as these are handled by django-cors-headers
        if request.method == 'OPTIONS':
            return True

        origin = request.META.get('HTTP_ORIGIN')
        
        if not origin:
            # No origin header, likely a direct request or from a non-browser client. Block it.
            return False
            
        # Check if the origin is in the allowed list.
        if origin in settings.CORS_ALLOWED_ORIGINS:
            return True
        
        return False 
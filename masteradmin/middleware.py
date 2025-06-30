from django.shortcuts import render
from app.models import Apps
from django.utils.deprecation import MiddlewareMixin

class AppMaintenanceMiddleware(MiddlewareMixin):
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Allow access to admin and masteradmin interfaces
        if request.path.startswith('/admin/') or request.path.startswith('/masteradmin/'):
            return self.get_response(request)

        disabled_apps = Apps.objects.filter(is_temporarily_disabled=True)
        
        for app in disabled_apps:
            if app.url_keyword and f'/{app.url_keyword}/' in request.path:
                return render(request, 'maintenance.html', {'app_name': app.name})
                
        response = self.get_response(request)
        return response 
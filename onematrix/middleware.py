from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin
from app.models import Apps
from django.http import HttpResponseForbidden

class AppAccessMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # We don't want to run this check on admin pages,
        # otherwise we might lock ourselves out.
        if request.path.startswith('/admin/'):
            return None

        disabled_apps = Apps.objects.filter(is_temporarily_disabled=True)

        for app in disabled_apps:
            # Ensure the app has a URL keyword and it's not empty
            if app.url_keyword and app.url_keyword in request.path:
                # The path contains a keyword for a disabled app.
                # Render a page indicating the app is disabled.
                context = {
                    'app_name': app.name,
                    'page_title': f"{app.name} Temporarily Disabled",
                }
                return render(request, 'onematrix/app_disabled.html', context, status=403)
                
        return None 
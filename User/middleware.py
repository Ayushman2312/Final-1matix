from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.models import User

class UserAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Get the current path
        current_path = request.path
        
        # List of paths that don't require authentication
        public_paths = [
            '/user/login/',
            '/user/signup/',
            '/user/google-login/',
            '/user/google-callback/',
            '/user/check-username/',
            '/',  # Root path
            # Add more public paths here
            '/website/',  # Main website page
            '/website/about/',  # About website builder
            '/website/pricing/',  # Pricing page
            '/website/features/',  # Features page
            '/website/templates/',  # Templates showcase
            '/hr_management/employee_dashboard/',
            '/hr_management/employee_resignation/',
            '/hr_management/employee_documents/',
            '/hr_management/employee_profile/',
            '/hr_management/employee_salary_slips/',
            '/hr_management/employee_reimbursement/',
            '/hr_management/employee_leave/',
            '/hr_management/employee/login/',
            '/hr_management/employee_attendance/',
        ]
        
        # Check if the path is a static or media file
        is_static_or_media = (
            current_path.startswith('/static/') or 
            current_path.startswith('/media/') or
            current_path.endswith('.js') or
            current_path.endswith('.css') or
            current_path.endswith('.jpg') or
            current_path.endswith('.png') or
            current_path.endswith('.ico')
        )
        
        # Check if the path is in the admin area
        is_admin_path = current_path.startswith('/alavi07/')
        
        # Check if this is an authenticated user session (using both custom auth and Django auth)
        is_user_authenticated = (
            request.session.get('user_id') is not None or  # Custom auth
            request.session.get('_auth_user_id') is not None  # Django auth
        )
        
        # Check if the path is a data_miner URL and the user is authenticated
        is_data_miner_path = current_path.startswith('/data_miner/')
        
        # Check if the path is public, static/media, admin, or other exempt paths
        is_public_path = (
            current_path in public_paths or 
            current_path.rstrip('/') in [p.rstrip('/') for p in public_paths] or  # Compare paths without trailing slashes
            is_static_or_media or 
            (is_data_miner_path and is_user_authenticated) or  # Allow data_miner access if authenticated
            'contact-us' in current_path or
            'about-us' in current_path or
            'privacy-policy' in current_path or
            'terms-and-conditions' in current_path or
            'cancellation' in current_path or
            'customersupport' in current_path or
            'upi-payment' in current_path or
            'masteradmin' in current_path or
            'alavi07' in current_path or
            'onboarding' in current_path or
            'employee' in current_path or
            'mark-attendance' in current_path or
            'attend' in current_path or
            # Include website public paths
            current_path.startswith('/website/public/') or
            current_path.startswith('/website/s/') or
            # Allow public access to website templates browsing
            current_path.startswith('/website/templates/') or
            # Include all public website slugs
            current_path.startswith('/s/') or
            # Allow access to 404 template
            request.resolver_match and request.resolver_match.url_name == '404' or
            hasattr(request, 'is_404') or
            request.META.get('REDIRECT_STATUS') == '404'
        )
        
        # For debugging - prints the session info for every request
        print(f"Auth check: path={current_path}, user_authenticated={is_user_authenticated}, session={list(request.session.keys())}")
        
        # Special handling for admin paths
        if is_admin_path:
            # Let Django's admin authentication handle admin paths
            return self.get_response(request)
            
        # For user paths that require authentication
        if not is_user_authenticated and not is_public_path:
            # Save the requested URL to redirect back after login
            request.session['next_url'] = current_path
            
            # Special handling for data_miner app
            if current_path.startswith('/data_miner/'):
                print(f"Redirecting unauthenticated user from data_miner to login: {current_path}")
                messages.warning(request, 'Please log in to access Data Miner')
                return redirect('/accounts/login/?next=/data_miner/')
            if current_path.startswith('/business_analytics/'):
                print(f"Redirecting unauthenticated user from data_miner to login: {current_path}")
                messages.warning(request, 'Please log in to access Data Miner')
                return redirect('/accounts/login/?next=/business_analytics/')
                
            # Check if this is a dashboard path
            if current_path == '/user/dashboard/' or current_path.startswith('/dashboard/'):
                messages.warning(request, 'Please log in to access the dashboard')
                return redirect('/user/login/')
            
            # Restrict website dashboard and editing features to logged-in users
            if 'website' in current_path and ('edit' in current_path or 'dashboard' in current_path):
                messages.warning(request, 'Please log in to access website management features')
                return redirect('/user/login/')
            
            # For most other protected paths, redirect to login
            messages.warning(request, 'Please log in to access this page')
            return redirect('/user/login/')
        
        # For all other paths, proceed with the request
        response = self.get_response(request)
        return response

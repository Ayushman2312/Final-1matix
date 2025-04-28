from .models import *
from django.views.generic import TemplateView
from django.views import View
from masteradmin.models import Tickets
from django.http import JsonResponse
from customersupport.models import SupportDepartment, SupportUser
from django.db.models import Count, Q
from .models import Feedbacks
import json
from django.shortcuts import redirect, render
from django.contrib.auth.hashers import make_password
from .models import User
from django.contrib import messages
import re
import logging
from django.utils import timezone
from allauth.socialaccount.models import SocialApp, SocialAccount
from django.conf import settings
from django.contrib.auth.models import User as AuthUser
from .google_auth import get_google_auth_url, handle_google_callback

logger = logging.getLogger(__name__)

# Create your views here.
def get_user_id(request):
    user = request.session.get('user_id')
    return user

class SignupView(TemplateView):
    template_name = 'user_dashboard/signup.html'
    mobile_template_name = 'user_dashboard/mobile-signup.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
    def get_template_names(self):
        # Check if request is from mobile device
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        if any(device in user_agent.lower() for device in ['mobile', 'android', 'iphone', 'ipad', 'ipod']):
            return [self.mobile_template_name]
        return [self.template_name]
    
    def post(self, request, *args, **kwargs):
        try:
            # Get form data
            full_name = request.POST.get('full_name')
            email = request.POST.get('email')  # Changed from username to email
            password = request.POST.get('password')
            mobile_number = request.POST.get('mobile_number')
            
            # Determine which template to use based on device
            template_to_use = self.get_template_names()[0]
            
            # For debugging
            print(f"Received form data: name={full_name}, email={email}, mobile={mobile_number}, pwd_length={len(password) if password else 0}")
            
            # Basic validation
            if not all([full_name, email, password, mobile_number]):
                messages.error(request, 'Please fill all required fields')
                return render(request, template_to_use)
            
            # Validate mobile number (assuming Indian format without +91)
            if not mobile_number.isdigit() or len(mobile_number) != 10:
                messages.error(request, 'Please enter a valid 10-digit mobile number')
                return render(request, template_to_use)
            
            # Check if username already exists in email field
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists')
                return render(request, template_to_use)
            
            # Check if mobile already exists
            if User.objects.filter(phone=mobile_number).exists():
                messages.error(request, 'Mobile number already registered')
                return render(request, template_to_use)
            
            # Create user
            user = User(
                name=full_name,
                email=email,
                phone=mobile_number,
                password=make_password(password),
                created_at=timezone.now()
            )
            
            # Set password if the model has a password field
            if hasattr(User, 'password'):
                user.password = make_password(password)
            
            user.save()
            print(f"User created with ID: {user.user_id}")
            
            # Redirect to login page or dashboard
            messages.success(request, 'Registration successful! Please log in.')
            return redirect('/user/login/')
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error creating user: {str(e)}")
            messages.error(request, f'Error during registration: {str(e)}')
            return render(request, template_to_use, {'form_data': request.POST})

            
class DashboardView(TemplateView):
    template_name = 'user_dashboard/base.html'

    def dispatch(self, request, *args, **kwargs):
        # Check both custom authentication and Django authentication
        is_authenticated = (
            request.session.get('user_id') is not None or  # Custom auth
            (request.session.get('_auth_user_id') is not None)  # Django auth
        )
        
        if not is_authenticated:
            messages.warning(request, 'Please log in to access the dashboard')
            return redirect('/user/login/')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add user data to context
        user_id = self.request.session.get('user_id')
        
        # Try to get user from custom auth or Django auth
        if user_id:
            try:
                user = User.objects.get(user_id=user_id)
                context['user'] = user
            except User.DoesNotExist:
                pass
        elif self.request.session.get('_auth_user_id'):
            # Try to get Django authenticated user
            from django.contrib.auth.models import User as AuthUser
            auth_user_id = self.request.session.get('_auth_user_id')
            try:
                auth_user = AuthUser.objects.get(id=auth_user_id)
                # Now get the corresponding custom User if it exists
                try:
                    user = User.objects.get(email=auth_user.email)
                    context['user'] = user
                except User.DoesNotExist:
                    # Create a new User record linked to the AuthUser
                    user = User(
                        name=auth_user.get_full_name() or auth_user.username,
                        email=auth_user.email,
                        created_at=timezone.now()
                    )
                    user.save()
                    context['user'] = user
                    # Set our custom user_id in session for future requests
                    self.request.session['user_id'] = str(user.user_id)
            except AuthUser.DoesNotExist:
                pass
                
        return context

class CreateTicketView(View):
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.info("Processing new support ticket request")
            
            # Get form data
            department = request.POST.get('department')
            mobile_number = request.POST.get('mobile_number')
            problem = request.POST.get('message')
            priority = request.POST.get('priority', 'Normal')
            email = request.user.email if request.user.is_authenticated else request.POST.get('email')
            attachment = request.FILES.get('attachment')

            logger.debug(f"Received ticket data - Department: {department}, Priority: {priority}, Has Attachment: {bool(attachment)}, Mobile Number: {mobile_number}, Email: {email}, Problem: {problem}")

            # Validate required fields
            if not all([department, problem, mobile_number]):
                logger.warning("Missing required fields in ticket submission")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please fill all required fields'
                }, status=400)

            # Get the support department
            try:
                support_dept = SupportDepartment.objects.get(name=department)
            except SupportDepartment.DoesNotExist:
                logger.error(f"Invalid department selected: {department}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid department selected'
                }, status=400)

            # Get available support users in the department
            support_users = SupportUser.objects.filter(
                support_department=support_dept,
                is_active=True,
                is_approved=True,
                is_rejected=False,
                is_suspended=False
            )

            if not support_users.exists():
                logger.error(f"No active support users found in department: {department}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'No support users available in {department} department'
                }, status=400)

            # Get the support user with the least number of pending tickets
            assigned_user = support_users.annotate(
                pending_tickets=Count(
                    'tickets',
                    filter=Q(tickets__status='Pending')
                )
            ).order_by('pending_tickets').first()

            logger.info(f"Assigning ticket to support user: {assigned_user.name}")

            # Create the ticket
            ticket = Tickets.objects.create(
                mobile_number=mobile_number,
                email=email,
                problem=problem,
                department=department,
                status='Pending',
                assigned_to=assigned_user
            )

            # Handle attachment if present
            if attachment:
                logger.debug(f"Processing attachment for ticket {ticket.id}")
                ticket.attachment = attachment
                ticket.save()

            logger.info(f"Successfully created ticket {ticket.id}")
            return JsonResponse({
                'status': 'success',
                'message': 'Support ticket created successfully!',
                'ticket_id': str(ticket.id),
                'assigned_to': assigned_user.name
            })

        except Exception as e:
            logger.exception("Error creating support ticket")
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

class HelpAndSupportView(TemplateView):
    template_name = 'user_dashboard/help_and_support.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['articles'] = UserArticle.objects.all()
        context['support_departments'] = SupportDepartment.objects.all()
        return context

class FeedbackView(View):
    def post(self, request):
        try:
            # Parse JSON data from request body
            data = json.loads(request.body)
            
            # Extract data from request
            rating = data.get('rating')
            message = data.get('message')
            name = data.get('name')
            
            # Validate required fields
            if not all([rating, message, name]):
                return JsonResponse({
                    'status': 'error',
                    'message': 'All fields are required'
                }, status=400)
            
            # Convert rating to integer
            try:
                rating = int(rating)
                if rating not in range(1, 6):
                    raise ValueError
            except ValueError:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid rating value'
                }, status=400)
            
            # Create feedback
            feedback = Feedbacks.objects.create(
                rating=rating,
                message=message,
                name=name
            )
            
            return JsonResponse({
                'status': 'success',
                'message': 'Thank you for your feedback!',
                'feedback_id': feedback.id
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

class CheckUsernameView(View):
    def get(self, request):
        email = request.GET.get('username', '')  # Keep 'username' for compatibility
        is_available = not User.objects.filter(email=email).exists()
        return JsonResponse({'available': is_available})

class GoogleLoginView(View):
    def get(self, request):
        """Redirect to Google OAuth"""
        auth_url = get_google_auth_url(request)
        return redirect(auth_url)

def google_callback(request):
    """Handle the Google OAuth callback"""
    user, error = handle_google_callback(request)
    
    if error:
        messages.error(request, f"Google sign-in failed: {error}")
        return redirect('signup')
    
    if user:
        # Set session variables
        request.session['user_id'] = str(user.user_id)
        request.session['user_email'] = user.email
        request.session['user_name'] = user.name
        
        messages.success(request, f"Welcome, {user.name}!")
        return redirect('/user/dashboard/')
    
    messages.error(request, "Failed to authenticate with Google")
    return redirect('signup')

class LoginView(TemplateView):
    template_name = 'user_dashboard/login.html'
    mobile_template_name = 'user_dashboard/mobile-login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
    def get_template_names(self):
        # Check if request is from mobile device
        user_agent = self.request.META.get('HTTP_USER_AGENT', '')
        if any(device in user_agent.lower() for device in ['mobile', 'android', 'iphone', 'ipad', 'ipod']):
            return [self.mobile_template_name]
        return [self.template_name]
    
    def post(self, request, *args, **kwargs):
        try:
            # Get form data
            email = request.POST.get('email', '')
            password = request.POST.get('password', '')
            remember_me = request.POST.get('remember_me') == 'on'
            
            # Determine which template to use based on device
            template_to_use = self.get_template_names()[0]
            
            # Basic validation
            if not email or not password:
                messages.error(request, 'Please fill all required fields')
                return render(request, template_to_use)
            
            # Check if user exists
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                messages.error(request, 'Invalid email or password')
                return render(request, template_to_use)
            
            # Check password
            from django.contrib.auth.hashers import check_password
            if not hasattr(user, 'password') or not check_password(password, user.password):
                messages.error(request, 'Invalid email or password')
                return render(request, template_to_use)
            
            # Login successful
            # Set session variables
            request.session['user_id'] = str(user.user_id)
            request.session['user_email'] = user.email
            request.session['user_name'] = user.name
            
            # Debug print - you can remove this after debugging
            print(f"User login successful: {user.name} (ID: {user.user_id})")
            
            # Set session expiry if remember_me is checked
            if not remember_me:
                request.session.set_expiry(0)  # Session expires when browser closes
            
            messages.success(request, f'Welcome back, {user.name}!')
            return redirect('/user/dashboard/')
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"Error during login: {str(e)}")
            messages.error(request, f'Error during login: {str(e)}')
            return render(request, self.get_template_names()[0])
class DebugSessionView(View):
    def get(self, request):
        """Debug view to check session values"""
        session_data = {
            'is_authenticated': request.session.get('user_id') is not None,
            'user_id': request.session.get('user_id'),
            'user_email': request.session.get('user_email'),
            'user_name': request.session.get('user_name'),
            'session_keys': list(request.session.keys()),
        }
        return JsonResponse(session_data)


def Logout(request):
    if 'user_id' in request.session:
        del request.session['user_id']
    request.session.flush()
    messages.success(request, 'You have been logged out successfully.')
    return redirect('/user/login/')




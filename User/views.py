import re
import json
import logging
import datetime
import requests
from django.contrib.auth.hashers import make_password
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from django.contrib.auth.models import User as AuthUser
from allauth.socialaccount.models import SocialApp, SocialAccount
from masteradmin.models import Tickets
from customersupport.models import SupportDepartment, SupportUser
from django.db.models import Count, Q
from django.contrib import messages
from .google_auth import get_google_auth_url, handle_google_callback
from .models import User, Reminder, Feedbacks, UserArticle, UserPolicy, QuickNote
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

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
        
        # Check if user is coming from Google authentication
        if 'google_auth_email' in self.request.session:
            context['google_auth_email'] = self.request.session.get('google_auth_email')
            context['google_auth_name'] = self.request.session.get('google_auth_name')
            context['google_auth_user_id'] = self.request.session.get('google_auth_user_id')
            context['is_google_auth'] = True
            
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
            
            # Check if this is a Google signup completion
            is_google_auth = 'google_auth_email' in request.session
            
            # Determine which template to use based on device
            template_to_use = self.get_template_names()[0]
            
            # For debugging
            print(f"Received form data: name={full_name}, email={email}, mobile={mobile_number}, pwd_length={len(password) if password else 0}")
            
            # Basic validation
            if not all([full_name, email, mobile_number]):
                messages.error(request, 'Please fill all required fields')
                return render(request, template_to_use, self.get_context_data())
            
            # Password is not required for Google auth
            if not is_google_auth and not password:
                messages.error(request, 'Password is required')
                return render(request, template_to_use, self.get_context_data())
            
            # Validate mobile number (assuming Indian format without +91)
            if not mobile_number.isdigit() or len(mobile_number) != 10:
                messages.error(request, 'Please enter a valid 10-digit mobile number')
                return render(request, template_to_use, self.get_context_data())
            
            # Check if username already exists in email field
            if User.objects.filter(email=email).exists():
                messages.error(request, 'Email already exists')
                return render(request, template_to_use, self.get_context_data())
            
            # Check if mobile already exists
            if User.objects.filter(phone=mobile_number).exists():
                messages.error(request, 'Mobile number already registered')
                return render(request, template_to_use, self.get_context_data())
            
            # Create user
            user = User(
                name=full_name,
                email=email,
                phone=mobile_number,
                created_at=timezone.now()
            )
            
            # Set password if not Google auth
            if not is_google_auth:
                user.password = make_password(password)
            
            user.save()
            print(f"User created with ID: {user.user_id}")
            
            # If this is Google auth completion, set session variables for login
            if is_google_auth:
                request.session['user_id'] = str(user.user_id)
                request.session['user_email'] = user.email
                request.session['user_name'] = user.name
                
                # Clear Google auth session data
                request.session.pop('google_auth_email', None)
                request.session.pop('google_auth_name', None)
                request.session.pop('google_auth_user_id', None)
                
                messages.success(request, 'Registration completed successfully!')
                return redirect('/user/dashboard/')
            
            # Regular signup - redirect to login page
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
        is_authenticated = request.session.get('user_id') is not None  # Only use custom auth
        
        if not is_authenticated:
            messages.warning(request, 'Please log in to access the dashboard')
            return redirect('/user/login/')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add user data to context
        user_id = self.request.session.get('user_id')
        
        # Only get user from custom auth system
        if user_id:
            try:
                user = User.objects.get(user_id=user_id)
                context['user'] = user
            except User.DoesNotExist:
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
        # If already logged in as a custom user, redirect to dashboard
        if request.session.get('user_id'):
            return redirect('/user/dashboard/')
            
        auth_url = get_google_auth_url(request)
        return redirect(auth_url)

def google_callback(request):
    """Handle the Google OAuth callback"""
    # If already logged in as a custom user, redirect to dashboard
    if request.session.get('user_id'):
        return redirect('/user/dashboard/')
        
    user, error = handle_google_callback(request)
    
    if error:
        messages.error(request, f"Google sign-in failed: {error}")
        return redirect('signup')
    
    if user:
        # Check if this is a newly created user (without complete profile)
        is_new_user = not hasattr(user, 'phone') or not user.phone
        
        if is_new_user:
            # Store user data in session for the signup form
            request.session['google_auth_email'] = user.email
            request.session['google_auth_name'] = user.name
            request.session['google_auth_user_id'] = str(user.user_id)
            
            # Delete incomplete user to prevent duplicate records
            user.delete()
            
            messages.info(request, "Please complete your profile to continue")
            return redirect('signup')
        
        # Set session variables for existing users (ONLY in custom user system)
        request.session['user_id'] = str(user.user_id)
        request.session['user_email'] = user.email
        request.session['user_name'] = user.name
        
        # Check if there's a next URL to redirect to
        next_url = request.session.get('next_url')
        if next_url:
            del request.session['next_url']
            messages.success(request, f"Welcome, {user.name}!")
            return redirect(next_url)
        
        messages.success(request, f"Welcome, {user.name}!")
        return redirect('/user/dashboard/')
    
    messages.error(request, "Failed to authenticate with Google")
    return redirect('signup')

class LoginView(TemplateView):
    template_name = 'user_dashboard/login.html'
    mobile_template_name = 'user_dashboard/mobile-login.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add next parameter to context if available
        next_url = self.request.GET.get('next') or self.request.session.get('next_url')
        if next_url:
            # Store next URL in session
            self.request.session['next_url'] = next_url
            context['next_url'] = next_url
        return context
    
    def get(self, request, *args, **kwargs):
        # If user is already logged in, redirect to dashboard
        if request.session.get('user_id'):
            return redirect('/user/dashboard/')
        return super().get(request, *args, **kwargs)
    
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
            
            # Check if user exists in our custom User model (not Django auth)
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
            
            # Check if there's a next URL to redirect to
            next_url = request.session.get('next_url')
            if next_url:
                del request.session['next_url']
                messages.success(request, f'Welcome back, {user.name}!')
                return redirect(next_url)
            
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
        # Only show custom user session values, not Django admin session info
        session_data = {
            'custom_is_authenticated': request.session.get('user_id') is not None,
            'custom_user_id': request.session.get('user_id'),
            'custom_user_email': request.session.get('user_email'),
            'custom_user_name': request.session.get('user_name'),
            'custom_session_keys': [key for key in request.session.keys() 
                                   if key in ['user_id', 'user_email', 'user_name', 'next_url']],
        }
        return JsonResponse(session_data)


def Logout(request):
    # Only remove custom user session variables
    if 'user_id' in request.session:
        del request.session['user_id']
    if 'user_email' in request.session:
        del request.session['user_email']
    if 'user_name' in request.session:
        del request.session['user_name']
        
    # Don't call request.session.flush() as it would log out Django admin too
    
    messages.success(request, 'You have been logged out successfully.')
    return redirect('/user/login/')

@method_decorator(csrf_exempt, name='dispatch')
class CreateReminderView(View):
    def post(self, request):
        print("Create reminder API called")
        print(f"Session data: {request.session.get('user_id')}")
        
        if not request.session.get('user_id'):
            print("User not authenticated")
            return JsonResponse({'success': False, 'message': 'User not authenticated'}, status=401)
        
        try:
            data = json.loads(request.body)
            print(f"Received data: {data}")
            
            user_id = request.session.get('user_id')
            print(f"Looking up user with ID: {user_id}")
            
            # Try different ways to find the user
            user = None
            
            # Try by user_id UUID field first
            try:
                user = User.objects.get(user_id=user_id)
                print(f"Found user by user_id: {user.name}")
            except User.DoesNotExist:
                pass
                
            # If not found, try by id
            if not user:
                try:
                    user = User.objects.get(id=user_id)
                    print(f"Found user by id: {user.name}")
                except (User.DoesNotExist, ValueError):
                    pass
            
            # If still not found, try by id (numeric)
            if not user:
                try:
                    # Try to convert to int
                    numeric_id = int(user_id)
                    user = User.objects.get(id=numeric_id)
                    print(f"Found user by numeric id: {user.name}")
                except (User.DoesNotExist, ValueError):
                    pass
                    
            # If we still couldn't find the user, return an error
            if not user:
                print(f"User not found with any ID method: {user_id}")
                return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
            
            title = data.get('title')
            description = data.get('description', '')
            reminder_datetime_str = data.get('reminder_time')
            timezone_name = data.get('timezone_name', '')
            
            print(f"Processing reminder with timezone: {timezone_name}")
            
            if not title or not reminder_datetime_str:
                print("Missing required fields")
                return JsonResponse({
                    'success': False, 
                    'message': 'Title and reminder time are required'
                }, status=400)
            
            # Parse the datetime string - handle different ISO formats
            try:
                print(f"Processing reminder time string: '{reminder_datetime_str}'")
                
                # First try simple fromisoformat (works with most formats)
                try:
                    reminder_time = datetime.datetime.fromisoformat(reminder_datetime_str)
                    print(f"Successfully parsed with fromisoformat: {reminder_time}")
                except ValueError as e:
                    print(f"fromisoformat failed: {e}")
                    # If that fails, try stripping 'Z' and milliseconds
                    if reminder_datetime_str.endswith('Z'):
                        # Remove the 'Z' and parse
                        clean_dt_str = reminder_datetime_str.rstrip('Z')
                        # Also remove milliseconds if present
                        if '.' in clean_dt_str:
                            clean_dt_str = clean_dt_str.split('.')[0]
                        print(f"Cleaned string (removed Z/ms): '{clean_dt_str}'")
                        reminder_time = datetime.datetime.fromisoformat(clean_dt_str)
                        print(f"Parsed after cleaning Z and ms: {reminder_time}")
                    else:
                        # If no Z but has milliseconds
                        if '.' in reminder_datetime_str:
                            clean_dt_str = reminder_datetime_str.split('.')[0]
                            print(f"Cleaned string (removed ms): '{clean_dt_str}'")
                            reminder_time = datetime.datetime.fromisoformat(clean_dt_str)
                            print(f"Parsed after cleaning ms: {reminder_time}")
                        else:
                            # Last resort, use dateutil parser which is more flexible
                            from dateutil import parser
                            reminder_time = parser.parse(reminder_datetime_str)
                            print(f"Parsed with dateutil parser: {reminder_time}")
                
                # Apply timezone handling
                if reminder_time.tzinfo is None:
                    print("Time is naive (no timezone info)")
                    # If no timezone info provided, assume it's in user's local timezone
                    # and convert to Django's timezone (typically UTC)
                    reminder_time = timezone.make_aware(reminder_time, timezone.get_current_timezone())
                    print(f"Made timezone aware (assuming local time): {reminder_time}")
                else:
                    print(f"Time already has timezone info: {reminder_time.tzinfo}")
                    # Ensure it's in Django's timezone format
                    reminder_time = timezone.localtime(reminder_time, timezone=timezone.get_current_timezone())
                    print(f"Converted to Django timezone: {reminder_time}")
                    
                # Store the original user timezone for later use when displaying
                user_timezone = None
                if "+" in reminder_datetime_str or "-" in reminder_datetime_str:
                    # Try to extract timezone offset from the string
                    try:
                        last_plus = reminder_datetime_str.rfind('+')
                        last_minus = reminder_datetime_str.rfind('-')
                        # Get the index of the last +/- that isn't at the start
                        if last_plus > 0 and (last_minus <= 0 or last_plus > last_minus):
                            user_timezone = reminder_datetime_str[last_plus:]
                        elif last_minus > 0:
                            user_timezone = reminder_datetime_str[last_minus:]
                        print(f"Extracted user timezone: {user_timezone}")
                    except Exception as e:
                        print(f"Error extracting timezone: {e}")
                        
            except Exception as e:
                print(f"Error parsing datetime: {e}")
                return JsonResponse({
                    'success': False,
                    'message': f'Invalid date format: {str(e)}'
                }, status=400)
                
            print(f"Final reminder time to save: {reminder_time}")
            
            # Create the reminder
            reminder = Reminder.objects.create(
                user=user,
                title=title,
                description=description,
                reminder_time=reminder_time,
                timezone_name=timezone_name  # Save the timezone name
            )
            
            print(f"Reminder created with ID: {reminder.id}")
            return JsonResponse({
                'success': True,
                'message': 'Reminder created successfully',
                'reminder': {
                    'id': str(reminder.id),
                    'title': reminder.title,
                    'description': reminder.description,
                    'reminder_time': reminder.reminder_time.isoformat(),
                    'status': reminder.status
                }
            })
            
        except User.DoesNotExist:
            print("User not found exception")
            return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
        except json.JSONDecodeError:
            print("Invalid JSON")
            return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"Error creating reminder: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class ListRemindersView(View):
    def get(self, request):
        if not request.session.get('user_id'):
            return JsonResponse({'success': False, 'message': 'User not authenticated'}, status=401)
        
        try:
            user_id = request.session.get('user_id')
            
            # Try different ways to find the user
            user = None
            
            # Try by user_id UUID field first
            try:
                user = User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                pass
                
            # If not found, try by id
            if not user:
                try:
                    user = User.objects.get(id=user_id)
                except (User.DoesNotExist, ValueError):
                    pass
            
            # If still not found, try by id (numeric)
            if not user:
                try:
                    # Try to convert to int
                    numeric_id = int(user_id)
                    user = User.objects.get(id=numeric_id)
                except (User.DoesNotExist, ValueError):
                    pass
                    
            # If we still couldn't find the user, return an error
            if not user:
                return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
            
            reminders = Reminder.objects.filter(user=user).order_by('reminder_time')
            
            reminders_list = []
            for reminder in reminders:
                reminders_list.append({
                    'id': str(reminder.id),
                    'title': reminder.title,
                    'description': reminder.description,
                    'reminder_time': reminder.reminder_time.isoformat(),
                    'status': reminder.status,
                    'is_due': reminder.is_due(),
                    'created_at': reminder.created_at.isoformat()
                })
            
            return JsonResponse({
                'success': True,
                'reminders': reminders_list
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CheckDueRemindersView(View):
    def get(self, request):
        if not request.session.get('user_id'):
            return JsonResponse({'success': False, 'message': 'User not authenticated'}, status=401)
        
        try:
            user_id = request.session.get('user_id')
            
            # Try different ways to find the user
            user = None
            
            # Try by user_id UUID field first
            try:
                user = User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                pass
                
            # If not found, try by id
            if not user:
                try:
                    user = User.objects.get(id=user_id)
                except (User.DoesNotExist, ValueError):
                    pass
            
            # If still not found, try by id (numeric)
            if not user:
                try:
                    # Try to convert to int
                    numeric_id = int(user_id)
                    user = User.objects.get(id=numeric_id)
                except (User.DoesNotExist, ValueError):
                    pass
                    
            # If we still couldn't find the user, return an error
            if not user:
                return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
            
            # Get current time
            now = timezone.now()
            
            # Find reminders that are due
            due_reminders = []
            
            # Check pending reminders that are due
            pending_reminders = Reminder.objects.filter(
                user=user,
                status='pending',
                reminder_time__lte=now
            )
            
            for reminder in pending_reminders:
                due_reminders.append({
                    'id': str(reminder.id),
                    'title': reminder.title,
                    'description': reminder.description,
                    'reminder_time': reminder.reminder_time.isoformat()
                })
                # Record that we sent a notification
                reminder.record_notification()
            
            # Check snoozed reminders that are now due
            snoozed_reminders = Reminder.objects.filter(
                user=user,
                status='snoozed',
                snoozed_until__lte=now
            )
            
            for reminder in snoozed_reminders:
                due_reminders.append({
                    'id': str(reminder.id),
                    'title': reminder.title,
                    'description': reminder.description,
                    'reminder_time': reminder.reminder_time.isoformat()
                })
                # Record that we sent a notification
                reminder.record_notification()
            
            # Check reminders that were notified more than 10 minutes ago but still active
            renotify_time = now - timezone.timedelta(minutes=10)
            renotify_reminders = Reminder.objects.filter(
                user=user,
                status__in=['pending', 'snoozed'],
                last_notification__lt=renotify_time,
                reminder_time__lte=now
            )
            
            for reminder in renotify_reminders:
                if reminder.id not in [r['id'] for r in due_reminders]:
                    due_reminders.append({
                        'id': str(reminder.id),
                        'title': reminder.title,
                        'description': reminder.description,
                        'reminder_time': reminder.reminder_time.isoformat()
                    })
                    # Record that we sent a notification
                    reminder.record_notification()
            
            return JsonResponse({
                'success': True,
                'due_reminders': due_reminders,
                'has_due_reminders': len(due_reminders) > 0
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class CompleteReminderView(View):
    def post(self, request, reminder_id):
        if not request.session.get('user_id'):
            return JsonResponse({'success': False, 'message': 'User not authenticated'}, status=401)
        
        try:
            user_id = request.session.get('user_id')
            
            # Try different ways to find the user
            user = None
            
            # Try by user_id UUID field first
            try:
                user = User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                pass
                
            # If not found, try by id
            if not user:
                try:
                    user = User.objects.get(id=user_id)
                except (User.DoesNotExist, ValueError):
                    pass
            
            # If still not found, try by id (numeric)
            if not user:
                try:
                    # Try to convert to int
                    numeric_id = int(user_id)
                    user = User.objects.get(id=numeric_id)
                except (User.DoesNotExist, ValueError):
                    pass
                    
            # If we still couldn't find the user, return an error
            if not user:
                return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
            
            reminder = Reminder.objects.get(id=reminder_id, user=user)
            reminder.mark_as_completed()
            
            return JsonResponse({
                'success': True,
                'message': 'Reminder marked as completed'
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
        except Reminder.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Reminder not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class SnoozeReminderView(View):
    def post(self, request, reminder_id):
        if not request.session.get('user_id'):
            return JsonResponse({'success': False, 'message': 'User not authenticated'}, status=401)
        
        try:
            data = json.loads(request.body)
            user_id = request.session.get('user_id')
            
            # Get snooze time in minutes (default to 10 minutes)
            snooze_minutes = data.get('snooze_minutes', 10)
            
            # Or get specific snooze datetime if provided
            snooze_datetime_str = data.get('snooze_datetime')
            
            # Get timezone name if provided
            timezone_name = data.get('timezone_name', '')
            print(f"Processing snooze with timezone: {timezone_name}")
            
            # Try different ways to find the user
            user = None
            
            # Try by user_id UUID field first
            try:
                user = User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                pass
                
            # If not found, try by id
            if not user:
                try:
                    user = User.objects.get(id=user_id)
                except (User.DoesNotExist, ValueError):
                    pass
            
            # If still not found, try by id (numeric)
            if not user:
                try:
                    # Try to convert to int
                    numeric_id = int(user_id)
                    user = User.objects.get(id=numeric_id)
                except (User.DoesNotExist, ValueError):
                    pass
                    
            # If we still couldn't find the user, return an error
            if not user:
                return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
            
            reminder = Reminder.objects.get(id=reminder_id, user=user)
            
            if snooze_datetime_str:
                # Parse the datetime string - handle different ISO formats
                try:
                    print(f"Processing snooze time string: '{snooze_datetime_str}'")
                    
                    # First try simple fromisoformat (works with most formats)
                    try:
                        snooze_datetime = datetime.datetime.fromisoformat(snooze_datetime_str)
                        print(f"Successfully parsed with fromisoformat: {snooze_datetime}")
                    except ValueError as e:
                        print(f"fromisoformat failed: {e}")
                        # If that fails, try stripping 'Z' and milliseconds
                        if snooze_datetime_str.endswith('Z'):
                            # Remove the 'Z' and parse
                            clean_dt_str = snooze_datetime_str.rstrip('Z')
                            # Also remove milliseconds if present
                            if '.' in clean_dt_str:
                                clean_dt_str = clean_dt_str.split('.')[0]
                            print(f"Cleaned string (removed Z/ms): '{clean_dt_str}'")
                            snooze_datetime = datetime.datetime.fromisoformat(clean_dt_str)
                            print(f"Parsed after cleaning Z and ms: {snooze_datetime}")
                        else:
                            # If no Z but has milliseconds
                            if '.' in snooze_datetime_str:
                                clean_dt_str = snooze_datetime_str.split('.')[0]
                                print(f"Cleaned string (removed ms): '{clean_dt_str}'")
                                snooze_datetime = datetime.datetime.fromisoformat(clean_dt_str)
                                print(f"Parsed after cleaning ms: {snooze_datetime}")
                            else:
                                # Last resort, use dateutil parser which is more flexible
                                from dateutil import parser
                                snooze_datetime = parser.parse(snooze_datetime_str)
                                print(f"Parsed with dateutil parser: {snooze_datetime}")
                    
                    # Apply timezone handling
                    if snooze_datetime.tzinfo is None:
                        print("Time is naive (no timezone info)")
                        # If no timezone info provided, assume it's in user's local timezone
                        # and convert to Django's timezone (typically UTC)
                        snooze_datetime = timezone.make_aware(snooze_datetime, timezone.get_current_timezone())
                        print(f"Made timezone aware (assuming local time): {snooze_datetime}")
                    else:
                        print(f"Time already has timezone info: {snooze_datetime.tzinfo}")
                        # Ensure it's in Django's timezone format
                        snooze_datetime = timezone.localtime(snooze_datetime, timezone=timezone.get_current_timezone())
                        print(f"Converted to Django timezone: {snooze_datetime}")
                    
                    print(f"Final snooze time to save: {snooze_datetime}")
                    
                    reminder.status = 'snoozed'
                    reminder.snoozed_until = snooze_datetime
                    
                    # Save timezone information if provided
                    if timezone_name:
                        reminder.timezone_name = timezone_name
                        
                    reminder.save()
                except Exception as e:
                    print(f"Error parsing datetime: {e}")
                    return JsonResponse({
                        'success': False,
                        'message': f'Invalid date format: {str(e)}'
                    }, status=400)
            else:
                # Use the minutes-based snooze
                reminder.snooze(minutes=snooze_minutes)
            
            return JsonResponse({
                'success': True,
                'message': 'Reminder snoozed successfully',
                'snoozed_until': reminder.snoozed_until.isoformat()
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User not found'}, status=404)
        except Reminder.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Reminder not found'}, status=404)
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class CreateQuickNoteView(View):
    """
    API endpoint for creating quick notes
    """
    def post(self, request):
        try:
            data = json.loads(request.body)
            user_id = request.session.get('user_id')
            
            if not user_id:
                return JsonResponse({
                    'success': False,
                    'message': 'User not authenticated'
                }, status=401)
            
            # Get the user
            try:
                user = User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'User not found'
                }, status=404)
            
            title = data.get('title')
            description = data.get('description', '')
            pinned = data.get('pinned', False)
            
            if not title:
                return JsonResponse({
                    'success': False,
                    'message': 'Title is required'
                }, status=400)
            
            # Create the quick note
            note = QuickNote.objects.create(
                user=user,
                title=title,
                description=description,
                pinned=pinned
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Quick note created successfully',
                'note': {
                    'id': str(note.id),
                    'title': note.title,
                    'description': note.description,
                    'pinned': note.pinned,
                    'created_at': note.created_at.isoformat()
                }
            })
            
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'message': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ListQuickNotesView(View):
    """
    API endpoint for listing user quick notes
    """
    def get(self, request):
        try:
            user_id = request.session.get('user_id')
            
            if not user_id:
                return JsonResponse({
                    'success': False,
                    'message': 'User not authenticated'
                }, status=401)
            
            # Get the user
            try:
                user = User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'User not found'
                }, status=404)
            
            # Get all notes for the user
            notes = QuickNote.objects.filter(user=user)
            
            # Format the notes for the response
            notes_data = []
            for note in notes:
                notes_data.append({
                    'id': str(note.id),
                    'title': note.title,
                    'description': note.description,
                    'pinned': note.pinned,
                    'created_at': note.created_at.isoformat()
                })
            
            return JsonResponse({
                'success': True,
                'notes': notes_data
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ToggleQuickNotePinView(View):
    """
    API endpoint for toggling pin status of a quick note
    """
    def post(self, request, note_id):
        try:
            user_id = request.session.get('user_id')
            
            if not user_id:
                return JsonResponse({
                    'success': False,
                    'message': 'User not authenticated'
                }, status=401)
            
            # Get the user
            try:
                user = User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'User not found'
                }, status=404)
            
            # Get the note
            try:
                note = QuickNote.objects.get(id=note_id, user=user)
            except QuickNote.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Note not found'
                }, status=404)
            
            # Toggle the pin status
            note.pinned = not note.pinned
            note.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Note {"pinned" if note.pinned else "unpinned"} successfully',
                'is_pinned': note.pinned
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class DeleteQuickNoteView(View):
    """
    API endpoint for deleting a quick note
    """
    def post(self, request, note_id):
        try:
            user_id = request.session.get('user_id')
            
            if not user_id:
                return JsonResponse({
                    'success': False,
                    'message': 'User not authenticated'
                }, status=401)
            
            # Get the user
            try:
                user = User.objects.get(user_id=user_id)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'User not found'
                }, status=404)
            
            # Get the note
            try:
                note = QuickNote.objects.get(id=note_id, user=user)
            except QuickNote.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Note not found'
                }, status=404)
            
            # Delete the note
            note.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Note deleted successfully'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)





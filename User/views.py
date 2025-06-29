import re
import json
import logging
import datetime
from django.urls import reverse
import random
import string
from django.contrib.auth.hashers import make_password
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.conf import settings
from django.contrib.auth.models import User as AuthUser
from masteradmin.models import Tickets, UserAgreement
from customersupport.models import SupportDepartment, SupportUser
from django.db.models import Count, Q
from django.contrib import messages
from .google_auth import get_google_auth_url, handle_google_callback
from .models import *
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.mail import send_mail
from django.template.loader import render_to_string
import uuid

logger = logging.getLogger(__name__)

def is_valid_gstin(gstin):
    """
    Validates a GSTIN number.
    - Must be 15 characters long.
    - First 2 characters must be a valid state code (01-37).
    - Next 10 characters must be a valid PAN.
    - 13th character is the entity number for the same PAN holder in a state.
    - 14th character must be 'Z'.
    - 15th character is a checksum.
    """
    if not re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$', gstin):
        return False

    # Check state code
    state_code = int(gstin[0:2])
    if not (1 <= state_code <= 37):
        return False

    # Checksum validation (MOD-36)
    gstin_chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    total = 0
    for i, char in enumerate(gstin[:-1]):
        val = gstin_chars.find(char)
        weight = (i % 2) + 1
        if weight == 1:
            total += val
        else:
            res = val * 2
            total += (res // 36) + (res % 36)

    checksum_val = (36 - (total % 36)) % 36
    checksum_char = gstin_chars[checksum_val]

    return gstin[-1] == checksum_char

# Create your views here.
def get_user_id(request):
    user = request.session.get('user_id')
    return user

class SignupView(TemplateView):
    template_name = 'user_dashboard/signup.html'
    mobile_template_name = 'user_dashboard/mobile-signup.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get the active user agreement
        active_agreement = UserAgreement.objects.filter(is_active=True).first()
        context['user_agreement'] = active_agreement

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
            data = json.loads(request.body)
            full_name = data.get('full_name')
            email = data.get('email')
            password = data.get('password') # Can be null for Google Auth
            mobile_number = data.get('mobile_number')
            gst_number = data.get('gst_number')
            user_agreement_id = data.get('user_agreement_id')
            is_google_auth = 'google_auth_email' in request.session and request.session['google_auth_email'] == email

            # Basic validation
            if not all([full_name, email, mobile_number]):
                return JsonResponse({'status': 'error', 'message': 'Please fill all required fields'}, status=400)

            if not is_google_auth and not password:
                 return JsonResponse({'status': 'error', 'message': 'Password is required'}, status=400)

            if not re.match(r'^\d{10}$', mobile_number):
                return JsonResponse({'status': 'error', 'message': 'Please enter a valid 10-digit mobile number'}, status=400)

            if User.objects.filter(email=email).exists():
                return JsonResponse({'status': 'error', 'message': 'Email already exists'}, status=400)
            
            if User.objects.filter(phone=mobile_number).exists():
                return JsonResponse({'status': 'error', 'message': 'Mobile number already registered'}, status=400)

            if gst_number:
                if not is_valid_gstin(gst_number):
                    return JsonResponse({'status': 'error', 'message': 'Please enter a valid GST number'}, status=400)

            # Get user agreement if ID was provided
            user_agreement = None
            if user_agreement_id:
                try:
                    user_agreement = UserAgreement.objects.get(id=user_agreement_id)
                except UserAgreement.DoesNotExist:
                    # Fallback to active agreement if provided ID doesn't exist
                    user_agreement = UserAgreement.objects.filter(is_active=True).first()
            else:
                # Get active agreement if no ID was provided
                user_agreement = UserAgreement.objects.filter(is_active=True).first()

            # Generate OTP and store data in session
            otp = ''.join(random.choices(string.digits, k=6))
            request.session['signup_data'] = {
                'full_name': full_name,
                'email': email,
                'password': make_password(password) if password else None,
                'mobile_number': mobile_number,
                'gst_number': gst_number,
                'otp': otp,
                'otp_expires_at': (timezone.now() + datetime.timedelta(minutes=10)).isoformat(),
                'is_google_auth': is_google_auth,
                'user_agreement_id': str(user_agreement.id) if user_agreement else None,
            }
            request.session.save()

            # Send OTP email
            html_message = render_to_string('user_dashboard/email/signup_otp_email.html', {'otp': otp, 'user_name': full_name})
            send_mail(
                'Verify your 1Matrix Account',
                f'Hi {full_name},\n\nYour One-Time Password (OTP) for creating your 1Matrix account is: {otp}\n\nThis OTP is valid for 10 minutes.',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
                html_message=html_message
            )

            return JsonResponse({'status': 'success', 'message': 'OTP sent to your email.'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
        except Exception as e:
            logger.error(f"Error in SignupView: {e}")
            return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred.'}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class VerifySignupOTPView(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            otp_entered = data.get('otp')
            
            signup_data = request.session.get('signup_data')

            if not signup_data or 'otp' not in signup_data:
                return JsonResponse({'status': 'error', 'message': 'Session expired. Please try signing up again.'}, status=400)

            if timezone.now() > datetime.datetime.fromisoformat(signup_data['otp_expires_at']):
                return JsonResponse({'status': 'error', 'message': 'OTP has expired. Please request a new one.'}, status=400)

            if signup_data['otp'] != otp_entered:
                return JsonResponse({'status': 'error', 'message': 'Invalid OTP. Please try again.'}, status=400)

            # Create user
            user = User.objects.create(
                name=signup_data['full_name'],
                email=signup_data['email'],
                phone=signup_data['mobile_number'],
                password=signup_data['password'],
                gst_number=signup_data.get('gst_number'),
                created_at=timezone.now()
            )
            
            # Track user agreement acceptance if available
            user_agreement = None
            if signup_data.get('user_agreement_id'):
                try:
                    user_agreement = UserAgreement.objects.get(id=signup_data['user_agreement_id'])
                    
                    # Create agreement acceptance record
                    from User.models import UserAgreementAcceptance
                    agreement_acceptance = UserAgreementAcceptance.objects.create(
                        user=user,
                        agreement=user_agreement,
                        agreement_title=user_agreement.title,
                        agreement_content=user_agreement.content,
                        ip_address=get_client_ip(request)
                    )
                    
                    # Send email with agreement details
                    self.send_agreement_email(user, user_agreement)
                    
                except (UserAgreement.DoesNotExist, Exception) as e:
                    logger.error(f"Error saving user agreement acceptance: {e}")
                    
            is_google_auth = signup_data.get('is_google_auth', False)
            
            # Clean up session
            del request.session['signup_data']
            if is_google_auth:
                request.session.pop('google_auth_email', None)
                request.session.pop('google_auth_name', None)
                request.session.pop('google_auth_user_id', None)
            
            request.session.save()

            logger.info(f"User created with ID: {user.user_id}")

            if is_google_auth:
                messages.success(request, 'Registration completed successfully!')
                return JsonResponse({'status': 'success_redirect', 'message': 'Account created! Please log in.', 'redirect_url': reverse('login')})

            return JsonResponse({'status': 'success', 'message': 'Account created successfully! Please log in.'})

        except json.JSONDecodeError:
            return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)
        except Exception as e:
            logger.error(f"Error in VerifySignupOTPView: {e}")
            return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred.'}, status=500)
    
    def send_agreement_email(self, user, agreement):
        """Send email with the accepted agreement details"""
        try:
            subject = '1Matrix - Your Account Terms and Conditions'
            
            html_message = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <div style="background-color: #f8f8f8; padding: 20px; text-align: center;">
                    <img src="/media/masteradmin_web/1mlogo.png" alt="1Matrix" style="max-width: 150px;">
                </div>
                <div style="padding: 30px 20px; border: 1px solid #eee; background-color: white;">
                    <h2 style="color: #333; margin-bottom: 20px;">Welcome to 1Matrix!</h2>
                    <p>Hello {user.name},</p>
                    <p>Your account has been successfully created. Thank you for joining us!</p>
                    <p>As part of your registration, you accepted the following terms and conditions:</p>
                    
                    <div style="background-color: #f9f9f9; border-left: 4px solid #ccc; padding: 15px; margin: 20px 0;">
                        <h3 style="color: #444;">{agreement.title}</h3>
                        <div>{agreement.content}</div>
                    </div>
                    
                    <p>Please keep this email for your reference.</p>
                    <p>If you have any questions or concerns, please contact our support team.</p>
                </div>
                <div style="padding: 15px; text-align: center; font-size: 12px; color: #666;">
                    <p>&copy; {timezone.now().year} 1Matrix. All rights reserved.</p>
                </div>
            </div>
            """
            
            plain_message = f"""
            Welcome to 1Matrix!
            
            Hello {user.name},
            
            Your account has been successfully created. Thank you for joining us!
            
            As part of your registration, you accepted the following terms and conditions:
            
            {agreement.title}
            
            {agreement.content}
            
            Please keep this email for your reference.
            
            If you have any questions or concerns, please contact our support team.
            
            © {timezone.now().year} 1Matrix. All rights reserved.
            """
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
                html_message=html_message
            )
            
            logger.info(f"Agreement acceptance email sent to {user.email}")
        except Exception as e:
            logger.error(f"Error sending agreement email: {e}")


# Helper function to get client IP
def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@method_decorator(csrf_exempt, name='dispatch')
class ResendSignupOTPView(View):
    def post(self, request, *args, **kwargs):
        try:
            signup_data = request.session.get('signup_data')

            if not signup_data:
                return JsonResponse({'status': 'error', 'message': 'Session expired. Please try signing up again.'}, status=400)

            # Generate new OTP
            otp = ''.join(random.choices(string.digits, k=6))
            signup_data['otp'] = otp
            signup_data['otp_expires_at'] = (timezone.now() + datetime.timedelta(minutes=10)).isoformat()
            
            request.session['signup_data'] = signup_data
            request.session.save()

            # Send new OTP email
            html_message = render_to_string('user_dashboard/email/signup_otp_email.html', {'otp': otp, 'user_name': signup_data['full_name']})
            send_mail(
                'Your New 1Matrix Signup OTP',
                f"Hi {signup_data['full_name']},\n\nYour new OTP is: {otp}\n\nThis OTP is valid for 10 minutes.",
                settings.DEFAULT_FROM_EMAIL,
                [signup_data['email']],
                fail_silently=False,
                html_message=html_message
            )

            return JsonResponse({'status': 'success', 'message': 'A new OTP has been sent to your email.'})

        except Exception as e:
            logger.error(f"Error in ResendSignupOTPView: {e}")
            return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred.'}, status=500)

class DashboardView(TemplateView):
    template_name = 'user_dashboard/base.html'

    def dispatch(self, request, *args, **kwargs):
        # Check authentication using the UserSession
        session_id = request.session.get('user_session_id')
        if not session_id:
            messages.warning(request, 'Please log in to access the dashboard')
            return redirect('/user/login/')

        try:
            user_session = UserSession.objects.select_related('user').get(id=session_id)
            
            # Check if session is expired
            if user_session.expires_at < timezone.now():
                user_session.delete()
                request.session.flush()
                messages.warning(request, 'Your session has expired. Please log in again.')
                return redirect('/user/login/')
            
            # Check if user is active
            if not user_session.user.is_active:
                user_session.delete()
                request.session.flush()
                messages.error(request, 'Your account is inactive. Please contact support.')
                return redirect('/user/login/')

            # Attach user to request for easy access in the view
            request.user = user_session.user
            # Activate timezone for this user
            if request.user.timezone:
                timezone.activate(request.user.timezone)

        except UserSession.DoesNotExist:
            request.session.flush()
            messages.warning(request, 'Invalid session. Please log in again.')
            return redirect('/user/login/')

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # The user is already attached to the request in dispatch
        context['user'] = self.request.user
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
    # If already logged in, redirect to dashboard
    session_id = request.session.get('user_session_id')
    if session_id:
        try:
            if UserSession.objects.filter(id=session_id).exists():
                return redirect('/user/dashboard/')
        except Exception:
            pass # Continue with login if session is invalid
        
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
        
        # Existing user login: Invalidate old sessions and create a new one.
        request.session.flush() # Clears the old session data.
        UserSession.objects.filter(user=user).delete()

        # Create a new session record, default to "remember me" for 30 days for Google logins
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        
        request.session.set_expiry(30 * 24 * 60 * 60) # 30 days
        expires_at = timezone.now() + datetime.timedelta(days=30)

        user_session = UserSession.objects.create(
            user=user,
            session_key=session_key,
            ip_address=request.META.get('REMOTE_ADDR'),
            user_agent=request.META.get('HTTP_USER_AGENT'),
            is_remembered=True, # Assume "remember me" for Google login
            expires_at=expires_at
        )

        # Set session variable
        request.session['user_session_id'] = str(user_session.id)
        
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
        session_id = request.session.get('user_session_id')
        if session_id:
            try:
                if UserSession.objects.filter(id=session_id).exists():
                    return redirect('/user/dashboard/')
            except Exception:
                pass # Continue to login page if session is invalid
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
                LoginActivity.objects.create(
                    user=None,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                    status='Failed'
                )
                return render(request, template_to_use)
            
            # Check password
            from django.contrib.auth.hashers import check_password
            if not hasattr(user, 'password') or not check_password(password, user.password):
                messages.error(request, 'Invalid email or password')
                LoginActivity.objects.create(
                    user=user,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                    status='Failed'
                )
                return render(request, template_to_use)
            
            if user.is_first_login:
                # Store temporary auth for the T&C and OTP flow
                request.session['pre_auth_user_id'] = user.user_id.hex
                return JsonResponse({'status': 'redirect', 'url': reverse('accept_terms')})
            
            # Login successful: Invalidate old sessions and create a new one.
            request.session.flush()
            
            # Determine if "remember me" was checked
            if remember_me:
                request.session.set_expiry(30 * 24 * 60 * 60) # 30 days
            else:
                request.session.set_expiry(0) # Session expires when browser closes

            # Create a new session record
            if not request.session.session_key:
                request.session.create()
            session_key = request.session.session_key

            expires_at = timezone.now() + datetime.timedelta(days=30) if remember_me else timezone.now() + datetime.timedelta(seconds=settings.SESSION_COOKIE_AGE)

            user_session = UserSession.objects.create(
                user=user,
                session_key=session_key,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT'),
                is_remembered=remember_me,
                expires_at=expires_at
            )

            LoginActivity.objects.create(
                user=user,
                ip_address=request.META.get('REMOTE_ADDR'),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
                status='Success'
            )

            # Set session variables
            request.session['user_session_id'] = str(user_session.id)
            
            # Debug print - you can remove this after debugging
            print(f"User login successful: {user.name} (Session ID: {user_session.id})")
            
            # Check if there's a next URL to redirect to
            next_url = request.session.get('next_url')
            if next_url:
                del request.session['next_url']
                messages.success(request, f'Welcome back, {user.name}!')
                return redirect(next_url)
            
            messages.success(request, f'Welcome back, {user.name}!')
            return redirect('/user/dashboard/')
            
        except Exception as e:
            print(f"Error during login: {str(e)}")
            messages.error(request, f'Error during login: {str(e)}')
            return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred.'}, status=500)

class AcceptTermsView(TemplateView):
    template_name = 'user_dashboard/accept_terms.html'

    def get(self, request, *args, **kwargs):
        if 'pre_auth_user_id' not in request.session:
            return redirect('login')
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['user_agreement'] = UserAgreement.objects.filter(is_active=True).first()
        return context

@method_decorator(csrf_exempt, name='dispatch')
class HandleAcceptTermsView(View):
    def post(self, request, *args, **kwargs):
        if 'pre_auth_user_id' not in request.session:
            return redirect('login')
        
        user_id = request.session['pre_auth_user_id']
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            return redirect('login')

        # Generate OTP
        otp = ''.join(random.choices(string.digits, k=6))
        request.session['first_login_otp'] = otp
        request.session['first_login_otp_expires_at'] = (timezone.now() + timezone.timedelta(minutes=10)).isoformat()

        # Send OTP email
        try:
            send_mail(
                'Verify Your Login',
                f'Your One-Time Password (OTP) for completing your login is: {otp}',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            logger.error(f"Failed to send OTP to {user.email}: {e}")
            messages.error(request, "Failed to send OTP. Please try again.")
            return redirect('accept_terms')

        return redirect('verify_first_login_otp')

class VerifyFirstLoginOtpView(TemplateView):
    template_name = 'user_dashboard/verify_first_login_otp.html'

    def get(self, request, *args, **kwargs):
        if 'pre_auth_user_id' not in request.session or 'first_login_otp' not in request.session:
            return redirect('login')
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        otp_entered = request.POST.get('otp')
        
        if 'pre_auth_user_id' not in request.session or 'first_login_otp' not in request.session:
            messages.error(request, 'Session expired. Please log in again.')
            return redirect('login')

        if timezone.now() > datetime.datetime.fromisoformat(request.session['first_login_otp_expires_at']):
            messages.error(request, 'OTP has expired. Please try again.')
            return render(request, self.template_name)

        if request.session['first_login_otp'] != otp_entered:
            messages.error(request, 'Invalid OTP. Please try again.')
            return render(request, self.template_name)

        # OTP is correct, finalize login
        try:
            user = User.objects.get(user_id=request.session['pre_auth_user_id'])
            
            # Update user
            user.is_first_login = False
            user.save()

            # Save agreement acceptance
            agreement = UserAgreement.objects.filter(is_active=True).first()
            if agreement:
                UserAgreementAcceptance.objects.create(
                    user=user,
                    agreement=agreement,
                    agreement_title=agreement.title,
                    agreement_content=agreement.content,
                    ip_address=get_client_ip(request)
                )

            # Create final user session
            request.session.flush()
            expires_at = timezone.now() + timezone.timedelta(days=1) # 1 day session
            user_session = UserSession.objects.create(
                user=user,
                session_key=request.session.session_key,
                expires_at=expires_at,
            )
            request.session['user_session_key'] = user_session.session_key

            messages.success(request, 'Login successful!')
            return redirect('dashboard')

        except User.DoesNotExist:
            messages.error(request, 'User not found. Please log in again.')
            return redirect('login')
        except Exception as e:
            logger.error(f"Error during OTP verification: {e}")
            messages.error(request, 'An unexpected error occurred.')
            return redirect('login')

class ForgotPasswordRequestView(View):
    def get(self, request):
        return render(request, 'user_dashboard/forgot_password.html')

    def post(self, request):
        email = request.POST.get('email')
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            messages.error(request, 'User with this email does not exist.')
            return redirect('forgot_password')

        # Invalidate old tokens
        PasswordResetToken.objects.filter(user=user).delete()

        # Create new token
        token = PasswordResetToken.objects.create(
            user=user,
            expires_at=timezone.now() + datetime.timedelta(hours=1)
        )

        # Send email
        reset_link = request.build_absolute_uri(reverse('reset_password', kwargs={'token': token.token}))
        
        html_message = render_to_string('user_dashboard/email/password_reset_email.html', {
            'user': user,
            'reset_link': reset_link,
        })

        send_mail(
            'Password Reset Request for 1Matrix',
            f'Hi {user.name},\n\nPlease click the link to reset your password: {reset_link}\n\nThe link will expire in 1 hour.',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
            html_message=html_message
        )

        messages.success(request, 'A password reset link has been sent to your email.')
        return redirect('forgot_password')


class ResetPasswordView(View):
    def get(self, request, token):
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            if reset_token.is_expired():
                messages.error(request, 'The password reset link has expired.')
                return redirect('forgot_password')
            return render(request, 'user_dashboard/reset_password.html', {'token': token})
        except PasswordResetToken.DoesNotExist:
            messages.error(request, 'Invalid password reset link.')
            return redirect('forgot_password')

    def post(self, request, token):
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
            if reset_token.is_expired():
                messages.error(request, 'The password reset link has expired.')
                return redirect('forgot_password')

            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')

            if new_password != confirm_password:
                messages.error(request, 'Passwords do not match.')
                return render(request, 'user_dashboard/reset_password.html', {'token': token})
            
            # Generate OTP
            otp = ''.join(random.choices(string.digits, k=6))
            request.session['reset_password_otp'] = otp
            request.session['reset_password_user_id'] = reset_token.user.id
            request.session['reset_password_new_password'] = make_password(new_password)
            request.session['reset_password_token'] = str(token)

            # Send OTP email
            html_message = render_to_string('user_dashboard/email/password_reset_otp.html', {
                'user': reset_token.user,
                'otp': otp,
            })
            
            send_mail(
                'Your Password Reset OTP for 1Matrix',
                f'Hi {reset_token.user.name},\n\nYour OTP to finalize your password reset is: {otp}\n\nThis OTP will expire shortly.',
                settings.DEFAULT_FROM_EMAIL,
                [reset_token.user.email],
                fail_silently=False,
                html_message=html_message
            )

            messages.info(request, 'An OTP has been sent to your email for final verification.')
            return redirect('verify_otp')

        except PasswordResetToken.DoesNotExist:
            messages.error(request, 'Invalid password reset link.')
            return redirect('forgot_password')

class VerifyOtpView(View):
    def get(self, request):
        if 'reset_password_otp' not in request.session:
            messages.error(request, 'Invalid request. Please start the password reset process again.')
            return redirect('forgot_password')
        return render(request, 'user_dashboard/verify_otp.html')

    def post(self, request):
        if 'reset_password_otp' not in request.session:
            messages.error(request, 'Your session has expired. Please start the password reset process again.')
            return redirect('forgot_password')

        otp = request.POST.get('otp')
        if otp != request.session['reset_password_otp']:
            messages.error(request, 'Invalid OTP. Please try again.')
            return render(request, 'user_dashboard/verify_otp.html')

        user_id = request.session['reset_password_user_id']
        new_password = request.session['reset_password_new_password']
        token_str = request.session['reset_password_token']

        try:
            user = User.objects.get(id=user_id)
            user.password = new_password
            user.save()

            # Invalidate the token
            PasswordResetToken.objects.filter(token=token_str).delete()

            # Clear session data
            del request.session['reset_password_otp']
            del request.session['reset_password_user_id']
            del request.session['reset_password_new_password']
            del request.session['reset_password_token']

            messages.success(request, 'Your password has been reset successfully. Please log in.')
            return redirect('login')

        except User.DoesNotExist:
            messages.error(request, 'An error occurred. Please try again.')
            return redirect('forgot_password')

class DebugSessionView(View):
    def get(self, request):
        """Debug view to check session values"""
        session_id = request.session.get('user_session_id')
        user_session = None
        user = None
        if session_id:
            try:
                user_session = UserSession.objects.get(id=session_id)
                user = user_session.user
            except UserSession.DoesNotExist:
                pass

        # Only show custom user session values, not Django admin session info
        session_data = {
            'custom_is_authenticated': user is not None,
            'user_session_id': session_id,
            'session_key': request.session.session_key,
            'user_name': user.name if user else None,
            'user_email': user.email if user else None,
            'session_expires_at': user_session.expires_at.isoformat() if user_session else None,
            'is_remembered': user_session.is_remembered if user_session else None,
            'session_expiry_age': request.session.get_expiry_age(),
            'custom_session_keys': list(request.session.keys())
        }
        return JsonResponse(session_data)


def Logout(request):
    # Only remove custom user session variables
    session_id = request.session.get('user_session_id')
    if session_id:
        try:
            UserSession.objects.filter(id=session_id).delete()
        except Exception as e:
            logger.error(f"Error deleting session on logout: {e}")
    
    request.session.flush() # Clears all session data
        
    # Don't call request.session.flush() as it would log out Django admin too
    
    messages.success(request, 'You have been logged out successfully.')
    return redirect('/user/login/')

@method_decorator(csrf_exempt, name='dispatch')
class CreateReminderView(View):
    def post(self, request):
        print("Create reminder API called")
        session_id = request.session.get('user_session_id')
        print(f"Session data: {session_id}")
        
        if not session_id:
            print("User not authenticated")
            return JsonResponse({'success': False, 'message': 'User not authenticated'}, status=401)
        
        try:
            data = json.loads(request.body)
            print(f"Received data: {data}")
            
            try:
                user_session = UserSession.objects.get(id=session_id)
                user = user_session.user
                print(f"Found user by session: {user.name}")
            except UserSession.DoesNotExist:
                print(f"User session not found with ID: {session_id}")
                return JsonResponse({'success': False, 'message': 'User session not found'}, status=404)
            
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
        session_id = request.session.get('user_session_id')
        if not session_id:
            return JsonResponse({'success': False, 'message': 'User not authenticated'}, status=401)
        
        try:
            user_session = UserSession.objects.get(id=session_id)
            user = user_session.user
            
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
        session_id = request.session.get('user_session_id')
        if not session_id:
            return JsonResponse({'success': False, 'message': 'User not authenticated'}, status=401)
        
        try:
            user_session = UserSession.objects.get(id=session_id)
            user = user_session.user
            
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
        session_id = request.session.get('user_session_id')
        if not session_id:
            return JsonResponse({'success': False, 'message': 'User not authenticated'}, status=401)
        
        try:
            user_session = UserSession.objects.get(id=session_id)
            user = user_session.user
            
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
        session_id = request.session.get('user_session_id')
        if not session_id:
            return JsonResponse({'success': False, 'message': 'User not authenticated'}, status=401)
        
        try:
            data = json.loads(request.body)
            user_session = UserSession.objects.get(id=session_id)
            user = user_session.user
            
            # Get snooze time in minutes (default to 10 minutes)
            snooze_minutes = data.get('snooze_minutes', 10)
            
            # Or get specific snooze datetime if provided
            snooze_datetime_str = data.get('snooze_datetime')
            
            # Get timezone name if provided
            timezone_name = data.get('timezone_name', '')
            print(f"Processing snooze with timezone: {timezone_name}")
            
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
            session_id = request.session.get('user_session_id')
            
            if not session_id:
                return JsonResponse({
                    'success': False,
                    'message': 'User not authenticated'
                }, status=401)
            
            # Get the user
            try:
                user_session = UserSession.objects.get(id=session_id)
                user = user_session.user
            except UserSession.DoesNotExist:
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
            session_id = request.session.get('user_session_id')
            
            if not session_id:
                return JsonResponse({
                    'success': False,
                    'message': 'User not authenticated'
                }, status=401)
            
            # Get the user
            try:
                user_session = UserSession.objects.get(id=session_id)
                user = user_session.user
            except UserSession.DoesNotExist:
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
            session_id = request.session.get('user_session_id')
            
            if not session_id:
                return JsonResponse({
                    'success': False,
                    'message': 'User not authenticated'
                }, status=401)
            
            # Get the user
            try:
                user_session = UserSession.objects.get(id=session_id)
                user = user_session.user
            except UserSession.DoesNotExist:
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
            session_id = request.session.get('user_session_id')
            
            if not session_id:
                return JsonResponse({
                    'success': False,
                    'message': 'User not authenticated'
                }, status=401)
            
            # Get the user
            try:
                user_session = UserSession.objects.get(id=session_id)
                user = user_session.user
            except UserSession.DoesNotExist:
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

class ProfileSettingsView(View):
    def get(self, request):
        login_activities = LoginActivity.objects.filter(user=request.user).order_by('-timestamp')[:10]
        return render(request, 'user_dashboard/settings.html', {'login_activities': login_activities})

    def post(self, request):
        user = request.user
        user.name = request.POST.get('name', user.name)
        user.phone = request.POST.get('phone', user.phone)
        user.language = request.POST.get('language', user.language)
        
        if 'profile_picture' in request.FILES:
            user.profile_picture = request.FILES['profile_picture']
        
        user.save()
        messages.success(request, 'Your profile has been updated successfully.')
        return redirect('user_settings')

class ChangePasswordView(View):
    def post(self, request):
        user = request.user
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_new_password = request.POST.get('confirm_new_password')

        if not user.check_password(current_password):
            messages.error(request, 'Your current password does not match.')
            return redirect('user_settings')

        if new_password != confirm_new_password:
            messages.error(request, 'The new passwords do not match.')
            return redirect('user_settings')
            
        user.password = make_password(new_password)
        user.save()
        messages.success(request, 'Your password has been changed successfully.')
        return redirect('user_settings')


class NotificationSettingsView(View):
    def post(self, request):
        user = request.user
        user.email_notifications = 'email_notifications' in request.POST
        user.sms_notifications = 'sms_notifications' in request.POST
        user.in_app_notifications = 'in_app_notifications' in request.POST
        user.notification_frequency = request.POST.get('notification_frequency', 'instant')
        user.save()
        messages.success(request, 'Your notification settings have been updated.')
        return redirect('user_settings')

class VerifyProfilingOtpView(View):
    template_name = 'user_dashboard/verify_profiling_otp.html'

    def get(self, request):
        if 'profiling_user_id' not in request.session:
            messages.error(request, 'No active profiling session found. Please start the process again.')
            return redirect('plans_and_pricing')
        return render(request, self.template_name)

    def post(self, request):
        user_id = request.session.get('profiling_user_id')
        if not user_id:
            messages.error(request, 'Your session has expired. Please start again.')
            return redirect('plans_and_pricing')

        submitted_otp = request.POST.get('otp')
        session_otp = request.session.get('profiling_otp')
        otp_expiry_str = request.session.get('profiling_otp_expiry')

        if not all([submitted_otp, session_otp, otp_expiry_str]):
            return render(request, self.template_name, {'error': 'Invalid request. Please try again.'})

        otp_expiry = timezone.datetime.fromisoformat(otp_expiry_str)

        if timezone.now() > otp_expiry:
            # Clear session keys
            del request.session['profiling_otp']
            del request.session['profiling_otp_expiry']
            del request.session['profiling_user_id']
            return render(request, self.template_name, {'error': 'OTP has expired. Please request a new one.'})

        if submitted_otp == session_otp:
            # OTP is correct, mark as verified for the next step
            request.session['profile_verification_complete'] = True
            
            # OTP is used, clear it from session
            del request.session['profiling_otp']
            del request.session['profiling_otp_expiry']

            return redirect('complete_profile')
        else:
            return render(request, self.template_name, {'error': 'Invalid OTP. Please try again.'})


class CompleteProfileView(View):
    template_name = 'user_dashboard/complete_profile.html'
    
    def get(self, request):
        if not request.session.get('profile_verification_complete'):
            messages.error(request, 'Please verify your OTP before completing your profile.')
            return redirect('verify_profiling_otp')

        user_id = request.session.get('profiling_user_id')
        if not user_id:
            messages.error(request, 'Session expired. Please start the process again.')
            return redirect('plans_and_pricing')

        try:
            user = User.objects.get(user_id=user_id)
            if user.password:
                messages.info(request, 'You have already completed your profile setup. Please log in.')
                return redirect('login')
        except User.DoesNotExist:
            messages.error(request, 'User not found. Please contact support.')
            return redirect('plans_and_pricing')

        return render(request, self.template_name)

    def post(self, request):
        if not request.session.get('profile_verification_complete'):
            messages.error(request, 'Please verify your OTP before completing your profile.')
            return redirect('verify_profiling_otp')

        user_id = request.session.get('profiling_user_id')
        if not user_id:
            messages.error(request, 'Session expired. Please start the process again.')
            return redirect('plans_and_pricing')
            
        try:
            user = User.objects.get(user_id=user_id)
        except User.DoesNotExist:
            messages.error(request, 'User not found. Please contact support.')
            return redirect('plans_and_pricing')

        if user.password:
            messages.info(request, 'You have already completed your profile setup. Please log in.')
            return redirect('login')
            
        name = request.POST.get('name', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if not all([name, password, confirm_password]):
            return render(request, self.template_name, {'error': 'Please fill in all fields.', 'name': name})
        
        if password != confirm_password:
            return render(request, self.template_name, {'error': 'Passwords do not match.', 'name': name})

        user.name = name
        user.password = make_password(password)
        user.is_first_login = False
        user.save()

        # Clean up session
        del request.session['profile_verification_complete']
        del request.session['profiling_user_id']

        session = UserSession.objects.create(
            user=user,
            session_key=str(uuid.uuid4()),
            ip_address=get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', ''),
            expires_at=timezone.now() + timezone.timedelta(days=30)
        )
        request.session['user_session_id'] = session.id
        request.session['user_id'] = user.user_id

        messages.success(request, 'Your profile has been set up successfully. Welcome to 1Matrix!')
        return redirect('dashboard')





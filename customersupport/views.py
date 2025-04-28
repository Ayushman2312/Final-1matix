from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import json
import random
import logging
from .models import *
from django.contrib.auth.hashers import make_password
from django.contrib import messages
from django.shortcuts import redirect
from masteradmin.models import *

logger = logging.getLogger(__name__)


# Create your views here.

# def login_view(request):
#     if request.method == "POST":
#         email = request.POST.get('email')
#         password = request.POST.get('password')
#         try:
#             user = SupportUser.objects.get(email=email)  # Use objects.get instead of GetUserByEmail
#             check = check_password(password, user.password)
#             if check:
#                 request.session['email'] = email
#                 return redirect('dashboard')
#             else:
#                 messages.info(request, "Invalid Password or Username")
#                 return render(request, 'home.html', {'error': "Invalid Password or Username"})
#         except User.DoesNotExist:
#             messages.info(request, "Username does not exist")
#             return render(request, 'home.html', {'error': "Username does not exist"})
#     return render(request, 'dashboard.html')


class RegisterView(TemplateView):
    template_name = "customer_support/support_register.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            passcode = self.kwargs.get('passcode')
            support = SupportUser.objects.filter(support_user_passcode=passcode).first()
            if support:
                if support.name and support.phone_number and support.dob:
                    context['support_error'] = 'Support has already registered'
                else:
                    context['email'] = support.email
                    context['support_passcode'] = passcode
            else:
                context['error'] = 'Support not found'
        except Exception as e:
            context['error'] = str(e)
        return context

    def post(self, request, *args, **kwargs):
        try:
            passcode = self.kwargs.get('passcode')
            support = SupportUser.objects.filter(support_user_passcode=passcode).first()
            
            if not support:
                return JsonResponse({'error': 'Support not found'}, status=404)
            
            if support.name and support.phone_number and support.dob:
                return JsonResponse({'error': 'Support has already registered'}, status=400)

            # Update basic information
            support.name = request.POST.get('name')
            support.phone_number = request.POST.get('phone_number')
            support.dob = request.POST.get('dob')
            support.qualification = request.POST.get('qualification')
            support.address = request.POST.get('address')
            support.experience = request.POST.get('experience_type')
            support.pan_number = request.POST.get('pan_number')
            support.aadhar_number = request.POST.get('aadhar_number')
            support.gender = request.POST.get('gender')

            # Update bank details
            support.bank_account_holder_name = request.POST.get('bank_account_holder_name')
            support.bank_account_number = request.POST.get('bank_account_number')
            support.bank_name = request.POST.get('bank_name')
            support.branch_name = request.POST.get('branch_name')
            support.bank_ifsc_code = request.POST.get('bank_ifsc_code')

            # Handle file uploads
            file_fields = {
                'photo': 'photo',
                'qualification_file': 'qualification_file',
                'cancelled_cheque_file': 'cancelled_cheque_file',
                'offer_letter_file': 'offer_letter_file',
                'bank_statement_file': 'bank_statement_file',
                'increment_letter_file': 'increment_letter_file',
                'pay_slip_file': 'pay_slip_file',
                'experience_letter_file': 'experience_letter_file',
                'leave_letter_file': 'leave_letter_file',
                'addhar_card_file': 'addhar_card_file',
                'pan_card_file': 'pan_card_file'
            }

            for model_field, form_field in file_fields.items():
                if form_field in request.FILES:
                    setattr(support, model_field, request.FILES[form_field])

            # Set password if provided
            if request.POST.get('password'):
                support.password = make_password(request.POST.get('password'))

            # Save the agent
            support.save()

            # Handle corporate references
            for i in range(1, 3):
                if all(request.POST.get(f'corporate_ref{i}_{field}') for field in ['name', 'email', 'phone', 'address']):
                    SupportCoorporate.objects.create(
                        support_user=support,
                        name=request.POST.get(f'corporate_ref{i}_name'),
                        email=request.POST.get(f'corporate_ref{i}_email'),
                        phone_number=request.POST.get(f'corporate_ref{i}_phone'),
                        address=request.POST.get(f'corporate_ref{i}_address')
                    )

            # Handle family references
            for i in range(1, 3):
                if all(request.POST.get(f'family_ref{i}_{field}') for field in ['name', 'email', 'phone', 'address']):
                    SupportFamily.objects.create(
                        support_user=support,
                        name=request.POST.get(f'family_ref{i}_name'),
                        email=request.POST.get(f'family_ref{i}_email'),
                        phone_number=request.POST.get(f'family_ref{i}_phone'),
                        address=request.POST.get(f'family_ref{i}_address')
                    )

            return redirect('support_success', passcode=passcode)

        except Exception as e:
            logger.error(f"Error in registration: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error during registration: {str(e)}'
            }, status=500)

# class SupportLoginView(TemplateView):
#     template_name = "customer_support/customer_support_login.html"

#     @method_decorator(csrf_exempt)
#     def dispatch(self, request, *args, **kwargs):
#         return super().dispatch(request, *args, **kwargs)

#     @staticmethod
#     def send_otp(request):
#         try:
#             data = json.loads(request.body)
#             email = data.get('email')
            
#             if not email:
#                 return JsonResponse({'error': 'Email is required.'}, status=400)

#             try:
#                 user = SupportUser.objects.get(email=email, is_active=True, is_approved=True)
#             except SupportUser.DoesNotExist:
#                 return JsonResponse({'error': 'Account not found or not approved.'}, status=404)

#             # Generate OTP and store in session with timestamp
#             otp = str(random.randint(100000, 999999))
#             request.session['otp'] = {
#                 'code': otp,
#                 'email': email,
#                 'timestamp': timezone.now().timestamp(),
#                 'attempts': 0
#             }
#             print(request.session['otp'])
#             try:
#                 # Configure email settings
#                 send_mail(
#                     subject='Your OTP Code',
#                     message=f'Your OTP code is {otp}. Valid for 5 minutes.',
#                     from_email=settings.EMAIL_HOST_USER,
#                     recipient_list=[email],
#                     fail_silently=False,
#                     auth_user=settings.EMAIL_HOST_USER,
#                     auth_password=settings.EMAIL_HOST_PASSWORD,
#                     connection=None
#                 )
#                 logger.info(f"OTP email sent successfully to {email}")
#                 return JsonResponse({'status': 'success', 'message': 'OTP sent to your email.'})
#             except Exception as e:
#                 logger.error(f"Failed to send OTP email: {str(e)}")
#                 return JsonResponse({'error': 'Failed to send OTP email.'}, status=500)

#         except Exception as e:
#             logger.error(f"Error in send_otp: {str(e)}")
#             return JsonResponse({'error': 'Internal server error.'}, status=500)

#     @staticmethod
#     def verify_otp(request):
#         try:
#             data = json.loads(request.body)
#             entered_otp = data.get('otp')
            
#             if not entered_otp:
#                 return JsonResponse({'error': 'OTP is required.'}, status=400)

#             otp_data = request.session.get('otp')
#             if not otp_data:
#                 return JsonResponse({'error': 'No OTP found. Please request a new one.'}, status=400)

#             # Check if OTP is expired (5 minutes)
#             current_time = timezone.now().timestamp()
#             if current_time - otp_data['timestamp'] > 300:  # 5 minutes
#                 del request.session['otp']
#                 return JsonResponse({'error': 'OTP has expired. Please request a new one.'}, status=400)

#             # Check attempts
#             if otp_data['attempts'] >= 3:
#                 del request.session['otp']
#                 return JsonResponse({'error': 'Too many attempts. Please request a new OTP.'}, status=400)

#             # Increment attempts
#             otp_data['attempts'] += 1
#             request.session['otp'] = otp_data

#             if entered_otp == otp_data['code']:
#                 # Store email for login step
#                 request.session['verified_email'] = otp_data['email']
#                 del request.session['otp']
#                 return JsonResponse({'status': 'success', 'message': 'OTP verified successfully.'})
            
#             return JsonResponse({'error': 'Invalid OTP.'}, status=400)

#         except Exception as e:
#             logger.error(f"Error in verify_otp: {str(e)}")
#             return JsonResponse({'error': 'Internal server error.'}, status=500)

#     @staticmethod
#     def login(request):
#         try:
#             from django.contrib.auth.hashers import check_password
            
#             data = json.loads(request.body)
#             email = data.get('email')
#             password = data.get('password')
            
#             if not email or not password:
#                 return JsonResponse({'error': 'Email and password are required.'}, status=400)

#             # Verify email matches the OTP-verified email
#             verified_email = request.session.get('verified_email')
#             if not verified_email or verified_email != email:
#                 return JsonResponse({'error': 'Please verify your email with OTP first.'}, status=400)

#             # Get the user directly first to check if they exist and are approved
#             try:
#                 support = SupportUser.objects.get(email=email)
#                 if not support.is_active or not support.is_approved:
#                     return JsonResponse({'error': 'Account not approved or inactive.'}, status=403)
                
#                 # Check hashed password directly
#                 if check_password(password, support.password):
#                     # Set session variables for custom login
#                     request.session['support_id'] = str(support.id)
#                     request.session['support_email'] = support.email
#                     request.session['is_authenticated'] = True

#                     request.session.modified = True
                    
#                     # Clear OTP verification data
#                     request.session.pop('verified_email', None)
                    
#                     return JsonResponse({'status': 'success', 'redirect_url': '/customersupport/dashboard/'})
#                 else:
#                     return JsonResponse({'error': 'Invalid password.'}, status=403)

#             except SupportUser.DoesNotExist:
#                 return JsonResponse({'error': 'Account not found.'}, status=404)

#         except json.JSONDecodeError:
#             return JsonResponse({'error': 'Invalid JSON data.'}, status=400)
#         except Exception as e:
#             logger.error(f"Error in login: {str(e)}")
#             return JsonResponse({'error': 'Internal server error.'}, status=500)
    
def CustomerSupportLogin(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not email:
            messages.error(request, 'Please provide both email and password')
            return render(request, 'customer_support/customer_support_login.html')
            
        try:
            user = SupportUser.objects.get(email=email)
            password = check_password(password, user.password)
            if password:
                request.session['support_id'] = str(user.id)
                return redirect('customer_support_dashboard')
            else:
                messages.error(request, 'Invalid password')
        except SupportUser.DoesNotExist:
            messages.error(request, 'Invalid credentials')
            
    return render(request, 'customer_support/customer_support_login.html')

class CustomerSupportDashboard(TemplateView):
    template_name = "customer_support/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["support_notifications"] = SupportNotification.objects.filter(support_user=self.request.session.get('support_id'), is_read=False).count()
        return context
    
class MasterNotificationsSupport(TemplateView):
    template_name = "agents/master_notifications.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        support_user = self.request.session.get("support_id")
        if support_user:
            context['support_notifications'] = SupportNotification.objects.filter(
                support_user=support_user, is_read=False
            ).select_related('support_user')  # This optimizes the query
        else:
            context['support_notifications'] = SupportNotification.objects.none()
        return context

class Success(TemplateView):
    template_name = "customer_support/success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        passcode = self.kwargs.get('passcode')
        try:
            support = SupportUser.objects.get(support_user_passcode=passcode)
            context['email'] = support.email
            context['passcode'] = passcode
        except SupportUser.DoesNotExist:
            context['email'] = ''
            context['passcode'] = passcode
        return context
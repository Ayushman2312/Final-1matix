from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, DetailView
from invoicing.models import Recipent, Invoice
from .models import FAQCategory, FAQItem, ContactUs, Payment
from rest_framework import viewsets, permissions
from .serializers import FAQCategorySerializer, FAQItemSerializer
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from masteradmin.models import Subscription, AppSubscriptionLimit, UserAgreement
from app.models import Apps
import uuid
from django.contrib import messages
from cashfree_pg.api_client import Cashfree
from cashfree_pg.models.create_order_request import CreateOrderRequest
from cashfree_pg.models.customer_details import CustomerDetails
from cashfree_pg.models.order_meta import OrderMeta
import json
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.hashers import make_password
import string
import random
from User.models import User, PasswordResetToken
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import logging
from decimal import Decimal, InvalidOperation
# Create your views here.

# It is recommended to store your API keys in environment variables
# For the purpose of this example, we are hardcoding them.
# Please replace with your actual keys.
# Professionalizing: Read from Django settings
# These should be set in your settings.py file, for example:
# CASHFREE_APP_ID = "YOUR_APP_ID"
# CASHFREE_SECRET_KEY = "YOUR_SECRET_KEY"
# CASHFREE_ENVIRONMENT = "sandbox"  # or "production"

Cashfree.XClientId = getattr(settings, 'CASHFREE_APP_ID', "956605704b2e8d84efba1d2a1e506659")
Cashfree.XClientSecret = getattr(settings, 'CASHFREE_SECRET_KEY', "cfsk_ma_prod_9c4245f2a1d88ddd7e0062511746ed8c_dc5a9c17")
CASHFREE_ENVIRONMENT = getattr(settings, 'CASHFREE_ENVIRONMENT', 'PRODUCTION')
Cashfree.XEnvironment = Cashfree.SANDBOX if CASHFREE_ENVIRONMENT == 'sandbox' else Cashfree.PRODUCTION

def is_mobile(request):
    """Detect if the request is coming from a mobile device"""
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    mobile_keywords = ['mobile', 'android', 'iphone' , 'windows phone']
    return any(keyword in user_agent for keyword in mobile_keywords)

class HomeView(TemplateView):
    def get_template_names(self):
        if is_mobile(self.request):
            return ['onematrix/mobile.html']
        return ['onematrix/home.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class ContactUsView(TemplateView):
    def get_template_names(self):
        if is_mobile(self.request):
            return ['onematrix/mobile-contact.html']
        return ['onematrix/contact-us.html']
    
    def post(self, request, *args, **kwargs):
        try:
            # Get form data with validation
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip()
            phone = request.POST.get('phone', '').strip()
            message = request.POST.get('message', '').strip()

            # Basic validation
            if not all([name, email, phone, message]):
                messages.error(request, 'Please fill in all fields')
                return redirect('contact-us')

            # Create contact entry
            contact = ContactUs.objects.create(
                name=name,
                email=email, 
                phone=phone,
                message=message
            )

            messages.success(request, 'Thank you for contacting us! We will get back to you soon.')
            return redirect('contact-us')

        except Exception as e:
            messages.error(request, 'An error occurred. Please try again.')
            return redirect('contact-us')
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add FAQ categories and items to context
        context['faq_categories'] = FAQCategory.objects.filter(is_active=True).prefetch_related(
            'faq_items'
        )
        # Get default category to show first (assuming 'service' is the default)
        default_category = FAQCategory.objects.filter(
            is_active=True, 
            name__iexact='service'
        ).first()
        
        # If 'service' category doesn't exist, get the first active category
        if not default_category and context['faq_categories'].exists():
            default_category = context['faq_categories'].first()
            
        context['default_category'] = default_category
        return context

class AboutUsView(TemplateView):
    def get_template_names(self):
        if is_mobile(self.request):
            return ['onematrix/mobile-about.html']
        return ['onematrix/about-us.html']
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class PrivacyPolicyView(TemplateView):
    template_name = 'onematrix/privacy-policy.html'
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class TermsAndConditionsView(TemplateView):
    template_name = 'onematrix/terms-and-conditions.html'
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class CancellationView(TemplateView):
    template_name = 'onematrix/cancellation.html'
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class TestApi(TemplateView):
    template_name = 'test_api.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context



class InvoiceReportsView(TemplateView):
    template_name = 'onematrix/invoice-reports.html'
    
    def dispatch(self, request, *args, **kwargs):
        recipient_id = kwargs.get('recipient_id')
        session_recipient_id = request.session.get('recipent_id')
        
        # Check if user is authenticated and accessing their own reports
        if not session_recipient_id or session_recipient_id != recipient_id:
            return redirect('home')
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        recipient_id = kwargs.get('recipient_id')
        recipient = Recipent.objects.get(recipent_id=recipient_id)
        context['recipient'] = recipient
        # Get all invoices from companies the recipient has access to
        invoices = Invoice.objects.filter(company__in=recipient.companies.all())
        companies = recipient.companies.all()
        
        context['invoices'] = invoices
        context['companies'] = companies
        return context

# FAQ Views
class FAQListView(ListView):
    model = FAQCategory
    template_name = 'onematrix/faq_list.html'
    context_object_name = 'categories'
    
    def get_queryset(self):
        return FAQCategory.objects.filter(is_active=True).prefetch_related('faq_items')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Frequently Asked Questions'
        return context

class FAQCategoryDetailView(DetailView):
    model = FAQCategory
    template_name = 'onematrix/faq_category.html'
    context_object_name = 'category'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'FAQ - {self.object.name}'
        context['items'] = self.object.faq_items.filter(is_active=True).order_by('order')
        return context

# API ViewSets
class FAQCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FAQCategory.objects.filter(is_active=True)
    serializer_class = FAQCategorySerializer
    permission_classes = [permissions.AllowAny]

class FAQItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FAQItem.objects.filter(is_active=True)
    serializer_class = FAQItemSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get('category', None)
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset

# API view for contact form submissions
@method_decorator(csrf_exempt, name='dispatch')  # Only use during testing, remove for production
class ContactAPIView(View):
    def post(self, request, *args, **kwargs):
        try:
            # Set up logging
            logger = logging.getLogger(__name__)
            logger.info("Contact form submission received")
            
            # Log all request data for debugging
            logger.info(f"POST data: {dict(request.POST.items())}")
            logger.info(f"Content type: {request.content_type}")
            logger.info(f"Headers: {dict(request.headers)}")
            
            # Get form data
            name = request.POST.get('name', '').strip()
            email = request.POST.get('email', '').strip()
            mobile = request.POST.get('mobile', '').strip()
            message = request.POST.get('message', '').strip()
            
            logger.info(f"Form data - Name: {name}, Email: {email}, Mobile: {mobile}, Message length: {len(message)}")
            
            # Basic validation
            missing_fields = []
            if not name: missing_fields.append('name')
            if not email: missing_fields.append('email')
            if not mobile: missing_fields.append('mobile')
            if not message: missing_fields.append('message')
            
            if missing_fields:
                logger.warning(f"Missing fields: {', '.join(missing_fields)}")
                is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                
                if is_ajax:
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Please fill in all required fields: {", ".join(missing_fields)}'
                    }, status=400)
                else:
                    # Redirect back to form for normal form submission
                    return redirect('contact-us')
            
            # Save the contact form data
            logger.info("Creating ContactUs instance...")
            try:
                # Create and save in a single step for simplicity
                contact = ContactUs.objects.create(
                    name=name,
                    email=email,
                    phone=mobile,  # Store mobile as phone in the database
                    message=message
                )
                logger.info(f"Contact saved with ID: {contact.id}")
            except Exception as e:
                logger.error(f"Database error: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                
                is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
                if is_ajax:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Database error occurred. Please try again later.'
                    }, status=500)
                else:
                    # Redirect back to form for normal form submission
                    return redirect('contact-us')
            
            # Determine if this is an AJAX request
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            
            if is_ajax:
                # For AJAX requests, return JSON response
                return JsonResponse({
                    'status': 'success',
                    'message': 'Thank you for contacting us! We will get back to you soon.',
                    'data': {
                        'name': name,
                        'email': email,
                        'mobile': mobile
                    }
                })
            else:
                # For direct form submissions, redirect with success parameter
                return redirect('/contact-us/?success=true')
                
        except Exception as e:
            # Log the error
            logger = logging.getLogger(__name__)
            logger.error(f"Unexpected error: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            # Determine if this is an AJAX request
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            
            if is_ajax:
                # For AJAX requests, return error JSON
                return JsonResponse({
                    'status': 'error',
                    'message': 'An unexpected error occurred. Please try again later.'
                }, status=500)
            else:
                # For direct form submissions, redirect back to the form
                return redirect('contact-us')

class ShippingAndDeliveryView(TemplateView):
    template_name = 'onematrix/shipping_and_delivery.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

class PlansAndPricingView(TemplateView):
    template_name = 'onematrix/plans_and_pricing.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Set up logging
        logger = logging.getLogger(__name__)
        logger.info("Rendering Plans & Pricing page")
        
        # Get all active subscriptions and convert to list to ensure we can add attributes
        subscriptions = list(Subscription.objects.filter(is_active=True).order_by('price_monthly'))
        logger.info(f"Found {len(subscriptions)} active subscriptions")
        
        # Process subscription data for template
        for subscription in subscriptions:
            logger.info(f"Processing subscription: {subscription.name} (ID: {subscription.id})")
            
            # Get all apps for this subscription
            apps = subscription.features.all()
            logger.info(f"Subscription has {apps.count()} apps")
            
            # Create apps_data list as an attribute of the subscription object
            apps_data = []
            
            for app in apps:
                logger.info(f"Processing app: {app.name}")
                try:
                    # Get app limits
                    app_limit = AppSubscriptionLimit.objects.get(
                        subscription=subscription,
                        app=app
                    )
                    
                    # Create app data dictionary
                    app_info = {
                        'name': app.name,
                        'description': app.description,
                        'limit_type': app_limit.limit_type,
                        'credits': app_limit.credits,
                        'daily_limit': app_limit.daily_limit,
                        'price': app_limit.price
                    }
                    
                    apps_data.append(app_info)
                    logger.info(f"Added app with limits: {app.name}")
                except AppSubscriptionLimit.DoesNotExist:
                    # If no limit is specified, use default values
                    app_info = {
                        'name': app.name,
                        'description': app.description,
                        'limit_type': 'Unlimited',
                        'credits': None,
                        'daily_limit': None,
                        'price': 0
                    }
                    apps_data.append(app_info)
                    logger.info(f"Added app with default limits: {app.name}")
                except Exception as e:
                    logger.error(f"Error processing app {app.name}: {str(e)}")
            
            # Add the processed apps data to the subscription
            subscription.apps_data = apps_data
            logger.info(f"Added {len(apps_data)} app entries to subscription {subscription.name}")
        
        # Add dummy subscription if none exist (for testing/development)
        if not subscriptions:
            logger.warning("No subscriptions found, adding dummy data for UI testing")
            
            # Create a simple object that behaves like a subscription
            class DummySubscription:
                pass
            
            dummy = DummySubscription()
            dummy.id = "dummy-1"
            dummy.name = "Basic Plan"
            dummy.price_monthly = 999
            dummy.max_users = 5
            dummy.validity_days = 30
            dummy.discount = 10
            dummy.apps_data = [
                {'name': 'Website Builder', 'limit_type': 'Unlimited'},
                {'name': 'CRM', 'limit_type': 'Limited', 'credits': 100}
            ]
            dummy.features = []
            
            subscriptions = [dummy]
        
        context['subscriptions'] = subscriptions
        context['cashfree_environment'] = CASHFREE_ENVIRONMENT
        logger.info(f"Returning context with {len(context['subscriptions'])} subscriptions")
        
        return context

@csrf_exempt
def create_payment_session(request):
    logger = logging.getLogger(__name__)
    logger.info("Create payment session request received.")

    if request.method != 'POST':
        logger.warning("Invalid request method used for create_payment_session.")
        return JsonResponse({'error': 'Invalid request method.'}, status=405)

    try:
        plan_id = request.POST.get('plan')
        email = request.POST.get('email', '').strip().lower()
        phone = request.POST.get('phone', '').strip()
        disabled_apps_str = request.POST.get('disabled_apps', '')

        logger.info(f"Payment session details: plan_id={plan_id}, email={email}, phone={phone}")
        logger.info(f"Disabled apps string: {disabled_apps_str}")

        if not all([plan_id, email, phone]):
            logger.error("Missing required fields: plan, email, or phone.")
            return JsonResponse({'error': 'Missing required fields: plan, email, or phone.'}, status=400)

        try:
            logger.info(f"Fetching subscription with ID: {plan_id}")
            subscription = Subscription.objects.get(id=plan_id)
            logger.info(f"Found subscription: {subscription.name}")
        except Subscription.DoesNotExist:
            logger.error(f"Invalid subscription plan ID provided: {plan_id}")
            return JsonResponse({'error': 'Invalid plan selected.'}, status=400)

        # --- Enhanced User Creation/Updation Logic ---
        logger.info(f"Looking up user by email: {email}")
        user_by_email = User.objects.filter(email=email).first()
        logger.info(f"Looking up user by phone: {phone}")
        user_by_phone = User.objects.filter(phone=phone).first()

        if user_by_email:
            logger.info(f"Found user by email: {user_by_email.id}")
        if user_by_phone:
            logger.info(f"Found user by phone: {user_by_phone.id}")

        if user_by_email and user_by_phone and user_by_email.id != user_by_phone.id:
            error_msg = f"Ambiguous user: email {email} (user {user_by_email.id}) and phone {phone} (user {user_by_phone.id}) belong to different accounts."
            logger.error(error_msg)
            return JsonResponse({'error': 'This email and phone number are associated with different accounts. Please use a different combination or contact support.'}, status=400)

        user = user_by_email or user_by_phone
        
        if user:
            logger.info(f"Updating existing user: {user.email} (ID: {user.id})")
            user.email = email
            user.phone = phone
            user.save()
            logger.info(f"User updated successfully: {user.id}")
        else:
            logger.info(f"Creating new user with email: {email}")
            user = User.objects.create(
                email=email,
                phone=phone,
                is_active=False  # Activate after successful payment
            )
            logger.info(f"New user created with ID: {user.id}")
        # --- End User Logic ---

        try:
            logger.info(f"Converting subscription price to Decimal: {subscription.price_monthly}")
            order_amount = Decimal(subscription.price_monthly)
            logger.info(f"Order amount set to: {order_amount}")
        except (InvalidOperation, TypeError):
            logger.error(f"Invalid price for subscription ID {subscription.id}: {subscription.price_monthly}")
            return JsonResponse({'error': 'Invalid plan price. Please contact support.'}, status=400)
            
        order_currency = "INR"
        order_id = f"order_{uuid.uuid4().hex}"
        logger.info(f"Generated order ID: {order_id}")

        logger.info(f"Creating payment object for order_id: {order_id} with amount: {order_amount}")
        payment = Payment.objects.create(
            user=user,
            order_id=order_id,
            subscription_plan=subscription,
            amount=order_amount,
            currency=order_currency,
            status='PROCESSING',
            customer_email=email,
            customer_phone=phone,
        )
        logger.info(f"Payment object created with ID: {payment.id} and status 'PROCESSING'")

        if disabled_apps_str:
            logger.info(f"Processing disabled apps: {disabled_apps_str}")
            disabled_app_ids = disabled_apps_str.split(',')
            logger.info(f"Disabled app IDs: {disabled_app_ids}")
            apps_to_exclude = Apps.objects.filter(id__in=disabled_app_ids)
            payment.excluded_apps.set(apps_to_exclude)
            logger.info(f"Excluding apps for payment: {list(apps_to_exclude.values_list('id', flat=True))}")

        customer_id = f"cust_{user.user_id}"
        logger.info(f"Customer ID set to: {customer_id}")
        
        return_url = request.build_absolute_uri(f'/payment/success/?order_id={order_id}')
        logger.info(f"Return URL set to: {return_url}")
        
        logger.info("Creating OrderMeta and CustomerDetails objects")
        order_meta = OrderMeta(return_url=return_url)
        customer_details = CustomerDetails(customer_id=customer_id, customer_phone=phone, customer_email=email)

        logger.info("Creating Cashfree order request")
        create_order_request = CreateOrderRequest(
            order_id=order_id,
            order_amount=float(order_amount),
            order_currency=order_currency,
            customer_details=customer_details,
            order_meta=order_meta,
        )
        logger.info(f"Prepared Cashfree CreateOrderRequest: {create_order_request.to_dict()}")

        logger.info("Sending request to Cashfree API")
        api_response = Cashfree().PGCreateOrder("2023-08-01", create_order_request)
        
        logger.info("Successfully received response from Cashfree API.")
        payment_session_id = api_response.data.payment_session_id
        logger.info(f"Payment session ID: {payment_session_id}")
        
        logger.info("Returning payment session ID to client")
        return JsonResponse({'payment_session_id': payment_session_id})

    except Exception as e:
        logger.error(f"Fatal error in create_payment_session: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred. Our team has been notified.'}, status=500)
@csrf_exempt
def cashfree_webhook(request):
    if request.method == "POST":
        signature = request.headers.get('x-webhook-signature')
        timestamp = request.headers.get('x-webhook-timestamp')
        raw_body = request.body

        if not signature or not timestamp:
            return HttpResponse("Webhook signature or timestamp missing", status=400)

        try:
            Cashfree().PGVerifyWebhookSignature(signature, raw_body, timestamp)
            payload = json.loads(raw_body)
            
            order_data = payload.get('data', {}).get('order', {})
            order_id = order_data.get('order_id')
            order_status = order_data.get('order_status')

            if not order_id:
                return HttpResponse("Order ID missing in webhook", status=400)

            try:
                payment = Payment.objects.get(order_id=order_id)
            except Payment.DoesNotExist:
                # This order was not initiated by our system.
                return HttpResponse("Payment record not found", status=404)

            # Prevent reprocessing successful payments
            if payment.status == 'SUCCESS':
                return HttpResponse("Webhook already processed", status=200)

            payment.webhook_payload = payload
            
            if order_status == 'PAID':
                if not payment.user:
                    customer_details = payload.get('data', {}).get('customer_details', {})
                    customer_email = customer_details.get('customer_email')
                    user = User.objects.filter(email=customer_email).first()
                    if user:
                        payment.user = user
                
                payment.status = 'SUCCESS'
                payment.payment_id = payload.get('data', {}).get('payment', {}).get('cf_payment_id')
                
                user = payment.user
                if user:
                    user.is_active = True
                    user.subscription_plan = payment.subscription_plan
                    user.last_payment_date = timezone.now().date()
                    user.last_payment_amount = payment.amount
                    user.last_payment_status = 'SUCCESS'

                    # Transfer excluded apps from payment to user
                    if payment.excluded_apps.exists():
                        user.excluded_apps.set(payment.excluded_apps.all())

                    user.save()

            elif order_status in ['PAYMENT_FAILED', 'TERMINATED']:
                payment.status = 'FAILED'

            payment.save()

        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Error processing webhook: {e}", exc_info=True)
            # The exception could be a verification error or any other processing error
            return HttpResponse("Error processing webhook", status=400)

        return HttpResponse(status=200)
    
    return HttpResponse("Invalid request method", status=405)

def payment_success(request):
    order_id = request.GET.get('order_id')
    if not order_id:
        messages.error(request, "Invalid request: Order ID is missing.")
        return redirect('plans_and_pricing')

    try:
        payment = Payment.objects.get(order_id=order_id)
        # Check for terminal states first
        if payment.status == 'FAILED':
            messages.error(request, "Your payment has failed. Please try again or contact support.")
            return redirect('plans_and_pricing')

        if payment.status != 'SUCCESS':
            # This handles both PENDING and PROCESSING states.
            # The webhook should ideally be faster, but this is a safe fallback.
            messages.warning(request, "Your payment is still processing. This page will refresh automatically. We will notify you once it's complete.")
            return render(request, 'onematrix/payment_processing.html', {'order_id': order_id})

    except Payment.DoesNotExist:
        messages.error(request, "Invalid Order ID. Your payment record was not found.")
        return redirect('plans_and_pricing')

    user = payment.user
    if not user:
         messages.error(request, "There was an issue associating your payment with an account. Please contact support.")
         return redirect('contact-us')

    # Generate a 6-digit OTP for profiling and send email
    otp = ''.join(random.choices(string.digits, k=6))
    otp_expiry = timezone.now() + timedelta(minutes=10)
    
    # Store OTP info in session for the verification step
    request.session['profiling_otp'] = otp
    request.session['profiling_otp_expiry'] = otp_expiry.isoformat()
    request.session['profiling_user_id'] = user.user_id
    
    try:
        send_mail(
            'Your 1Matrix Account Verification Code',
            f'Thank you for subscribing to 1Matrix!\n\n'
            f'Your verification code is: {otp}\n\n'
            f'This code will expire in 10 minutes.\n\n'
            f'Please use this code to complete your profile setup.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        messages.success(request, 'Your payment was successful! We have sent a verification code to your email to complete your account setup.')
    except Exception as e:
        logger.error(f"Failed to send profiling OTP email to {user.email}: {e}")
        messages.warning(request, "Your payment was successful, but we couldn't send the verification email. Please contact support to complete your account setup.")

    # Redirect to the profile completion page
    return redirect('complete_profile_setup')

def complete_profile_setup(request):
    logger = logging.getLogger(__name__)
    
    # Verify that the user is in the profiling flow via session
    profiling_user_id = request.session.get('profiling_user_id')
    if not profiling_user_id:
        messages.error(request, "Invalid session. Please start the payment process again.")
        return redirect('plans_and_pricing')

    try:
        user = User.objects.get(user_id=profiling_user_id)
    except User.DoesNotExist:
        messages.error(request, "User not found. Please contact support.")
        # Clear session to prevent reuse
        request.session.flush()
        return redirect('plans_and_pricing')

    if request.method == 'POST':
        otp = request.POST.get('otp', '').strip()
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        # --- OTP Validation ---
        session_otp = request.session.get('profiling_otp')
        session_otp_expiry_str = request.session.get('profiling_otp_expiry')
        
        if not session_otp or not session_otp_expiry_str:
            messages.error(request, "Your session has expired. Please try again.")
            return redirect('plans_and_pricing')
            
        session_otp_expiry = timezone.datetime.fromisoformat(session_otp_expiry_str)

        if timezone.now() > session_otp_expiry:
            messages.error(request, "The verification code has expired. Please restart the process.")
            # Clear session and guide user
            request.session.flush()
            return redirect('plans_and_pricing')

        if otp != session_otp:
            messages.error(request, "Invalid verification code.")
            return render(request, 'onematrix/profile_setup.html', {'user_email': user.email})

        # --- Password Validation ---
        if not password or not password_confirm or len(password) < 8:
            messages.error(request, "Please enter a password of at least 8 characters.")
            return render(request, 'onematrix/profile_setup.html', {'user_email': user.email})
        
        if password != password_confirm:
            messages.error(request, "Passwords do not match.")
            return render(request, 'onematrix/profile_setup.html', {'user_email': user.email})

        # --- Finalize User Profile ---
        user.set_password(password)  # Hashes the password
        user.is_profile_complete = True # Assuming you add this field to your User model
        user.save()

        # Clean up session
        request.session.flush()

        messages.success(request, "Your profile has been updated successfully! You can now log in.")
        # Redirect to your login page
        return redirect('account_login') # Assuming you have a login URL named 'account_login'

    return render(request, 'onematrix/profile_setup.html', {'user_email': user.email})

def payment_failure(request):
    order_id = request.GET.get('order_id')
    # You can add more logic here to retrieve payment details and show a more informative message.
    messages.error(request, "Your payment was not successful. Please try again or contact our support team if the issue persists.")
    return render(request, 'onematrix/payment_failure.html', {'order_id': order_id})


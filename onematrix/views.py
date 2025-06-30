from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, DetailView
from invoicing.models import Recipent, Invoice
from .models import FAQCategory, FAQItem, ContactUs, Payment, ProfileSetupToken
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
from User.models import User, PasswordResetToken, UserAppCredit, UserAgreementAcceptance
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta
import logging
from decimal import Decimal, InvalidOperation
from datetime import datetime
from django.contrib.auth import login
from django.views.decorators.http import require_POST

# Create your views here.

# It is recommended to store your API keys in environment variables
# For the purpose of this example, we are hardcoding them.
# Please replace with your actual keys.
# Professionalizing: Read from Django settings
# These should be set in your settings.py file, for example:
# CASHFREE_APP_ID = "YOUR_APP_ID"
# CASHFREE_SECRET_KEY = "YOUR_SECRET_KEY"
# CASHFREE_ENVIRONMENT = "sandbox"  # or "production"


def convert_to_json_serializable(data):
    """
    Recursively converts any datetime objects in a dict to ISO strings.
    """
    if isinstance(data, dict):
        return {k: convert_to_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_to_json_serializable(v) for v in data]
    elif isinstance(data, datetime):
        return data.isoformat()
    else:
        return data
    
def log_error(message, extra=None, **kwargs):
    if extra is None:
        extra = {}
    logger.error(f"[OneMatrix] {message}", extra=extra, **kwargs)


# Configure logger for OneMatrix views
logger = logging.getLogger('onematrix')

def log_info(message, extra=None):
    """Helper function to log information with consistent formatting"""
    if extra is None:
        extra = {}
    logger.info(f"[OneMatrix] {message}", extra=extra)

def log_error(message, extra=None):
    """Helper function to log errors with consistent formatting"""
    if extra is None:
        extra = {}
    logger.error(f"[OneMatrix] {message}", extra=extra)

def log_debug(message, extra=None):
    """Helper function to log debug information with consistent formatting"""
    if extra is None:
        extra = {}
    logger.debug(f"[OneMatrix] {message}", extra=extra)

def log_warning(message, extra=None):
    """Helper function to log warnings with consistent formatting"""
    if extra is None:
        extra = {}
    logger.warning(f"[OneMatrix] {message}", extra=extra)


Cashfree.XClientId = getattr(settings, 'CASHFREE_APP_ID', "956605704b2e8d84efba1d2a1e506659")
Cashfree.XClientSecret = getattr(settings, 'CASHFREE_SECRET_KEY', "cfsk_ma_prod_9c4245f2a1d88ddd7e0062511746ed8c_dc5a9c17")
CASHFREE_ENVIRONMENT = getattr(settings, 'CASHFREE_ENVIRONMENT', 'production')
Cashfree.XEnvironment = Cashfree.SANDBOX if CASHFREE_ENVIRONMENT == 'sandbox' else Cashfree.PRODUCTION

# Cashfree.XClientId = "956605704b2e8d84efba1d2a1e506659"
# Cashfree.XClientSecret = "cfsk_ma_test_0c2b7ebca198a28a94dbef99bf4644a8_92ac8754"
# Cashfree.XEnvironment = Cashfree.SANDBOX
# CASHFREE_ENVIRONMENT = 'sandbox'

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
        api_response = Cashfree().PGCreateOrder("2023-08-01", create_order_request)

        payment_session_id = api_response.data.payment_session_id
        logger.info(f"Payment session ID: {payment_session_id}")

        logger.info("Successfully received response from Cashfree API.")
           
        logger.info("Returning payment session ID to client")
        return JsonResponse({'payment_session_id': payment_session_id})

    except Exception as e:
        logger.error(f"Fatal error in create_payment_session: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'An unexpected error occurred. Our team has been notified.'}, status=500)

def send_profiling_email_if_needed(request, payment):
    """
    Sends the profiling setup email if it hasn't been sent for a given payment.
    This function is idempotent and safe to call multiple times.
    """
    logger = logging.getLogger(__name__)

    if not payment or payment.status != 'SUCCESS' or payment.profiling_email_sent:
        status_log = f"Payment status: {payment.status}" if payment else "No payment object"
        sent_log = f"Email sent flag: {payment.profiling_email_sent}" if payment else "N/A"
        logger.info(f"Skipping profiling email for Order {payment.order_id}. {status_log}, {sent_log}")
        return

    user = payment.user
    if not user:
        logger.error(f"Cannot send profiling email for Order {payment.order_id}: User not found.")
        return

    logger.info(f"Attempting to send profiling email for Order {payment.order_id} to {user.email}")
    
    otp = ''.join(random.choices(string.digits, k=6))
    token, created = ProfileSetupToken.objects.update_or_create(
        user=user,
        defaults={'otp': otp, 'expires_at': timezone.now() + timedelta(minutes=15)}
    )

    complete_profile_url = request.build_absolute_uri(f'/complete-profile-setup/{token.token}/')

    try:
        send_mail(
            'Your 1Matrix Account Verification and Profile Setup',
            f'Thank you for subscribing to 1Matrix!\n\n'
            f'Please complete your profile setup by clicking the link below:\n'
            f'{complete_profile_url}\n\n'
            f'Your verification code is: {otp}\n\n'
            f'This link and code will expire in 15 minutes.\n',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )
        
        payment.profiling_email_sent = True
        payment.save(update_fields=['profiling_email_sent'])
        
        logger.info(f"Successfully sent profiling email for Order {payment.order_id} and marked as sent.")
        messages.success(request, 'Your payment was successful! We have sent a setup link to your email.')
        
    except Exception as e:
        logger.error(f"Failed to send profiling email for Order {payment.order_id} to {user.email}: {e}")
        messages.warning(request, "Your payment was successful, but we had an issue sending the setup email. Please contact support.")

@csrf_exempt
def cashfree_webhook(request):
    log_info("Cashfree webhook received.")
    if request.method == "POST":
        signature = request.headers.get('x-webhook-signature')
        timestamp = request.headers.get('x-webhook-timestamp')
        raw_body = request.body

        log_info(f"Webhook headers: signature={'present' if signature else 'missing'}, timestamp={'present' if timestamp else 'missing'}")

        if not signature or not timestamp:
            log_warning("Webhook signature or timestamp missing.")
            return HttpResponse("Webhook signature or timestamp missing", status=400)

        try:
            # Verify signature first
            Cashfree().PGVerifyWebhookSignature(signature, raw_body, timestamp)
            log_info("Webhook signature verified successfully.")

            payload = json.loads(raw_body)
            log_debug(f"Webhook payload: {payload}")
            
            order_data = payload.get('data', {}).get('order', {})
            order_id = order_data.get('order_id')
            order_status = order_data.get('order_status')
            log_info(f"Processing webhook for order_id: {order_id} with status: {order_status}")

            if not order_id:
                log_error("Order ID missing in webhook payload.")
                return HttpResponse("Order ID missing in webhook", status=400)

            try:
                payment = Payment.objects.get(order_id=order_id)
                log_info(f"Found payment object (ID: {payment.id}) for order_id: {order_id}")
            except Payment.DoesNotExist:
                log_error(f"Payment record not found for order_id: {order_id}. This order may not have been initiated by our system.")
                return HttpResponse("Payment record not found", status=404)

            # Idempotency check: Prevent reprocessing successful or failed payments
            if payment.status in ['SUCCESS', 'FAILED']:
                log_warning(f"Webhook for order_id: {order_id} already processed. Current status: {payment.status}. Ignoring.")
                return HttpResponse(f"Webhook already processed with status {payment.status}", status=200)

            api_data_dict = convert_to_json_serializable(payload)
            payment.webhook_payload = api_data_dict
            payment.save()
            
            
            if order_status == 'PAID':
                log_info(f"Order {order_id} is PAID. Updating status to SUCCESS.")
                if not payment.user:
                    customer_details = payload.get('data', {}).get('customer_details', {})
                    customer_email = customer_details.get('customer_email')
                    log_info(f"Payment object for order {order_id} has no user. Trying to find user by email: {customer_email}")
                    user = User.objects.filter(email=customer_email).first()
                    if user:
                        payment.user = user
                        log_info(f"Found and assigned user {user.id} to payment {payment.id}")
                    else:
                        log_warning(f"Could not find a user with email {customer_email} for order {order_id}")
                
                payment.status = 'SUCCESS'
                payment.payment_id = payload.get('data', {}).get('payment', {}).get('cf_payment_id')
                
                user = payment.user
                if user:
                    log_info(f"Updating user profile for user: {user.email} (ID: {user.id})")
                    user.is_active = True
                    user.subscription_plan = payment.subscription_plan
                    user.last_payment_date = timezone.now().date()
                    user.last_payment_amount = payment.amount
                    user.last_payment_status = 'SUCCESS'

                    if payment.excluded_apps.exists():
                        excluded_app_names = list(payment.excluded_apps.values_list('name', flat=True))
                        log_info(f"Transferring {len(excluded_app_names)} excluded apps to user {user.id}: {excluded_app_names}")
                        user.excluded_apps.set(payment.excluded_apps.all())
                    
                    user.save()
                    payment.save()

                    # --- New Logic: Assign Credits and Validity ---
                    subscription = payment.subscription_plan
                    apps_in_plan = subscription.features.all()
                    
                    if payment.excluded_apps.exists():
                        apps_in_plan = apps_in_plan.exclude(id__in=payment.excluded_apps.all().values_list('id', flat=True))

                    for app in apps_in_plan:
                        try:
                            app_limit = AppSubscriptionLimit.objects.get(subscription=subscription, app=app)
                            credits = app_limit.credits if app_limit.limit_type == 'Limited' else -1 # -1 for unlimited
                        except AppSubscriptionLimit.DoesNotExist:
                            credits = -1 # Default to unlimited if no specific limit is set

                        UserAppCredit.objects.update_or_create(
                            user=user,
                            app=app,
                            defaults={
                                'credits_remaining': credits,
                                'valid_until': timezone.now().date() + timedelta(days=subscription.validity_days)
                            }
                        )
                        log_info(f"Assigned credits for app '{app.name}' to user {user.id}. Credits: {'Unlimited' if credits == -1 else credits}, Valid until: {timezone.now().date() + timedelta(days=subscription.validity_days)}")
                    # --- End New Logic ---
                    
                    log_info(f"User {user.id} saved.")
                    payment.save()
                    log_info(f"Payment {payment.id} saved with status SUCCESS.")

                    log_info(f"Calling send_profiling_email_if_needed for order {order_id}")
                    send_profiling_email_if_needed(request, payment)
                else:
                    log_error(f"Cannot update user profile for order {order_id} because no user is associated with the payment.")
                    payment.save() # Still save the payment status
                    log_info(f"Payment {payment.id} saved with status SUCCESS (no user found).")


            elif order_status in ['PAYMENT_FAILED', 'TERMINATED', 'CANCELLED']:
                log_warning(f"Order {order_id} status is {order_status}. Updating payment status to FAILED.")
                payment.status = 'FAILED'
                payment.save()
                log_info(f"Payment {payment.id} for order {order_id} saved with status FAILED.")
            
            else:
                log_info(f"Received unhandled order status '{order_status}' for order {order_id}. No action taken.")

        except Exception as e:
            # The exception could be a verification error or any other processing error
            log_error(f"Error processing webhook: {e}", extra={'exc_info': True})
            return HttpResponse("Error processing webhook", status=400)

        log_info(f"Webhook for order {order_id} processed successfully.")
        return HttpResponse(status=200)
    
    log_warning("Webhook received with invalid request method.")
    return HttpResponse("Invalid request method", status=405)

def payment_success(request):
    order_id = request.GET.get('order_id')
    if not order_id:
        messages.error(request, "Invalid request: Order ID is missing.")
        return redirect('plans_and_pricing')

    try:
        payment = Payment.objects.get(order_id=order_id)
        
        if payment.status == 'FAILED':
            messages.error(request, "Your payment has failed. Please try again or contact support.")
            return redirect('plans_and_pricing')

        # Fallback for when webhook is delayed or not working (e.g., in local dev)
        if payment.status != 'SUCCESS':
            log_info(f"Payment {order_id} status is '{payment.status}'. Verifying with Cashfree as a fallback.")
            try:
                # API call to verify payment status
                api_response = Cashfree().PGFetchOrder("2023-08-01", order_id)
                
                if api_response.data and api_response.data.order_status == 'PAID':
                    log_info(f"Cashfree confirms order {order_id} is PAID. Processing success logic.")
                    
                    # Convert the API response to be JSON serializable before saving
                    serializable_payload = convert_to_json_serializable(api_response.data.to_dict())

                    # Safely extract the payment ID from the payments array in the response
                    cf_payment_id = None
                    if 'payments' in serializable_payload and serializable_payload['payments']:
                        # Get the payment ID from the first payment in the list
                        cf_payment_id = serializable_payload['payments'][0].get('cf_payment_id')

                    # This block mimics the webhook's success logic.
                    payment.status = 'SUCCESS'
                    payment.webhook_payload = serializable_payload
                    payment.payment_id = cf_payment_id

                    user = payment.user
                    if user:
                        user.is_active = True
                        user.subscription_plan = payment.subscription_plan
                        user.last_payment_date = timezone.now().date()
                        user.last_payment_amount = payment.amount
                        user.last_payment_status = 'SUCCESS'

                        if payment.excluded_apps.exists():
                            user.excluded_apps.set(payment.excluded_apps.all())
                        
                        user.save()
                        payment.save()
                        
                        # --- New Logic: Assign Credits and Validity (Fallback) ---
                        subscription = payment.subscription_plan
                        apps_in_plan = subscription.features.all()
                        
                        if payment.excluded_apps.exists():
                            apps_in_plan = apps_in_plan.exclude(id__in=payment.excluded_apps.all().values_list('id', flat=True))

                        for app in apps_in_plan:
                            try:
                                app_limit = AppSubscriptionLimit.objects.get(subscription=subscription, app=app)
                                credits = app_limit.credits if app_limit.limit_type == 'Limited' else -1
                            except AppSubscriptionLimit.DoesNotExist:
                                credits = -1

                            UserAppCredit.objects.update_or_create(
                                user=user,
                                app=app,
                                defaults={
                                    'credits_remaining': credits,
                                    'valid_until': timezone.now().date() + timedelta(days=subscription.validity_days)
                                }
                            )
                            log_info(f"FALLBACK: Assigned credits for app '{app.name}' to user {user.id}. Credits: {'Unlimited' if credits == -1 else credits}, Valid until: {timezone.now().date() + timedelta(days=subscription.validity_days)}")
                        # --- End New Logic ---

                        log_info(f"Fallback successfully updated user {user.id} and payment {payment.id}.")
                    else:
                        log_error(f"Fallback could not find user for payment {payment.id}.")
                        payment.save()
                
                elif api_response.data and api_response.data.order_status in ['PAYMENT_FAILED', 'TERMINATED', 'CANCELLED']:
                    log_warning(f"Cashfree confirms order {order_id} has failed. Updating status.")
                    payment.status = 'FAILED'
                    payment.save()
                    messages.error(request, "Your payment has failed. Please try again or contact support.")
                    return redirect('plans_and_pricing')

                else:
                    # Status is still processing
                    log_info(f"Cashfree confirms order {order_id} is still processing. Showing processing page.")
                    messages.warning(request, "Your payment is still processing. This page will refresh automatically. We will notify you once it's complete.")
                    return render(request, 'onematrix/payment_processing.html', {'order_id': order_id})

            except Exception as e:
                log_error(f"Error verifying payment status for {order_id} with Cashfree: {e}", exc_info=True)
                messages.error(request, "We couldn't verify your payment status at the moment. Please contact support if you have been charged.")
                return redirect('plans_and_pricing')


    except Payment.DoesNotExist:
        messages.error(request, "Invalid Order ID. Your payment record was not found.")
        return redirect('plans_and_pricing')

    # --- Proceed only if payment status is now SUCCESS ---
    if payment.status != 'SUCCESS':
        # This case should be rare, but it's a final safeguard.
        log_warning(f"Payment {order_id} is still not in SUCCESS state after checks. Displaying processing page.")
        messages.warning(request, "Your payment is still processing. This page will refresh automatically.")
        return render(request, 'onematrix/payment_processing.html', {'order_id': order_id})
        
    # At this point, payment status is SUCCESS.
    # The webhook or the fallback should have already sent the email, but this is a final check.
    log_info(f"Payment {order_id} is SUCCESS. Ensuring profiling email is sent.")
    send_profiling_email_if_needed(request, payment)

    user = payment.user
    token = ProfileSetupToken.objects.filter(user=user).order_by('-created_at').first()

    if not user or not token:
         messages.error(request, "There was an issue initiating your profile setup. Please contact support.")
         return redirect('contact-us')

    # Redirect to the profile completion page.
    log_info(f"Redirecting user {user.id} to profile setup with token {token.token}")
    return redirect(f'/complete-profile-setup/{token.token}/')

def complete_profile_setup(request, token):
    logger = logging.getLogger(__name__)
    
    try:
        # Verify that the user is in the profiling flow via token
        profile_token = ProfileSetupToken.objects.select_related('user').get(token=token)
    except ProfileSetupToken.DoesNotExist:
        messages.error(request, "Invalid or expired profile setup link. Please check your email or restart the payment process.")
        return redirect('plans_and_pricing')

    if profile_token.is_expired():
        messages.error(request, "Your profile setup link has expired. Please restart the payment process to get a new one.")
        profile_token.delete()
        return redirect('plans_and_pricing')

    user = profile_token.user

    # The POST logic is now handled by dedicated AJAX views. This block will only be
    # hit if JavaScript is disabled, in which case we show an error.
    if request.method == 'POST':
        logger.warning(f"POST request received on complete_profile_setup for token {token}, which should be handled by AJAX.")
        messages.error(request, "There was a problem with the submission. Please enable JavaScript and try again.")
    
    # For GET request or if POST fails due to disabled JS
    active_agreement = UserAgreement.objects.filter(is_active=True).order_by('-updated_at').first()

    return render(request, 'onematrix/profile_setup.html', {
        'user_email': user.email,
        'user_phone': user.phone,
        'token': token,
        'agreement': active_agreement,
    })

def payment_failure(request):
    order_id = request.GET.get('order_id')
    # You can add more logic here to retrieve payment details and show a more informative message.
    messages.error(request, "Your payment was not successful. Please try again or contact our support team if the issue persists.")
    return render(request, 'onematrix/payment_failure.html', {'order_id': order_id})

@require_POST
@csrf_exempt
def accept_agreement_and_send_otp(request):
    logger = logging.getLogger(__name__)
    try:
        data = json.loads(request.body)
        token = data.get('token')
        name = data.get('name', '').strip()
        password = data.get('password')

        if not all([token, name, password]):
            return JsonResponse({'status': 'error', 'message': 'Missing required fields.'}, status=400)

        profile_token = ProfileSetupToken.objects.select_related('user').get(token=token)
        if profile_token.is_expired():
            return JsonResponse({'status': 'error', 'message': 'Your session has expired. Please refresh and try again.'}, status=400)

        user = profile_token.user
        otp = ''.join(random.choices(string.digits, k=6))
        
        # Store necessary data in session to finalize after OTP verification
        request.session['profile_setup_data'] = {
            'user_id': str(user.user_id),
            'token': token,
            'name': name,
            'password': make_password(password),
            'otp': otp,
            'otp_expires_at': (timezone.now() + timedelta(minutes=10)).isoformat(),
        }

        send_mail(
            'Your 1Matrix Account Final Verification',
            f'Hi {name},\n\nYour One-Time Password (OTP) to complete your profile setup is: {otp}\n\nThis OTP is valid for 10 minutes.',
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            fail_silently=False,
        )

        logger.info(f"Sent profile setup OTP to {user.email} for token {token}")
        return JsonResponse({'status': 'success', 'message': 'OTP sent to your email.'})

    except ProfileSetupToken.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Invalid session. Please refresh the page.'}, status=404)
    except Exception as e:
        logger.error(f"Error in accept_agreement_and_send_otp: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred.'}, status=500)


@require_POST
@csrf_exempt
def verify_profile_otp_and_finalize(request):
    logger = logging.getLogger(__name__)
    try:
        data = json.loads(request.body)
        submitted_otp = data.get('otp')
        
        profile_data = request.session.get('profile_setup_data')

        if not profile_data or not submitted_otp:
            return JsonResponse({'status': 'error', 'message': 'Session expired. Please start over.'}, status=400)

        if timezone.now() > datetime.fromisoformat(profile_data['otp_expires_at']):
            return JsonResponse({'status': 'error', 'message': 'OTP has expired. Please try again.'}, status=400)

        if profile_data['otp'] != submitted_otp:
            return JsonResponse({'status': 'error', 'message': 'Invalid OTP provided.'}, status=400)
            
        # --- Finalize User Profile ---
        user = User.objects.get(user_id=profile_data['user_id'])
        user.name = profile_data['name']
        user.password = profile_data['password']
        user.is_profile_complete = True
        user.save()

        # Save agreement acceptance
        active_agreement = UserAgreement.objects.filter(is_active=True).order_by('-version').first()
        if active_agreement:
            # You need a function to get the client's IP, let's assume one exists or add it.
            # For now, let's just use a placeholder.
            client_ip = request.META.get('REMOTE_ADDR')
            UserAgreementAcceptance.objects.create(
                user=user,
                agreement=active_agreement,
                ip_address=client_ip
            )

        # Clean up the token and session
        ProfileSetupToken.objects.filter(token=profile_data['token']).delete()
        del request.session['profile_setup_data']

        # Log the user in
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')

        logger.info(f"User {user.email} completed profile setup successfully.")
        messages.success(request, "Your profile has been updated successfully! Welcome to 1Matrix.")
        
        return JsonResponse({
            'status': 'success', 
            'message': 'Profile setup complete!',
            'redirect_url': '/user/dashboard/' # Or wherever you want to redirect
        })

    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found. Please contact support.'}, status=404)
    except Exception as e:
        logger.error(f"Error in verify_profile_otp_and_finalize: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'An unexpected error occurred.'}, status=500)


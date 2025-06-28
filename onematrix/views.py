from pyexpat.errors import messages
from django.shortcuts import render, redirect
from django.views.generic import TemplateView, ListView, DetailView
from invoicing.models import Recipent, Invoice
from .models import *
from rest_framework import viewsets, permissions
from .serializers import FAQCategorySerializer, FAQItemSerializer
from django.http import JsonResponse
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
# Create your views here.

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
            import logging
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
            import logging
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


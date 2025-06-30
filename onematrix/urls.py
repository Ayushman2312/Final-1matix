from django.urls import path, include
from .views import *
from invoicing.api import verify_professional, verify_passcode
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static

# Create a router for the FAQ API
router = DefaultRouter()
router.register(r'api/faq/categories', FAQCategoryViewSet)
router.register(r'api/faq/items', FAQItemViewSet)

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('contact-us/', ContactUsView.as_view(), name='contact-us'),
    path('about-us/', AboutUsView.as_view(), name='about-us'),
    path('privacy-policy/', PrivacyPolicyView.as_view(), name='privacy-policy'),
    path('terms-and-conditions/', TermsAndConditionsView.as_view(), name='terms-and-conditions'),
    path('cancellation/', CancellationView.as_view(), name='cancellation'),
    path('invoice-reports/<str:recipient_id>/', InvoiceReportsView.as_view(), name='invoice-reports'),
    path('shipping-and-delivery/', ShippingAndDeliveryView.as_view(), name='shipping_and_delivery'),
    path('plans-and-pricing/', PlansAndPricingView.as_view(), name='plans_and_pricing'),
    path('create-payment-session/', create_payment_session, name='create_payment_session'),
    # FAQ URLs
    path('faq/', FAQListView.as_view(), name='faq-list'),
    path('faq/category/<int:pk>/', FAQCategoryDetailView.as_view(), name='faq-category-detail'),
    path('test-api/', TestApi.as_view(), name='test-api'),
    # Include the FAQ API URLs
    path('', include(router.urls)),
    
    # API endpoints
    path('api/verify-professional/', verify_professional, name='verify-professional'),
    path('api/verify-passcode/', verify_passcode, name='verify-passcode'),
    path('api/contact/', ContactAPIView.as_view(), name='contact-api'),
    path('payment/success/', payment_success, name='payment_success'),
    path('payment/failure/', payment_failure, name='payment_failure'),
    path('payment/webhook/', cashfree_webhook, name='cashfree_webhook'),
    path('complete-profile-setup/<uuid:token>/', complete_profile_setup, name='complete_profile_setup'),
    path('accept-agreement-and-send-otp/', accept_agreement_and_send_otp, name='accept_agreement_and_send_otp'),
    path('verify-profile-otp-and-finalize/', verify_profile_otp_and_finalize, name='verify_profile_otp_and_finalize'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


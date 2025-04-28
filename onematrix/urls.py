from django.urls import path, include
from .views import *
from invoicing.api import verify_professional, verify_passcode
from rest_framework.routers import DefaultRouter

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
    # FAQ URLs
    path('faq/', FAQListView.as_view(), name='faq-list'),
    path('faq/category/<int:pk>/', FAQCategoryDetailView.as_view(), name='faq-category-detail'),
    
    # Include the FAQ API URLs
    path('', include(router.urls)),
    
    # API endpoints
    path('api/verify-professional/', verify_professional, name='verify-professional'),
    path('api/verify-passcode/', verify_passcode, name='verify-passcode'),
    path('api/contact/', ContactAPIView.as_view(), name='contact-api'),
]


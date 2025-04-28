from django.urls import path
from .views import *

urlpatterns = [
    path('', CustomerSupportLogin, name="support_login"),
    path('register/<str:passcode>/', RegisterView.as_view(), name="support_register"),
    # path('send_otp/', SupportLoginView.send_otp, name='send_otp'),
    # path('verify_otp/', SupportLoginView.verify_otp, name='verify_otp'),
    # path('login/', SupportLoginView.login, name='login'), 
    path('dashboard/', CustomerSupportDashboard.as_view(), name='customer_support_dashboard'),
    path('master_notifications_support/', MasterNotificationsSupport.as_view(), name='master_notifications_support'),
    path('success/<str:passcode>', Success.as_view(), name="support_success"),
]

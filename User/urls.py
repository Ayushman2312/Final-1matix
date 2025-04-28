from django.urls import path, include
from .views import *

# Remove the namespace for simplicity and to avoid potential issues
# app_name = 'User'

urlpatterns = [
    path('dashboard/', DashboardView.as_view(), name='dashboard'),
    path('create-ticket/', CreateTicketView.as_view(), name='create_ticket'),
    path('help_and_support/', HelpAndSupportView.as_view(), name='help_and_support'),
    path('api/feedback/', FeedbackView.as_view(), name='feedback'),
    path('signup/', SignupView.as_view(), name='signup'),
    path('check-username/', CheckUsernameView.as_view(), name='check_username'),
    path('accounts/', include('allauth.urls')),
    path('google-login/', GoogleLoginView.as_view(), name='google_login'),
    path('google-callback/', google_callback, name='google_callback'),
    path('login/', LoginView.as_view(), name='login'),
    path('debug-session/', DebugSessionView.as_view(), name='debug_session'),
    path('logout/', Logout, name='logout'),
]
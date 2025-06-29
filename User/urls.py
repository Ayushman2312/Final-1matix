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
    path('verify-signup-otp/', VerifySignupOTPView.as_view(), name='verify_signup_otp'),
    path('resend-signup-otp/', ResendSignupOTPView.as_view(), name='resend_signup_otp'),
    path('check-username/', CheckUsernameView.as_view(), name='check_username'),
    path('accounts/', include('allauth.urls')),
    path('google-login/', GoogleLoginView.as_view(), name='google_login'),
    path('google-callback/', google_callback, name='google_callback'),
    path('login/', LoginView.as_view(), name='login'),
    path('accept-terms/', AcceptTermsView.as_view(), name='accept_terms'),
    path('handle-accept-terms/', HandleAcceptTermsView.as_view(), name='handle_accept_terms'),
    path('verify-first-login-otp/', VerifyFirstLoginOtpView.as_view(), name='verify_first_login_otp'),
    path('debug-session/', DebugSessionView.as_view(), name='debug_session'),
    path('logout/', Logout, name='logout'),
    
    # Reminder URLs
    path('api/reminders/create/', CreateReminderView.as_view(), name='create_reminder'),
    path('api/reminders/list/', ListRemindersView.as_view(), name='list_reminders'),
    path('api/reminders/check/', CheckDueRemindersView.as_view(), name='check_reminders'),
    path('api/reminders/<uuid:reminder_id>/complete/', CompleteReminderView.as_view(), name='complete_reminder'),
    path('api/reminders/<uuid:reminder_id>/snooze/', SnoozeReminderView.as_view(), name='snooze_reminder'),
    
    # Quick Notes URLs
    path('api/quick-notes/create/', CreateQuickNoteView.as_view(), name='create_quick_note'),
    path('api/quick-notes/list/', ListQuickNotesView.as_view(), name='list_quick_notes'),
    path('api/quick-notes/<uuid:note_id>/toggle-pin/', ToggleQuickNotePinView.as_view(), name='toggle_note_pin'),
    path('api/quick-notes/<uuid:note_id>/delete/', DeleteQuickNoteView.as_view(), name='delete_quick_note'),

    # Forgot Password URLs
    path('forgot-password/', ForgotPasswordRequestView.as_view(), name='forgot_password'),
    path('reset-password/<uuid:token>/', ResetPasswordView.as_view(), name='reset_password'),
    path('verify-otp/', VerifyOtpView.as_view(), name='verify-otp'),

    # User Settings URLs
    path('settings/', ProfileSettingsView.as_view(), name='user_settings'),
    path('settings/profile/', ProfileSettingsView.as_view(), name='profile_settings'),
    path('settings/change-password/', ChangePasswordView.as_view(), name='change_password'),
    path('settings/notifications/', NotificationSettingsView.as_view(), name='notification_settings'),

    # New URL path for complete-profile/<uuid:token>/
    path('complete-profile/', CompleteProfileView.as_view(), name='complete_profile'),
    path('verify-profiling-otp/', VerifyProfilingOtpView.as_view(), name='verify_profiling_otp'),
]
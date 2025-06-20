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
]
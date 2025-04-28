from django.urls import path
from .views import *
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', AgentLogin, name='agent_login'),
    path('dashboard/', AgentDashboardView.as_view(), name='agent_dashboard'),
    path('meetings/', MeetingsView.as_view(), name='meetings'),
    path('profile/', AgentProfileView.as_view(), name='agent_profile'),
    # path('demo/', DemoView.as_view(), name='demo'),
    # path('api/meetings/', MeetingApiView.as_view(), name='meeting_api'),
    # path('api/agents/', AgentUserApiView.Was_view(), name='agent_api'),
    path('register/<str:passcode>/', RegisterView.as_view(), name='agent_register'),
    # path('send_otp/', AgentLoginView.send_otp, name='send_otp'),
    # path('verify_otp/', AgentLoginView.verify_otp, name='verify_otp'),
    # path('login/', AgentLoginView.login, name='login'),
    path('logout/', logout, name='logout'),
    path("save-audio/", save_audio, name="save_audio"),
    path('end-demo/', MeetingsView.end_demo, name='end_demo'),
    path('master-notifications/', MasterNotificationsView.as_view(), name='master_notifications'),
    path('agent-read/<str:agent_id>/', AgentReadView.as_view(), name='agent_read'),
    path('success/<str:passcode>', Success.as_view(), name='agent_success'),
    # path('start-demo-otp/', MeetingsView.send_demo_otp, name='start_demo_otp'),
    # path('verify-demo-otp/', MeetingsView.as_view(), name='verify_demo_otp'),
    # path('send_otp/',, name='send_otp'),

    # path('api/agents/', AgentApiView.as_view(), name='agent_api')/,
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
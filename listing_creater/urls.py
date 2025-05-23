from django.urls import path
from . import views

urlpatterns = [
    path("ai-chat/", views.ai_chat_view, name="ai_chat_view"),
    path("api/generate-listing/", views.ai_chat_view, name="generate_listing"),
]


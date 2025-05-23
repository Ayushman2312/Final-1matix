from django.urls import path
from . import views

app_name = 'trends'

urlpatterns = [
    path('', views.trends_view, name='trends'),
    path('insights/<str:keyword>/', views.insights_view, name='insights'),
    path('insights/', views.insights_view, name='insights'),
    path('api/', views.trends_api, name='trends_api'),
    path('ai-insights/', views.ai_insights_api, name='ai_insights_api'),
    path('ai-analysis/', views.ai_analysis_api, name='ai_analysis_api'),
]

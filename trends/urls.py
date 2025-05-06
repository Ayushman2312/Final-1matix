from django.urls import path
from .views import TrendsView, TrendsApiView, InsightsView, AiInsightsApiView

app_name = 'trends'

urlpatterns = [
    path('', TrendsView.as_view(), name='trends'),
    path('api/data/', TrendsApiView.as_view(), name='trends_api'),
    path('insights/<str:keyword>/', InsightsView.as_view(), name='insights'),
    path('api/ai-insights/', AiInsightsApiView.as_view(), name='ai_insights_api'),
]

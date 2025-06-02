from django.urls import path
from .views import SalesDataUploadView, BusinessAnalyticsView, AnalysisResultView

app_name = 'business_analytics'

urlpatterns = [
    # API endpoints
    path('api/upload/', SalesDataUploadView.as_view(), name='api_upload_sales_data'),
    path('api/analysis/', AnalysisResultView.as_view(), name='analysis_list'),
    path('api/analysis/<uuid:analysis_id>/', AnalysisResultView.as_view(), name='analysis_detail'),
    
    # Dashboard view
    path('dashboard/', BusinessAnalyticsView.as_view(), name='dashboard'),
    path('dashboard/<int:analysis_id>/', BusinessAnalyticsView.as_view(), name='dashboard_with_analysis'),
]

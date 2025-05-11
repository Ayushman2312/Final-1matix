from django.urls import path
from .views import DataMinerView

urlpatterns = [
    path('', DataMinerView.as_view(), name='data_miner'),
    path('download/<int:history_id>/', DataMinerView.as_view(), {'action': 'get_excel'}, name='download_excel'),
    path('download/', DataMinerView.as_view(), name='download_current_results'),
]
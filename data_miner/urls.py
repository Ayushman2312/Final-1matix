from django.urls import path
from .views import *

urlpatterns = [
    path('', DataMinerView.as_view(), name='data_miner'),
    path('download/<int:history_id>/', DataMinerView.as_view(), name='download_excel'),
    path('download/', DataMinerView.as_view(), name='download_current_results'),
]
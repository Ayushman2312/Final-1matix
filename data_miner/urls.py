from django.urls import path
from .views import DataMinerView, TaskStatusView, BackgroundTasksView, TestCeleryView

urlpatterns = [
    path('', DataMinerView.as_view(), name='data_miner'),
    path('download/<int:history_id>/', DataMinerView.as_view(), {'action': 'get_excel'}, name='download_excel'),
    path('download/', DataMinerView.as_view(), name='download_current_results'),
    path('api/task-status/<str:task_id>/', TaskStatusView.as_view(), name='task_status'),
    path('api/cancel-task/<str:task_id>/', DataMinerView.as_view(), {'action': 'cancel_task'}, name='cancel_task'),
    path('background-tasks/', BackgroundTasksView.as_view(), name='background_tasks'),
    path('api/test-celery/', TestCeleryView.as_view(), name='test_celery'),
]
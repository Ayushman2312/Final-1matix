from django.urls import path
from .views import *
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('company/', CompanyView.as_view(), name='company'),
    path('creation/', CreationView.as_view(), name='creation'),
    path('onboarding/', OnboardingView.as_view(), name='employees'),
    path('attendance/', AttendanceView.as_view(), name='attendance'),
    path('qr-code/', csrf_exempt(QRCodeView.as_view()), name='qr-code'),
    path('get-qr-code/', QRCodeView.as_view(), name='get-qr-code'),
    path('generate-qr-code/', QRCodeView.as_view(), name='generate-qr-code'),
    path('mark-attendance/', EmployeeAttendanceView.as_view(), name='mark_attendance'),
    path('create-company/', CreateCompanyView.as_view(), name='create-company'),
    path('create-folder/', CreateFolderView.as_view(), name='create-folder'),
    path('folder/<str:folder_id>/', FolderView.as_view(), name='folder'),
    path('create-data/<str:folder_id>/', FolderView.as_view(), name='add-data'),
    path('update-data/<str:folder_id>/', FolderView.as_view(), name='update-data'),
    path('delete-data/<str:folder_id>/', FolderView.as_view(), name='delete-data'),
]


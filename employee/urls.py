from django.urls import path
from .views import *

urlpatterns = [
    path('', EmployeeLogin, name='employee_login'),
    path('register/<str:passcode>/', RegisterView.as_view(), name='employee_register'),
    path('profile/', EmployeeProfileView.as_view(), name='employee_profile'),
    path('employee-read/<int:employee_id>/', EmployeeReadView.as_view(), name='employee_read'),
    path('master_notifications_support/', MasterNotificationsView.as_view(), name='master_notifications_support'),
    path('success/<str:passcode>', Success.as_view(), name="employee_success"),
    # path('employee/', views.employee_list, name='employee_list'),
]


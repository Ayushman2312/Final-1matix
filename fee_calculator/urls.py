from django.urls import path
from .views import *

urlpatterns = [
    path('', FeeCalculatorView.as_view(), name='calculator'),
]

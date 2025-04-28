from django.urls import path
from .views import trends_view

app_name = 'trends'

urlpatterns = [
    path('', trends_view, name='trends'),
]

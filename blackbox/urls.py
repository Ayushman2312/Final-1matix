from django.urls import path
from .views import *

urlpatterns = [
    path('', BlackBoxSearchView.as_view(), name='black_box_search'),
    path('api/', BlackBoxApiView.as_view(), name='black_box_api'),
]


from django.urls import path
from .views import *

urlpatterns = [
    # Web Views
    path('product-details/', product_form_view, name='product_form'),
    path('product-details/success/', product_form_success, name='product_form_success'),
    path('my-products/', user_products_view, name='user_products'),
    
    # API Endpoints
    path('api/products/', published_products_api, name='published_products_api'),
    path('api/products/<uuid:product_id>/', product_detail_api, name='product_detail_api'),
    path('api/my-products/', user_products_api, name='user_products_api'),
    path('api/products/create/', create_product_api, name='create_product_api'),
]


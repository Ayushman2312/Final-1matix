from django.urls import path
from .views import *

urlpatterns = [
    path('', CreateProductCardView.as_view(), name='create_product_card'),
    path('all/', AllProductCardView.as_view(), name='all_product_card'),
    path('product/<str:product_id>/', ProductCardDetailView.as_view(), name='product_card_detail'),
    path('delete/<str:product_id>/', delete_product, name='delete_product'),
    path('update/<str:product_id>/', update_product_card, name='update_product_card'),
    path('category/', CategoryView.as_view(), name='category'),
    path('edit_category/<int:category_id>/', edit_category, name='edit_category'),
    path('delete_category/<int:category_id>/', DeleteCategoryView.as_view(), name='delete_category'),
    path('api/products/', ProductViewSet.as_view({'get': 'list', 'post': 'create'}), name='product-list'),
    path('api/products/<str:pk>/', ProductViewSet.as_view({'get': 'retrieve'}), name='product-detail'),
    path('api/products/search/', search_products, name='search_products'),
]

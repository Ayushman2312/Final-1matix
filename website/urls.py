from django.urls import path
from . import views

urlpatterns = [
    path('select-template/', views.select_template, name='select_template'),
    path('create/<int:template_id>/', views.create_website, name='create_website'),
    path('edit/<int:website_id>/', views.edit_website, name='edit_website'),
    path('preview/<int:website_id>/', views.preview_website, name='preview_website'),
    path('delete/<int:website_id>/', views.delete_website, name='delete_website'),
    path('domain-settings/', views.domain_settings, name='domain_settings'),
    path('domain-verification/<int:domain_id>/', views.domain_verification, name='domain_verification'),
    path('delete-domain/<int:domain_id>/', views.delete_domain, name='delete_domain'),
    path('about-us/', views.about_us, name='about_us'),
    path('fix-all-slugs/', views.fix_all_slugs, name='fix_all_slugs'),
    
    # Dashboard URLs
    path('dashboard/', views.dashboard, name='website_dashboard'),
    
    # Page management URLs
    path('pages/<int:website_id>/', views.manage_pages, name='manage_pages'),
    path('pages/<int:website_id>/create/', views.create_page, name='create_page'),
    path('pages/edit/<int:page_id>/', views.edit_page, name='edit_page'),
    path('pages/delete/<int:page_id>/', views.delete_page, name='delete_page'),
    path('pages/<int:website_id>/reorder/', views.reorder_pages, name='reorder_pages'),
    
    # Product and category management URLs
    path('product-categories/', views.product_category, name='website_product_category'),
    path('product-categories/delete/<int:category_id>/', views.delete_category, name='delete_category'),
    path('products/', views.products, name='website_products'),
    path('products/create/', views.product_create, name='website_product_create'),
    path('products/edit/<uuid:product_id>/', views.product_edit, name='website_product_edit'),
    path('products/delete/<uuid:product_id>/', views.product_delete, name='website_product_delete'),
    path('products/detail/<uuid:product_id>/', views.product_detail, name='website_product_detail'),
    
    # Public shareable URL
    path('s/<slug:public_slug>/', views.public_website, name='public_website'),
    path('s/<slug:public_slug>/<slug:page_slug>/', views.public_website_page, name='public_website_page'),
    
    # Shop redirect URL
    path('<str:public_slug>/shop/', views.shop_redirect, name='shop_redirect'),
    
    # Policy pages
    path('s/<slug:public_slug>/privacy-policy/', views.privacy_policy_page, name='privacy_policy_page'),
    path('s/<slug:public_slug>/terms-conditions/', views.terms_conditions_page, name='terms_conditions_page'),
    path('s/<slug:public_slug>/refund-policy/', views.refund_policy_page, name='refund_policy_page'),
    
    # Enhanced homepage URL pattern
    path('website/<int:website_id>/enhanced-home/', views.view_enhanced_homepage, name='view_enhanced_homepage'),
    path('website/<int:website_id>/apply-enhanced-template/', views.apply_enhanced_template, name='apply_enhanced_template'),
    
    # SEO Management
    path('website/<int:website_id>/seo/', views.seo_management, name='seo_management'),
    
    # Debug utilities
    path('debug/fix-templates/', views.debug_fix_templates, name='debug_fix_templates'),
    
    path('<str:public_slug>/page/<str:page_slug>/', views.public_website_page, name='public_website_page'),
    path('<str:public_slug>/category/<str:category_slug>/', views.category_detail, name='category_detail'),
]

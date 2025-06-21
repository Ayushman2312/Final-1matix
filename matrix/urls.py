"""
URL configuration for matrix project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', include('pwa.urls')),  # PWA URLs
    path('offline/', TemplateView.as_view(template_name="offline.html"), name="offline"),
    path('manifest.json', RedirectView.as_view(url=settings.STATIC_URL + 'manifest.json'), name='manifest'),
    path('', include('onematrix.urls')),
    path('apps/', include('app.urls')),
    path('alavi07/', admin.site.urls),
    path('masteradmin/', include('masteradmin.urls')),
    path('agents/', include('agents.urls')),
    path('customersupport/', include('customersupport.urls')),
    path('user/', include('User.urls')),
    path('employee/', include('employee.urls')),
    path('fee_calculator/', include('fee_calculator.urls')),
    path('listing_creater/', include('listing_creater.urls')),
    path('product_card/', include('product_card.urls')),
    path('hr/', include('hr.urls')),
    path('invoicing/', include('invoicing.urls')),
    path('blackbox/', include('blackbox.urls')),
    path('onematrix/', include('onematrix.urls')),
    path('website/', include('website.urls')),
    path('data_miner/', include('data_miner.urls')),
    path('trends/', include('trends.urls')),
    path('business_analytics/', include('business_analytics.urls')),
    path('accounts/', include('allauth.urls')),
    path('landingx/', include('landingx.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

    
    

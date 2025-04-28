from django.urls import path
from .views import *

urlpatterns = [
    path('companies/', CompaniesView.as_view(), name='companies'),
    path('create-company/', CreateCompanyView.as_view(), name='create_company'),
    path('edit-company/<str:company_id>/', EditCompanyView.as_view(), name='edit_company'),
    path('delete-company/<str:company_id>/', DeleteCompanyView.as_view(), name='delete_company'),
    path('create-invoice/', CreateInvoiceView.as_view(), name='create_invoice'),
    path('upi-payment/<str:company_id>/', UpiPaymentView.as_view(), name='upi_payment'),
    path('reports/', ReportsView.as_view(), name='reports'),
    path('add-billing/', AddBillingView.as_view(), name='add_billing'),
    path('recipient-auth/', RecipientAuthView.as_view(), name='recipient_auth'),
    path('create-recipient/', CreateRecipientView.as_view(), name='create_recipient'),
]


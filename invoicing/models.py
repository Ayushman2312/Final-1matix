from django.db import models
import uuid
from django.utils import timezone
from User.models import User
from product_card.models import Product
# Create your models here.


class Company(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    company_id = models.UUIDField(default=uuid.uuid4,primary_key=True, editable=False, unique=True)
    company_name = models.CharField(max_length=255)
    company_logo = models.ImageField(upload_to='company_logo/', blank=True, null=True)
    company_gst_number = models.CharField(max_length=255)
    company_mobile_number = models.CharField(max_length=255)
    company_pincode = models.CharField(max_length=255, null=True, blank=True)
    company_email = models.EmailField()
    company_state = models.CharField(max_length=255, null=True, blank=True)
    company_signature = models.ImageField(upload_to='company_signature/', blank=True, null=True)
    company_invoice_prefix = models.CharField(max_length=255)
    company_bank_name = models.CharField(max_length=255)
    company_bank_account_number = models.CharField(max_length=255)
    company_bank_ifsc_code = models.CharField(max_length=255)
    company_upi_id = models.CharField(max_length=255)
    company_address = models.TextField()
    company_created_at = models.DateTimeField(default=timezone.now)
    company_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.company_name

BILLING_TYPE_CHOICES = [
    ('Proforma Invoice', 'Proforma Invoice'),
    ('Invoice', 'Invoice'),
]

class Billing(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    billing_id = models.UUIDField(default=uuid.uuid4,primary_key=True, editable=False, unique=True)
    billing_email = models.EmailField(null=True, blank=True)
    billing_name = models.CharField(max_length=255)
    billing_state = models.CharField(max_length=255, null=True, blank=True)
    billing_address = models.TextField(null=True, blank=True)
    billing_phone = models.CharField(max_length=255, null=True, blank=True)
    billing_gst_number = models.CharField(max_length=255, null=True, blank=True)
    billing_created_at = models.DateTimeField(default=timezone.now)
    billing_updated_at = models.DateTimeField(auto_now=True)
    billing_pincode = models.CharField(max_length=6, null=True, blank=True)

    def __str__(self):
        return self.billing_name

    
class Invoice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True)
    billing = models.ForeignKey(Billing, on_delete=models.CASCADE, null=True, blank=True)
    invoice_id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False, unique=True)
    invoice_pdf = models.FileField(upload_to='invoices/', null=True, blank=True)
    invoice_title = models.CharField(max_length=255, null=True, blank=True)
    invoice_created_at = models.DateTimeField(default=timezone.now)
    invoice_type = models.CharField(max_length=255, choices=BILLING_TYPE_CHOICES, null=True, blank=True)
    invoice_product = models.JSONField(null=True, blank=True)
    invoice_quantity = models.IntegerField(null=True, blank=True)
    invoice_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    invoice_unit_type = models.CharField(max_length=255, null=True, blank=True)
    payment_screenshot = models.ImageField(upload_to='payment_screenshots/', null=True, blank=True)
    payment_status = models.BooleanField(default=False)
    invoice_updated_at = models.DateTimeField(auto_now=True)
    shipping_address = models.TextField(null=True, blank=True)
    shipping_pincode = models.CharField(max_length=6, null=True, blank=True)
    use_billing_address = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.invoice_title or 'Untitled'} - {self.invoice_created_at.strftime('%Y-%m-%d')}"

    def save(self, *args, **kwargs):
        if not self.invoice_title and self.company and self.billing:
            self.invoice_title = f"{self.company.company_name}_{self.billing.billing_name}"
        super().save(*args, **kwargs)


class Recipent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    companies = models.ManyToManyField(Company, blank=True)
    recipent_id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False, unique=True)
    recipent_mobile_number = models.CharField(max_length=255)
    security_code = models.CharField(max_length=255)
    passcode = models.CharField(max_length=255)
    recipent_created_at = models.DateTimeField(default=timezone.now)
    recipent_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.recipent_mobile_number

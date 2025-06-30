from django.db import models
import uuid
from django.utils import timezone
from datetime import timedelta

# Create your models here.

class FAQCategory(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "FAQ Category"
        verbose_name_plural = "FAQ Categories"
        ordering = ['order', 'name']


class FAQItem(models.Model):
    category = models.ForeignKey(FAQCategory, on_delete=models.CASCADE, related_name='faq_items')
    question = models.CharField(max_length=500)
    answer = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.question
    
    class Meta:
        verbose_name = "FAQ Item"
        verbose_name_plural = "FAQ Items"
        ordering = ['category', 'order', 'question']


class ContactUs(models.Model):
    name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=255)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Contact Us"
        verbose_name_plural = "Contact Us"


class Payment(models.Model):
    PAYMENT_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('SUCCESS', 'Success'),
        ('FAILED', 'Failed'),
    ]

    user = models.ForeignKey('User.User', on_delete=models.SET_NULL, null=True, blank=True)
    order_id = models.CharField(max_length=255, unique=True)
    payment_id = models.CharField(max_length=255, null=True, blank=True)
    subscription_plan = models.ForeignKey('masteradmin.Subscription', on_delete=models.SET_NULL, null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='PENDING')
    customer_email = models.EmailField()
    customer_phone = models.CharField(max_length=20, blank=True, null=True)
    excluded_apps = models.ManyToManyField('app.Apps', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    webhook_payload = models.JSONField(blank=True, null=True)
    profiling_email_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"Payment {self.id} for Order {self.order_id}"

    class Meta:
        ordering = ['-created_at']


class ProfileSetupToken(models.Model):
    user = models.OneToOneField('User.User', on_delete=models.CASCADE)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def save(self, *args, **kwargs):
        if not self.id:
            self.expires_at = timezone.now() + timedelta(minutes=15)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Profile Setup Token for {self.user.email}"


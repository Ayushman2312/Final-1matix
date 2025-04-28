from django.db import models
import uuid
from agents.models import AgentUser
from django.contrib.auth.hashers import check_password as django_check_password
# Create your models here

class User(models.Model):
    user_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255,null=True,blank=True)
    email = models.EmailField(unique=True,null=True,blank=True)
    phone = models.CharField(max_length=10, unique=True,null=True,blank=True)
    gst_number = models.CharField(max_length=15, blank=True, null=True)
    subscription_plan = models.ForeignKey('masteradmin.Subscription', on_delete=models.CASCADE, null=True, blank=True)
    password = models.CharField(max_length=255, null=True, blank=True)
    address = models.TextField(blank=True, null=True)
    agent = models.ForeignKey(AgentUser, on_delete=models.CASCADE, null=True, blank=True)
    discount = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    user_policy = models.TextField(blank=True, null=True)
    upi_id = models.CharField(max_length=255, blank=True, null=True)
    last_payment_date = models.DateField(null=True, blank=True)
    last_payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    last_payment_status = models.CharField(max_length=255, blank=True, null=True)
    last_payment_mode = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def check_password(self, raw_password):
        """
        Check if the provided password matches the stored hashed password
        """
        if not hasattr(self, 'password'):
            return False
        return django_check_password(raw_password, self.password)

class UserPolicy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
class UserArticle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to='user_articles/', null=True, blank=True)
    description = models.TextField()
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class Feedbacks(models.Model):
    RATING_CHOICES = (
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    )
    
    rating = models.IntegerField(choices=RATING_CHOICES)
    message = models.TextField()
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Feedback from {self.name} - {self.rating} stars"

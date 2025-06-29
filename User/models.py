from django.db import models
import uuid
from agents.models import AgentUser
from django.contrib.auth.hashers import check_password as django_check_password
from django.utils import timezone
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
    is_staff = models.BooleanField(default=False)
    is_first_login = models.BooleanField(default=True)
    excluded_apps = models.ManyToManyField('app.Apps', blank=True, help_text="Apps that the user has chosen to exclude from their plan.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # New fields for User Settings
    profile_picture = models.ImageField(upload_to='profile_pictures/', null=True, blank=True)
    timezone = models.CharField(max_length=100, default='UTC')
    language = models.CharField(max_length=10, default='en')
    
    # 2FA Settings
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=255, null=True, blank=True)
    
    # Notification Settings
    email_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    in_app_notifications = models.BooleanField(default=True)
    notification_frequency = models.CharField(max_length=20, default='instant') # instant, daily, weekly

    def __str__(self):
        return f"{self.name} - {self.user_id}"

    def check_password(self, raw_password):
        """
        Check if the provided password matches the stored hashed password
        """
        if not hasattr(self, 'password'):
            return False
        return django_check_password(raw_password, self.password)

    def has_app_access(self, app):
        """
        Check if a user has access to a specific app.
        """
        # 1. Check if the app is globally disabled by an admin
        if app.is_temporarily_disabled:
            return False

        # 2. Check if the user has an active subscription plan
        if not self.subscription_plan:
            return False

        # 3. Check if the app is part of the user's subscription plan features
        if not self.subscription_plan.features.filter(pk=app.pk).exists():
            return False
            
        # 4. Check if the user has personally excluded this app
        if self.excluded_apps.filter(pk=app.pk).exists():
            return False
            
        # If all checks pass, the user has access
        return True

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

class Reminder(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('snoozed', 'Snoozed'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminders')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    reminder_time = models.DateTimeField()
    timezone_name = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    snoozed_until = models.DateTimeField(null=True, blank=True)
    last_notification = models.DateTimeField(null=True, blank=True)
    notification_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.user.name}"
    
    def is_due(self):
        """Check if the reminder is due for notification"""
        now = timezone.now()
        
        if self.status == 'completed':
            return False
            
        if self.status == 'snoozed' and self.snoozed_until and self.snoozed_until > now:
            return False
            
        return self.reminder_time <= now
    
    def snooze(self, minutes=10):
        """Snooze the reminder for the specified number of minutes"""
        self.status = 'snoozed'
        self.snoozed_until = timezone.now() + timezone.timedelta(minutes=minutes)
        self.save()
    
    def mark_as_completed(self):
        """Mark the reminder as completed"""
        self.status = 'completed'
        self.save()
    
    def record_notification(self):
        """Record that a notification was sent for this reminder"""
        self.last_notification = timezone.now()
        self.notification_count += 1
        self.save()

class QuickNote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='quick_notes')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.user.name}"
    
    class Meta:
        ordering = ['-created_at']  # Newest first by default

class LoginActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='login_activities')
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=255)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20) # e.g., 'Success', 'Failed'

    def __str__(self):
        return f"{self.user.name} - {self.status} at {self.timestamp}"

class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    is_remembered = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    last_activity = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session for {self.user.name} ({self.session_key})"

class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Password reset token for {self.user.name}"

class UserAgreementAcceptance(models.Model):
    """Model to track which agreement a user accepted during signup"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agreement_acceptances')
    agreement = models.ForeignKey('masteradmin.UserAgreement', on_delete=models.SET_NULL, null=True)
    agreement_title = models.CharField(max_length=255)  # Store title in case agreement is deleted
    agreement_content = models.TextField()  # Store content in case agreement is deleted
    accepted_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.email} - {self.agreement_title} - {self.accepted_at}"
    
    class Meta:
        verbose_name = "User Agreement Acceptance"
        verbose_name_plural = "User Agreement Acceptances"
        ordering = ['-accepted_at']

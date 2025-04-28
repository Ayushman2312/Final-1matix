from django.db import models
import uuid
from django.utils import timezone
from User.models import User
from agents.models import AgentUser
from employee.models import Employee
from customersupport.models import SupportUser

class MasterAdmin(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    phone_number = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return self.email

class Subscription(models.Model):
    PLAN_TYPES = [
        ('Monthly', 'Monthly'),
        ('Quarterly', 'Quarterly'),
        ('Yearly', 'Yearly'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    plan_type = models.CharField(max_length=10, choices=PLAN_TYPES)
    price_monthly = models.DecimalField(max_digits=10, decimal_places=2)
    features = models.ManyToManyField('app.Apps', blank=True)
    validity_days = models.PositiveIntegerField()
    discount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    users = models.PositiveIntegerField(default=1)
    max_users = models.PositiveIntegerField(default=4)
    additional_user_cost = models.DecimalField(max_digits=10, decimal_places=2, default=1000)
    is_active = models.BooleanField(default=True)
    is_paused = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    paused = models.BooleanField(default=False)

    def __str__(self):
        return self.name

# masteradmin/models.py

class AppList(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name
    
DISCOUNT_TYPES = [
        ('Flat', 'Flat'),
        ('Percent', 'Percent'),
    ]

class Coupons(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=50, unique=True)
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPES)
    rate = models.DecimalField(max_digits=10, decimal_places=2)
    number_of_uses = models.PositiveIntegerField(default=1)  # -1 for unlimited
    expiry_date = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.name
    
COMPLAINTS_DEPARTMENT = (
        ('Accounts and Billing', 'Accounts and Billing'),
        ('Sales', 'Sales'),
        ('Marketing', 'Marketing'),
        ('IT', 'IT'),
        ('Customer Care', 'Customer Care'),
    )

class Tickets(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mobile_number = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField()
    problem = models.TextField(null=True, blank=True)
    attachment = models.FileField(upload_to='complaints/', null=True, blank=True)
    status = models.CharField(max_length=255, choices=[('Pending', 'Pending'), ('Resolved', 'Resolved')], default='Pending', null=True, blank=True)
    priority = models.CharField(max_length=255, choices=[('Normal', 'Normal'), ('Urgent', 'Urgent')], default='Normal', null=True, blank=True)
    department = models.CharField(max_length=255, choices= COMPLAINTS_DEPARTMENT, default='hr', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    assigned_to = models.ForeignKey(SupportUser, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.mobile_number
    
class Feedback(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    feedback = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class WhatsOnMind(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, null=True, blank=True)
    message = models.TextField(null=True, blank=True)
    department_type = models.CharField(max_length=255, null=True, blank=True)  # Changed from department to department_type to match view
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.title

class WhatsOnMindReadStatus(models.Model):
    whats_on_mind = models.ForeignKey(WhatsOnMind, on_delete=models.CASCADE)
    agent = models.ForeignKey(AgentUser, on_delete=models.CASCADE, null=True, blank=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, blank=True) 
    support = models.ForeignKey(SupportUser, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [
            ('whats_on_mind', 'agent'),
            ('whats_on_mind', 'employee'),
            ('whats_on_mind', 'support')
        ]
    def __str__(self):
        return f"{self.whats_on_mind.title} - {self.agent.name if self.agent else self.employee.name if self.employee else self.support.name}"

class AgentNotification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent_user = models.ForeignKey(AgentUser, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return self.agent_user.name
class EmployeeNotification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee_user = models.ForeignKey(Employee, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    def __str__(self):
        return self.employee_user.name
    
    
class SupportNotification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    support_user = models.ForeignKey(SupportUser, on_delete=models.CASCADE)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    def __str__(self):
        return self.support_user.name



class AI_Prompt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    platform = models.CharField(max_length=255, unique=True)
    prompt = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.prompt

class UserNotification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.URLField(null=True, blank=True)
    attachment = models.FileField(upload_to='notifications/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    users = models.ManyToManyField(User, through='UserNotificationRecipient')

    def __str__(self):
        return self.title
# This class manages the relationship between notifications and users, tracking which users have received
# and read which notifications. It's crucial for:
# 1. Ensuring each user only receives a notification once (via unique_together constraint)
# 2. Tracking read status and timing of notifications per user
# 3. Enabling efficient querying of notifications for specific users
# 4. Managing the many-to-many relationship between notifications and users with additional metadata
class UserNotificationRecipient(models.Model):
    notification = models.ForeignKey(UserNotification, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE) 
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['notification', 'user']

    def __str__(self):
        return f"{self.notification.title} - {self.user.name}"

class QuickNotes(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    note = models.TextField()
    is_pinned = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

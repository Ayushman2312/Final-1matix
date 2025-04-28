from django.db import models
import uuid
from django.utils import timezone

class Policy(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    terms_and_conditions = models.TextField(null=True)

    def __str__(self):
        return self.name

class AgentUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    department = models.ForeignKey(Policy, on_delete=models.CASCADE, null=True)
    photo = models.ImageField(upload_to='agents/photos/', null=True)
    name = models.CharField(max_length=100, null=True)
    agent_passcode = models.CharField(unique=True, max_length=128, null=True)
    email = models.EmailField(unique=True, null=True)
    password = models.CharField(max_length=128, null=True)
    phone_number = models.CharField(max_length=15, null=True)
    pan_number = models.CharField(max_length=10, null=True)
    aadhar_number = models.CharField(max_length=12, null=True)
    address = models.TextField(null=True)
    dob = models.DateField(null=True)
    gender = models.CharField(max_length=10, null=True)
    qualification = models.CharField(max_length=100, null=True)
    qualification_file = models.FileField(upload_to='agents/qualification_files/', null=True)
    bank_account_holder_name = models.CharField(max_length=100, null=True)
    bank_account_number = models.CharField(max_length=15, null=True)
    bank_name = models.CharField(max_length=100, null=True)
    branch_name = models.CharField(max_length=100, null=True)
    bank_ifsc_code = models.CharField(max_length=10, null=True)
    cancelled_cheque_file = models.FileField(upload_to='agents/cancelled_cheque_files/', null=True)
    offer_letter_file = models.FileField(upload_to='agents/offer_letter_files/', null=True)
    bank_statement_file = models.FileField(upload_to='agents/bank_statement_files/', null=True)
    increment_letter_file = models.FileField(upload_to='agents/increment_letter_files/', null=True)
    pay_slip_file = models.FileField(upload_to='agents/pay_slip_files/', null=True)
    experience_letter_file = models.FileField(upload_to='agents/experience_letter_files/', null=True)
    leave_letter_file = models.FileField(upload_to='agents/leave_letter_files/', null=True)
    addhar_card_file = models.FileField(upload_to='agents/addhar_card_files/', null=True)
    pan_card_file = models.FileField(upload_to='agents/pan_card_files/', null=True)
    experience = models.CharField(max_length=100, null=True)
    is_active = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    is_rejected = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False)
    no_of_meetings = models.IntegerField(default=0)
    no_of_meetings_completed = models.IntegerField(default=0)
    no_of_sales = models.IntegerField(default=0)
    total_sales = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name if self.name else "Unnamed Agent" 
    
class AgentFamily(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent_user = models.ForeignKey(AgentUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()

    def __str__(self):
        return self.agent_user.name
    
class AgentCoorporate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent_user = models.ForeignKey(AgentUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()

    def __str__(self):
        return self.agent_user.name

class Meeting(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent_user = models.ForeignKey(AgentUser, on_delete=models.CASCADE)
    meeting_duration = models.DurationField(null=True)
    meeting_audio = models.FileField(upload_to='customer_support/meeting_audio/', null=True)
    meeting_image = models.FileField(upload_to='customer_support/meeting_image/', null=True)
    is_completed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True)
    duration = models.CharField(default='', max_length=100)

    def save(self, *args, **kwargs):
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            self.meeting_duration = delta  # Save the duration as a DurationField
            total_seconds = int(delta.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.duration = f"{hours}h {minutes}m {seconds}s"
        else:
            self.duration = ''  # Ensure duration is set to empty if end_time or start_time is not set
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Meeting"
        verbose_name_plural = "Meetings"


class DemoSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent_user = models.ForeignKey("AgentUser", on_delete=models.CASCADE)
    client_name = models.CharField(max_length=255)
    client_email = models.EmailField()
    client_phone = models.CharField(max_length=15)
    otp = models.CharField(max_length=6, null=True, blank=True)
    is_verified = models.BooleanField(default=False)
    demo_url = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expired_at = models.DateTimeField(null=True, blank=True)

    def expire_demo(self):
        self.expired_at = timezone.now()
        self.demo_url = None  # Remove access
        self.save()
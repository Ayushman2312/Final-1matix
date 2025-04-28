from django.db import models
import uuid
from agents.models import Policy

class SupportDepartment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
    
    
class SupportUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    photo = models.ImageField(upload_to='customersupport/photos/', null=True)
    name = models.CharField(max_length=100, null=True)
    support_department = models.ForeignKey(SupportDepartment, on_delete=models.CASCADE, null=True)
    support_user_passcode = models.CharField(unique=True, max_length=128, null=True)
    email = models.EmailField(unique=True, null=True)
    password = models.CharField(max_length=128, null=True)
    phone_number = models.CharField(max_length=15, null=True)
    pan_number = models.CharField(max_length=10, null=True)
    aadhar_number = models.CharField(max_length=12, null=True)
    address = models.TextField(null=True)
    dob = models.DateField(null=True)
    gender = models.CharField(max_length=10, null=True)
    salary = models.IntegerField(null=True)
    qualification = models.CharField(max_length=100, null=True)
    qualification_file = models.FileField(upload_to='customersupport/qualification_files/', null=True)
    bank_account_holder_name = models.CharField(max_length=100, null=True)
    bank_account_number = models.CharField(max_length=15, null=True)
    bank_name = models.CharField(max_length=100, null=True)
    branch_name = models.CharField(max_length=100, null=True)
    bank_ifsc_code = models.CharField(max_length=10, null=True)
    cancelled_cheque_file = models.FileField(upload_to='customersupport/cancelled_cheque_files/', null=True)
    offer_letter_file = models.FileField(upload_to='customersupport/offer_letter_files/', null=True)
    bank_statement_file = models.FileField(upload_to='customersupport/bank_statement_files/', null=True)
    increment_letter_file = models.FileField(upload_to='customersupport/increment_letter_files/', null=True)
    pay_slip_file = models.FileField(upload_to='customersupport/pay_slip_files/', null=True)
    experience_letter_file = models.FileField(upload_to='customersupport/experience_letter_files/', null=True)
    leave_letter_file = models.FileField(upload_to='customersupport/leave_letter_files/', null=True)
    addhar_card_file = models.FileField(upload_to='customersupport/addhar_card_files/', null=True)
    pan_card_file = models.FileField(upload_to='customersupport/pan_card_files/', null=True)
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
    terms_and_conditions = models.ForeignKey(Policy, on_delete=models.CASCADE, null=True)

    def __str__(self):
        return self.name if self.name else "Unnamed Agent"
    
class SupportFamily(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    support_user = models.ForeignKey(SupportUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()

    def __str__(self):
        return self.support_user.name
    
class SupportCoorporate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    support_user = models.ForeignKey(SupportUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15)
    address = models.TextField()

    def __str__(self):
        return self.support_user.name


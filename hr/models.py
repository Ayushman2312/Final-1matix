from django.db import models
import uuid
from django.utils import timezone
import json
from django.db.models.signals import pre_save
from django.dispatch import receiver
import logging
from User.models import User  # Import User model
# Create your models here.

logger = logging.getLogger(__name__)

class Company(models.Model):
    company_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_name = models.CharField(max_length=255,null=True,blank=True)
    company_email = models.EmailField(unique=True,null=True,blank=True)
    company_logo = models.ImageField(upload_to='company_logos/',null=True,blank=True)
    company_phone = models.CharField(max_length=255,null=True,blank=True)
    company_address = models.TextField(null=True,blank=True)
    company_identification_number = models.CharField(max_length=255,null=True,blank=True)
    company_gst_number = models.CharField(max_length=255,null=True,blank=True)
    company_state = models.CharField(max_length=255,null=True,blank=True)
    company_pincode = models.CharField(max_length=6,null=True,blank=True)
    company_created_at = models.DateTimeField(default=timezone.now)
    company_updated_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='companies')

    def __str__(self):
        return self.company_name

class Employee(models.Model):
    employee_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    number_of_days_attended = models.IntegerField(default=0)
    attendance_photo = models.ImageField(upload_to='attendance_photos/',null=True,blank=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    location = models.CharField(max_length=255,null=True,blank=True)
    employee_name = models.CharField(max_length=255)
    employee_email = models.EmailField(unique=True)
    password = models.CharField(max_length=255,null=True,blank=True)
    is_active = models.BooleanField(default=False)
    is_approved = models.BooleanField(default=False)
    attendance_verification = models.BooleanField(default=False)
    last_attendance_time = models.DateTimeField(null=True, blank=True)
    attendance_status = models.CharField(max_length=20, 
    default='not_marked')  # can be 'marked', 'unmarked', 'completed'
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='employees')

    def __str__(self):
        return self.employee_name


class Department(models.Model):
    department_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='departments')

    def __str__(self):
        return self.name

class Designation(models.Model):
    designation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='designations')

    def __str__(self):
        return self.name

class TandC(models.Model):
    tandc_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    description = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='terms_and_conditions')

    def __str__(self):
        return self.name

class Role(models.Model):
    role_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='roles')

    def __str__(self):
        return self.name

class OfferLetter(models.Model):
    offer_letter_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    content = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='offer_letters')

    def __str__(self):
        return self.name
    
class HiringAgreement(models.Model):
    hiring_agreement_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    content = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='hiring_agreements')

    def __str__(self):
        return self.name

class Handbook(models.Model):
    handbook_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    content = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='handbooks')

    def __str__(self):
        return self.name
    
class TrainingMaterial(models.Model):
    training_material_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    content = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='training_materials')

    def __str__(self):
        return self.name

class QRCode(models.Model):
    qr_code_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    location_and_coordinates = models.JSONField(null=True,blank=True)
    qr_code_image = models.ImageField(upload_to='qr_codes/',null=True,blank=True)
    secret_key = models.CharField(max_length=64, default=uuid.uuid4)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='qr_codes')

    def __str__(self):
        return self.company.company_name

class Device(models.Model):
    device_id = models.CharField(max_length=255, unique=True) 
    ip_address = models.GenericIPAddressField()                
    user = models.ForeignKey(Employee, on_delete=models.CASCADE,null=True,blank=True)                       
    platform = models.CharField(max_length=255)                
    created_at = models.DateTimeField(auto_now_add=True)       
    owner = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='devices')

    def __str__(self):
        return f"{self.device_id} - {self.ip_address}"

class Folder(models.Model):
    folder_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    logo = models.ImageField(upload_to='folder_logos/',null=True,blank=True)
    name = models.CharField(max_length=100,null=True,blank=True)
    description = models.TextField(null=True,blank=True)
    json_data = models.JSONField(null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='folders')

    def __str__(self):
        return self.name or str(self.folder_id)

class OnboardingInvitation(models.Model):
    INVITATION_STATUS = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
        ('rejected', 'Rejected'),
        ('accepted', 'Accepted'),
        ('need_discussion', 'Need Discussion'),
    )
    
    invitation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    email = models.EmailField()
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    designation = models.ForeignKey(Designation, on_delete=models.SET_NULL, null=True, blank=True)
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    offer_letter_template = models.ForeignKey(OfferLetter, on_delete=models.SET_NULL, null=True, blank=True)
    hiring_agreement_template = models.ForeignKey(HiringAgreement, on_delete=models.SET_NULL, null=True, blank=True)
    handbook_template = models.ForeignKey(Handbook, on_delete=models.SET_NULL, null=True, blank=True)
    hr_policies_template = models.ForeignKey(TandC, on_delete=models.SET_NULL, null=True, blank=True, related_name='hr_policies_invitations')
    training_material_template = models.ForeignKey(TrainingMaterial, on_delete=models.SET_NULL, null=True, blank=True)
    form_link = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=20, choices=INVITATION_STATUS, default='pending')
    policies = models.JSONField(null=True, blank=True)
    additional_documents = models.JSONField(null=True, blank=True)
    photo = models.ImageField(upload_to='employee_photos/', null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, null=True)
    discussion_message = models.TextField(blank=True, null=True)
    has_viewed_offer = models.BooleanField(default=False)
    is_form_completed = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='onboarding_invitations')
    
    def __str__(self):
        return f"{self.name} - {self.email}"

    class Meta:
        ordering = ['-created_at']
        
    def save(self, *args, **kwargs):
        """Ensure policies is properly serialized as JSON before saving"""
        # Make sure policies is a valid dictionary
        if self.policies is None:
            self.policies = {}
        # Handle string conversion if needed
        elif isinstance(self.policies, str):
            try:
                self.policies = json.loads(self.policies)
            except json.JSONDecodeError:
                self.policies = {}
                
        # Make sure policies is a dictionary
        if not isinstance(self.policies, dict):
            self.policies = {}
        
        # For completed forms, ensure we have a backup copy of the form data
        if self.is_form_completed and self.status == 'completed':
            # If form_data exists in policies, save a backup copy in the rejection_reason field
            # This adds redundancy in case of JSON serialization issues
            if 'form_data' in self.policies:
                # We'll use the rejection_reason field to store a compressed form data summary
                try:
                    # Create a summary of the form data
                    form_data_summary = {
                        'submission_time': timezone.now().isoformat(),
                        'field_count': len(self.policies['form_data']),
                        'has_structured_data': 'structured_data' in self.policies['form_data'],
                        'has_personal_info': 'personal_info' in self.policies['form_data'],
                        'has_employment_details': 'employment_details' in self.policies['form_data']
                    }
                    
                    # Store the summary as backup
                    if not self.rejection_reason:  # Only set if not already used
                        self.rejection_reason = f"FORM_DATA_BACKUP: {json.dumps(form_data_summary)}"
                except Exception as e:
                    logger.error(f"Error creating form data backup: {str(e)}", exc_info=True)
        
        # Call the original save method
        super().save(*args, **kwargs)
        
    def accept_invitation(self):
        """Mark invitation as accepted and update related fields"""
        self.status = 'accepted'
        self.accepted_at = timezone.now()
        self.save()
        return True
        
    def reject_invitation(self, reason=None):
        """Mark invitation as rejected with optional reason"""
        self.status = 'rejected'
        self.rejected_at = timezone.now()
        if reason:
            self.rejection_reason = reason
        self.save()
        return True

class EmployeeAttendance(models.Model):
    attendance_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey('employee.Employee', on_delete=models.CASCADE, related_name='attendances')
    check_in_time = models.DateTimeField(default=timezone.now)
    check_out_time = models.DateTimeField(null=True, blank=True)
    date = models.DateField(default=timezone.now)
    status = models.CharField(max_length=20, choices=[
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('leave', 'Leave'),
    ], default='present')
    notes = models.TextField(null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    device_info = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='employee_attendances')
    
    class Meta:
        unique_together = ['employee', 'date']
        ordering = ['-date', '-check_in_time']
    
    def __str__(self):
        return f"{self.employee.name} - {self.date} - {self.status}"

class LeaveApplication(models.Model):
    LEAVE_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ]
    
    LEAVE_TYPES = [
        ('casual', 'Casual Leave'),
        ('sick', 'Sick Leave'),
        ('annual', 'Annual Leave'),
        ('maternity', 'Maternity Leave'),
        ('paternity', 'Paternity Leave'),
        ('bereavement', 'Bereavement Leave'),
        ('unpaid', 'Unpaid Leave'),
        ('other', 'Other'),
    ]
    
    leave_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey('employee.Employee', on_delete=models.CASCADE, related_name='leave_applications')
    leave_type = models.CharField(max_length=20, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=LEAVE_STATUS, default='pending')
    document = models.FileField(upload_to='leave_documents/', null=True, blank=True)
    reviewed_by = models.ForeignKey('employee.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_leaves')
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='leave_applications')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.employee.name} - {self.leave_type} ({self.start_date} to {self.end_date})"
    
    @property
    def duration(self):
        """Calculate the number of days in the leave period"""
        return (self.end_date - self.start_date).days + 1

class ReimbursementRequest(models.Model):
    REQUEST_STATUS = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled'),
    ]
    
    EXPENSE_CATEGORIES = [
        ('travel', 'Travel'),
        ('meals', 'Meals & Entertainment'),
        ('office', 'Office Supplies'),
        ('equipment', 'Equipment'),
        ('software', 'Software & Subscriptions'),
        ('training', 'Training & Education'),
        ('medical', 'Medical Expenses'),
        ('other', 'Other'),
    ]
    
    reimbursement_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey('employee.Employee', on_delete=models.CASCADE, related_name='reimbursement_requests')
    expense_date = models.DateField()
    category = models.CharField(max_length=20, choices=EXPENSE_CATEGORIES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    description = models.TextField()
    receipt = models.FileField(upload_to='receipts/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=REQUEST_STATUS, default='pending')
    approved_by = models.ForeignKey('employee.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_reimbursements')
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(null=True, blank=True)
    payment_date = models.DateField(null=True, blank=True)
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='reimbursement_requests')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.employee.name} - {self.category} - {self.amount} {self.currency}"

class SalarySlip(models.Model):
    salary_slip_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey('employee.Employee', on_delete=models.CASCADE, related_name='salary_slips')
    month = models.IntegerField()  # 1-12 for Jan-Dec
    year = models.IntegerField()
    basic_salary = models.DecimalField(max_digits=10, decimal_places=2)
    allowances = models.JSONField(default=dict)  # For storing different allowances
    deductions = models.JSONField(default=dict)  # For storing different deductions
    net_salary = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    payment_method = models.CharField(max_length=50)
    payment_reference = models.CharField(max_length=100, null=True, blank=True)
    pdf_file = models.FileField(upload_to='salary_slips/', null=True, blank=True)
    is_paid = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='salary_slips')
    
    class Meta:
        unique_together = ['employee', 'month', 'year']
        ordering = ['-year', '-month']
    
    def __str__(self):
        return f"{self.employee.name} - {self.get_month_name()} {self.year}"
    
    def get_month_name(self):
        """Convert month number to name"""
        return {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }.get(self.month, '')
    
    @property
    def period_display(self):
        """Display the salary period in a readable format"""
        return f"{self.get_month_name()} {self.year}"

class Resignation(models.Model):
    RESIGNATION_STATUS = [
        ('pending', 'Pending'),
        ('acknowledged', 'Acknowledged'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
    ]
    
    resignation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    employee = models.ForeignKey('employee.Employee', on_delete=models.CASCADE, related_name='resignations')
    resignation_date = models.DateField(default=timezone.now)
    last_working_date = models.DateField()
    reason = models.TextField()
    additional_notes = models.TextField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=RESIGNATION_STATUS, default='pending')
    processed_by = models.ForeignKey('employee.Employee', on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_resignations')
    processed_at = models.DateTimeField(null=True, blank=True)
    feedback = models.TextField(null=True, blank=True)
    exit_interview_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='resignations')
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.employee.name} - {self.resignation_date}"
    
    @property
    def notice_period_days(self):
        """Calculate the notice period in days"""
        return (self.last_working_date - self.resignation_date).days

class EmployeeDocument(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='documents')
    document_type = models.CharField(max_length=100)
    document_name = models.CharField(max_length=255)
    notes = models.TextField(blank=True, null=True)
    file = models.FileField(upload_to='employee_documents/')
    file_size = models.CharField(max_length=20, blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='employee_documents')
    
    def __str__(self):
        return f"{self.employee.employee_name} - {self.document_name}"

class TrustedDevice(models.Model):
    device_id = models.UUIDField(default=uuid.uuid4, editable=False)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='trusted_devices')
    device_name = models.CharField(max_length=255, null=True, blank=True)
    browser_info = models.CharField(max_length=255, null=True, blank=True)
    platform = models.CharField(max_length=100, null=True, blank=True)
    last_used = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.employee.employee_name}'s device ({self.device_id})"
    
    class Meta:
        unique_together = ['device_id', 'employee']
        ordering = ['-last_used']

class LeaveType(models.Model):
    leave_type_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='leave_types')
    days_allowed = models.PositiveIntegerField(default=0)
    description = models.TextField(null=True, blank=True)
    color_code = models.CharField(max_length=20, default="#4F46E5", help_text="HEX color code for UI representation")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='leave_types')
    
    def __str__(self):
        return f"{self.name} ({self.days_allowed} days)"
    
    class Meta:
        ordering = ['name']

class Deduction(models.Model):
    deduction_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='deductions')
    description = models.TextField(null=True, blank=True)
    is_percentage = models.BooleanField(default=False, help_text="If True, the value is a percentage of salary; otherwise, it's a fixed amount")
    default_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_tax_exempt = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='deductions')
    
    def __str__(self):
        if self.is_percentage:
            return f"{self.name} ({self.default_value}%)"
        return f"{self.name} (₹{self.default_value})"
    
    class Meta:
        ordering = ['name']

class Allowance(models.Model):
    allowance_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='allowances')
    description = models.TextField(null=True, blank=True)
    is_percentage = models.BooleanField(default=False, help_text="If True, the value is a percentage of salary; otherwise, it's a fixed amount")
    default_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_taxable = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='allowances')
    
    def __str__(self):
        if self.is_percentage:
            return f"{self.name} ({self.default_value}%)"
        return f"{self.name} (₹{self.default_value})"
    
    class Meta:
        ordering = ['name']

# Add a pre-save signal handler for OnboardingInvitation
@receiver(pre_save, sender='hr.OnboardingInvitation')
def ensure_onboarding_data_saved(sender, instance, **kwargs):
    """Ensure form data is properly saved before saving the model to database"""
    # Skip if not a completed form
    if not instance.is_form_completed:
        return
    
    # Ensure policies field is initialized
    if instance.policies is None:
        instance.policies = {}
    elif isinstance(instance.policies, str):
        try:
            instance.policies = json.loads(instance.policies)
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse policies JSON for invitation {instance.invitation_id}")
            instance.policies = {}
    
    # Log form data size
    if 'form_data' in instance.policies:
        form_data_size = len(str(instance.policies['form_data']))
        logger.info(f"Saving form data ({form_data_size} bytes) for invitation {instance.invitation_id}")
    else:
        logger.warning(f"No form_data found in policies for completed invitation {instance.invitation_id}")

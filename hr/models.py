from django.db import models
import uuid
from django.utils import timezone
# Create your models here.

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
    attendance_verification = models.BooleanField(default=False)
    last_attendance_time = models.DateTimeField(null=True, blank=True)
    attendance_status = models.CharField(max_length=20, 
    default='not_marked')  # can be 'marked', 'unmarked', 'completed'


    def __str__(self):
        return self.employee_name


class Department(models.Model):
    department_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

class Designation(models.Model):
    designation_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

class TandC(models.Model):
    tandc_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    description = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

class Role(models.Model):
    role_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

class OfferLetter(models.Model):
    offer_letter_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    content = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name
    
class HiringAgreement(models.Model):
    hiring_agreement_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    content = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

class Handbook(models.Model):
    handbook_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    content = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name
    
class TrainingMaterial(models.Model):
    training_material_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100,null=True,blank=True)
    content = models.TextField(null=True,blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

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

    def __str__(self):
        return self.company.company_name

class Device(models.Model):
    device_id = models.CharField(max_length=255, unique=True) 
    ip_address = models.GenericIPAddressField()                
    user = models.ForeignKey(Employee, on_delete=models.CASCADE,null=True,blank=True)                       
    platform = models.CharField(max_length=255)                
    created_at = models.DateTimeField(auto_now_add=True)       

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

    def __str__(self):
        return self.name

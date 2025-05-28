from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(Employee)
admin.site.register(Department)
admin.site.register(Designation)
admin.site.register(TandC)
admin.site.register(Role)
admin.site.register(QRCode)
admin.site.register(OfferLetter)
admin.site.register(Device)
admin.site.register(Company)
admin.site.register(Folder)
admin.site.register(TrainingMaterial)
admin.site.register(HiringAgreement)
admin.site.register(Handbook)

@admin.register(OnboardingInvitation)
class OnboardingInvitationAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'department', 'designation', 'role', 'status', 'created_at', 'sent_at']
    list_filter = ['status', 'created_at', 'sent_at']
    search_fields = ['name', 'email', 'department', 'designation', 'role']
    readonly_fields = ['invitation_id', 'created_at', 'sent_at', 'completed_at', 'rejected_at']
    date_hierarchy = 'created_at'
    
@admin.register(EmployeeAttendance)
class EmployeeAttendanceAdmin(admin.ModelAdmin):
    list_display = ['employee', 'date', 'status', 'check_in_time', 'check_out_time']
    list_filter = ['status', 'date']
    search_fields = ['employee__name', 'employee__email']
    date_hierarchy = 'date'

@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'leave_type', 'start_date', 'end_date', 'status']
    list_filter = ['status', 'leave_type', 'start_date']
    search_fields = ['employee__name', 'employee__email', 'reason']
    date_hierarchy = 'start_date'

@admin.register(ReimbursementRequest)
class ReimbursementRequestAdmin(admin.ModelAdmin):
    list_display = ['employee', 'category', 'amount', 'expense_date', 'status']
    list_filter = ['status', 'category', 'expense_date']
    search_fields = ['employee__name', 'employee__email', 'description']
    date_hierarchy = 'expense_date'

@admin.register(SalarySlip)
class SalarySlipAdmin(admin.ModelAdmin):
    list_display = ['employee', 'get_month_name', 'year', 'basic_salary', 'net_salary', 'is_paid']
    list_filter = ['is_paid', 'year', 'month', 'payment_date']
    search_fields = ['employee__name', 'employee__email']
    date_hierarchy = 'payment_date'

@admin.register(Resignation)
class ResignationAdmin(admin.ModelAdmin):
    list_display = ['employee', 'resignation_date', 'last_working_date', 'status']
    list_filter = ['status', 'resignation_date', 'last_working_date']
    search_fields = ['employee__name', 'employee__email', 'reason']
    date_hierarchy = 'resignation_date'

@admin.register(EmployeeDocument)
class EmployeeDocumentAdmin(admin.ModelAdmin):
    list_display = ['employee', 'document_type', 'document_name', 'uploaded_at']
    list_filter = ['document_type', 'uploaded_at']
    search_fields = ['employee__name', 'employee__email', 'document_name', 'document_type']
    date_hierarchy = 'uploaded_at'

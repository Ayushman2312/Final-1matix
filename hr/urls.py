from django.urls import path

from employee.views import EmployeeReadView
from .views import *
from django.views.decorators.csrf import csrf_exempt

urlpatterns = [
    path('company/', CompanyView.as_view(), name='company'),
    path('creation/', CreationView.as_view(), name='creation'),
    path('onboarding/', OnboardingView.as_view(), name='employees'),
    path('attendance/', AttendanceView.as_view(), name='attendance'),
    path('qr-code/', csrf_exempt(QRCodeView.as_view()), name='qr-code'),
    path('get-qr-code/', QRCodeView.as_view(), name='get-qr-code'),
    path('generate-qr-code/', QRCodeView.as_view(), name='generate-qr-code'),
    path('qr-code-details/<uuid:qr_code_id>/', QRCodeDetailsView.as_view(), name='qr-code-details'),
    path('delete-qr-code/<uuid:qr_code_id>/', csrf_exempt(DeleteQRCodeView.as_view()), name='delete-qr-code'),
    path('mark-attendance/', EmployeeAttendanceView.as_view(), name='mark_attendance'),
    path('attend/<uuid:qr_code_id>/<str:secret_key>/', QRAttendanceRedirectView.as_view(), name='qr_attendance_redirect'),
    path('create-company/', CreateCompanyView.as_view(), name='create-company'),
    path('create-folder/', CreateFolderView.as_view(), name='create-folder'),
    path('folder/<str:folder_id>/', FolderView.as_view(), name='folder'),
    path('create-data/<str:folder_id>/', FolderView.as_view(), name='add-data'),
    path('update-data/<str:folder_id>/', FolderView.as_view(), name='update-data'),
    path('delete-data/<str:folder_id>/', FolderView.as_view(), name='delete-data'),
    path('onboarding/send-invitation/', OnboardingInvitationView.as_view(), name='send-onboarding-invitation'),
    path('onboarding/form/<str:token>/', OnboardingView.as_view(), name='onboarding-form'),
    path('onboarding/view-offer/<str:token>/', ViewOfferView.as_view(), name='view-offer'),
    path('onboarding/offer-response/<str:invitation_id>/', OfferResponseView.as_view(), name='offer-response'),
    path('onboarding/complete/<uuid:invitation_id>/', OnboardingInvitationStatusView.as_view(), name='complete-onboarding'),
    path('onboarding/reject/<uuid:invitation_id>/', OnboardingInvitationStatusView.as_view(), name='reject-onboarding'),
    path('onboarding/invitations/', OnboardingInvitationsListView.as_view(), name='invitations-list'),
    
    # New onboarding invitation API endpoints
    path('onboarding/invitation/<uuid:invitation_id>/', OnboardingInvitationDetailView.as_view(), name='invitation-detail'),
    path('onboarding/invitation/<uuid:invitation_id>/accept/', OnboardingInvitationAcceptView.as_view(), name='invitation-accept'),
    path('onboarding/invitation/<uuid:invitation_id>/reject/', OnboardingInvitationRejectView.as_view(), name='invitation-reject'),
    path('onboarding/invitation/<uuid:invitation_id>/delete/', OnboardingInvitationDeleteView.as_view(), name='invitation-delete'),
    
    # Form completion actions
    path('onboarding/form-action/<uuid:invitation_id>/', FormCompletedActionView.as_view(), name='form-action'),
    
    # Employee dashboard URLs
    path('employee/login/', HREmployeeLoginView.as_view(), name='hr_employee_login'),
    path('employee/dashboard/', EmployeeDashboardView.as_view(), name='employee_dashboard'),
    path('employee/profile/', EmployeeProfileView.as_view(), name='employee_profile'),
    path('employee/leave/', EmployeeLeaveView.as_view(), name='employee_leave'),
    path('employee/reimbursement/', EmployeeReimbursementView.as_view(), name='employee_reimbursement'),
    path('employee/salary-slips/', EmployeeSalarySlipsView.as_view(), name='employee_salary_slips'),
    path('employee/resignation/', EmployeeResignationView.as_view(), name='employee_resignation'),
    path('employee/documents/', EmployeeDocumentsView.as_view(), name='employee_documents'),
    path('employee/logout/', EmployeeLogoutView.as_view(), name='employee_logout'),
    
    # Employee API endpoints
    path('api/mark-attendance/', csrf_exempt(MarkAttendanceAPIView.as_view()), name='api_mark_attendance'),
    path('api/leave/apply/', csrf_exempt(LeaveApplicationAPIView.as_view()), name='api_apply_leave'),
    path('api/leave/cancel/<int:leave_id>/', csrf_exempt(CancelLeaveAPIView.as_view()), name='api_cancel_leave'),
    path('api/leave/<uuid:leave_id>/details/', csrf_exempt(LeaveDetailsAPIView.as_view()), name='api_leave_details'),
    path('api/reimbursement/submit/', csrf_exempt(ReimbursementRequestAPIView.as_view()), name='api_submit_reimbursement'),
    path('api/reimbursement/<uuid:reimbursement_id>/details/', csrf_exempt(ReimbursementDetailsAPIView.as_view()), name='api_reimbursement_details'),
    path('api/reimbursement/<uuid:reimbursement_id>/cancel/', csrf_exempt(ReimbursementCancelAPIView.as_view()), name='api_cancel_reimbursement'),
    path('api/salary-slip/<uuid:salary_slip_id>/details/', csrf_exempt(SalarySlipDetailsAPIView.as_view()), name='api_salary_slip_details'),
    path('api/resignation/submit/', csrf_exempt(ResignationAPIView.as_view()), name='api_submit_resignation'),
    path('api/resignation/cancel/', csrf_exempt(CancelResignationAPIView.as_view()), name='api_cancel_resignation'),
    path('api/profile/update/', csrf_exempt(UpdateProfileAPIView.as_view()), name='api_update_profile'),
    path('api/password/update/', csrf_exempt(UpdatePasswordAPIView.as_view()), name='api_update_password'),
    path('api/document/upload/', csrf_exempt(UploadDocumentAPIView.as_view()), name='api_upload_document'),
    path('api/document/delete/<int:document_id>/', csrf_exempt(DeleteDocumentAPIView.as_view()), name='api_delete_document'),
    path('api/employee/<uuid:employee_id>/toggle-status/', csrf_exempt(EmployeeStatusToggleAPIView.as_view()), name='api_toggle_employee_status'),
    
    # Template URLs
    path('departments/', DepartmentTemplateView.as_view(), name='department_template'),
    path('designations/', DesignationTemplateView.as_view(), name='designation_template'),
    path('roles/', RoleTemplateView.as_view(), name='role_template'),
    path('offerletters/', OfferLetterTemplateView.as_view(), name='offerletter_template'),
    path('offerletters/<uuid:template_id>/preview/', OfferLetterPreviewView.as_view(), name='offerletter_preview'),
    path('offerletters/<uuid:template_id>/update/', OfferLetterUpdateView.as_view(), name='offerletter_update'),
    path('offerletters/<uuid:template_id>/delete/', OfferLetterDeleteView.as_view(), name='offerletter_delete'),
    path('templates/offer-letter/preview/<uuid:template_id>/', OfferLetterPreviewView.as_view(), name='offerletter_template_preview'),
    path('policies/', PolicyTemplateView.as_view(), name='policy_template'),
    path('policies/<uuid:template_id>/preview/', PolicyPreviewView.as_view(), name='policy_preview'),
    path('policies/<uuid:template_id>/update/', PolicyUpdateView.as_view(), name='policy_update'),
    path('policies/<uuid:template_id>/delete/', PolicyDeleteView.as_view(), name='policy_delete'),
    path('hiring-agreements/', HiringAgreementTemplateView.as_view(), name='hiring_agreement_template'),
    path('hiring-agreements/<uuid:template_id>/preview/', HiringAgreementPreviewView.as_view(), name='hiring_agreement_preview'),
    path('hiring-agreements/<uuid:template_id>/update/', HiringAgreementUpdateView.as_view(), name='hiring_agreement_update'),
    path('hiring-agreements/<uuid:template_id>/delete/', HiringAgreementDeleteView.as_view(), name='hiring_agreement_delete'),
    path('handbooks/', HandbookTemplateView.as_view(), name='handbook_template'),
    path('handbooks/<uuid:template_id>/preview/', HandbookPreviewView.as_view(), name='handbook_preview'),
    path('handbooks/<uuid:template_id>/update/', HandbookUpdateView.as_view(), name='handbook_update'),
    path('handbooks/<uuid:template_id>/delete/', HandbookDeleteView.as_view(), name='handbook_delete'),
    path('training-materials/', TrainingMaterialTemplateView.as_view(), name='training_material_template'),
    path('training-materials/<uuid:template_id>/preview/', TrainingMaterialPreviewView.as_view(), name='training_material_preview'),
    path('training-materials/<uuid:template_id>/update/', TrainingMaterialUpdateView.as_view(), name='training_material_update'),
    path('training-materials/<uuid:template_id>/delete/', TrainingMaterialDeleteView.as_view(), name='training_material_delete'),
]


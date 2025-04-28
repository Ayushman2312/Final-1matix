from django.views.generic import TemplateView
from django.http import JsonResponse
from .models import *
from django.contrib.auth.hashers import make_password, check_password
import logging
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View
from masteradmin.models import *

logger = logging.getLogger(__name__)

# Create your views here.
class RegisterView(TemplateView):
    template_name = "employee/register.html"
    

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # policy_id = self.kwargs.get('policy_id')
        try:
            passcode = self.kwargs.get('passcode')
            employee = Employee.objects.filter(employee_passcode=passcode).first()
            if employee:
                if employee.name and employee.phone_number and employee.dob:
                    context['employee_error'] = 'Employee has already registered'
                    context['policies'] = employee.department.terms_and_conditions
                else:
                    context['email'] = employee.email
                    context['employee_passcode'] = passcode
                    context['employee_policy'] = employee.department.terms_and_conditions
            else:

                context['error'] = 'Employee not found'
        except Exception as e:


            context['error'] = str(e)
        return context

    def post(self, request, *args, **kwargs):
        try:
            passcode = self.kwargs.get('passcode')
            employee = Employee.objects.filter(employee_passcode=passcode).first()
            

            if not employee:
                return JsonResponse({'error': 'Employee not found'}, status=404)
            

            if employee.name and employee.phone_number and employee.dob:
                return JsonResponse({'error': 'Employee has already registered'}, status=400)


            # Update basic information
            employee.name = request.POST.get('name')
            employee.phone_number = request.POST.get('phone_number')
            employee.dob = request.POST.get('dob')
            employee.qualification = request.POST.get('qualification')
            employee.address = request.POST.get('address')
            employee.experience = request.POST.get('experience_type')
            employee.pan_number = request.POST.get('pan_number')

            employee.aadhar_number = request.POST.get('aadhar_number')



            # Update bank details
            employee.bank_account_holder_name = request.POST.get('bank_account_holder_name')
            employee.bank_account_number = request.POST.get('bank_account_number')
            employee.bank_name = request.POST.get('bank_name')
            employee.branch_name = request.POST.get('branch_name')
            employee.bank_ifsc_code = request.POST.get('bank_ifsc_code')


            # Handle file uploads
            file_fields = {
                'photo': 'photo',
                'qualification_file': 'qualification_file',
                'cancelled_cheque_file': 'cancelled_cheque_file',
                'offer_letter_file': 'offer_letter_file',
                'bank_statement_file': 'bank_statement_file',
                'increment_letter_file': 'increment_letter_file',
                'pay_slip_file': 'pay_slip_file',
                'experience_letter_file': 'experience_letter_file',
                'leave_letter_file': 'leave_letter_file',
                'addhar_card_file': 'addhar_card_file',
                'pan_card_file': 'pan_card_file'
            }


            for model_field, form_field in file_fields.items():
                if form_field in request.FILES:
                    setattr(employee, model_field, request.FILES[form_field])


            # Set password if provided
            if request.POST.get('password'):
                employee.password = make_password(request.POST.get('password'))

            # Save the employee
            employee.save()

            # Handle corporate references

            for i in range(1, 3):
                if all(request.POST.get(f'corporate_ref{i}_{field}') for field in ['name', 'email', 'phone', 'address']):
                    EmployeeCoorperate.objects.create(
                        support_user=employee,
                        name=request.POST.get(f'corporate_ref{i}_name'),
                        email=request.POST.get(f'corporate_ref{i}_email'),
                        phone_number=request.POST.get(f'corporate_ref{i}_phone'),
                        address=request.POST.get(f'corporate_ref{i}_address')
                    )


            # Handle family references
            for i in range(1, 3):
                if all(request.POST.get(f'family_ref{i}_{field}') for field in ['name', 'email', 'phone', 'address']):
                    EmployeeFamily.objects.create(
                        support_user=employee,
                        name=request.POST.get(f'family_ref{i}_name'),
                        email=request.POST.get(f'family_ref{i}_email'),

                        phone_number=request.POST.get(f'family_ref{i}_phone'),
                        address=request.POST.get(f'family_ref{i}_address')
                    )

            return redirect('employee_success', passcode=passcode)


        except Exception as e:
            logger.error(f"Error in registration: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error during registration: {str(e)}'
            }, status=500)
        
class EmployeeProfileView(TemplateView):
    template_name = "employee/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employee'] = Employee.objects.get(id=self.request.session['employee_id'])
        return context

def EmployeeLogin(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not email:
            messages.error(request, 'Please provide both email and password')
            return render(request, 'employee/employee_login.html')
            
        try:
            user = Employee.objects.get(email=email)
            password = check_password(password, user.password)
            if password:
                request.session['employee_id'] = str(user.id)
                return redirect('employee_profile')
            else:
                messages.error(request, 'Invalid password')
        except Employee.DoesNotExist:
            messages.error(request, 'Invalid credentials')
            
    return render(request, 'employee/employee_login.html')

class EmployeeReadView(View):
    def post(self, request, employee_id):
        try:
            notification = EmployeeNotification.objects.get(id=employee_id)
            notification.is_read = True
            notification.save()
            return JsonResponse({'status': 'success'})
        except EmployeeNotification.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)
        except Exception as e:
            logger.error(f"Error updating notification status: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)
        
class MasterNotificationsView(TemplateView):
    template_name = "employee/master_notifications.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee_user = self.request.session.get("employee_id")
        if employee_user:
            context['employee_notifications'] = EmployeeNotification.objects.filter(
                employee_user=employee_user, is_read=False
            ).select_related('employee_user')  # This optimizes the query
        else:
            context['employee_notifications'] = EmployeeNotification.objects.none()
        return context
    
class Success(TemplateView):
    template_name = "employee/success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        passcode = self.kwargs.get('passcode')
        try:
            employee = Employee.objects.get(employee_passcode=passcode)
            context['email'] = employee.email
            context['passcode'] = passcode
        except Employee.DoesNotExist:
            context['email'] = ''
            context['passcode'] = passcode
        return context
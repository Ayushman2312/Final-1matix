from django.views.generic import TemplateView, View
from hr.models import *
from django.http import JsonResponse
from io import BytesIO
from django.core.files.base import ContentFile
import qrcode
import json
from django.views import View
import json
import uuid
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
import random
from datetime import datetime, timedelta
from geopy.distance import geodesic
import base64
from django.shortcuts import redirect
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
import logging
from django.core.files.storage import default_storage
import os
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from hr.models import OnboardingInvitation
from django.contrib.auth.hashers import make_password
import string
from functools import wraps
from django.contrib import messages
from django.contrib.auth.hashers import check_password

logger = logging.getLogger(__name__)

def class_employee_login_required(cls):
    original_dispatch = cls.dispatch
    
    def new_dispatch(self, request, *args, **kwargs):
        employee_id = request.session.get('employee_id')
        if not employee_id:
            return redirect('hr_employee_login')
        return original_dispatch(self, request, *args, **kwargs)
    
    cls.dispatch = new_dispatch
    return cls

# Create your views here.
class CompanyView(TemplateView):
    template_name = 'hr_management/company.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['companies'] = Company.objects.all()
        context['qr_codes'] = QRCode.objects.all()
        return context

class CreationView(TemplateView):
    template_name = 'hr_management/creation.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.all()
        context['designations'] = Designation.objects.all()
        context['tandcs'] = TandC.objects.all()
        context['roles'] = Role.objects.all()
        context['folder_list'] = Folder.objects.all()
        context['offer_letters'] = OfferLetter.objects.all()
        return context

    def post(self, request, *args, **kwargs):
        try:
            # Handle department creation
            if 'department_name' in request.POST:
                Department.objects.create(name=request.POST['department_name'])
                return JsonResponse({'success': True})

            # Handle designation creation
            elif 'designation_name' in request.POST:
                Designation.objects.create(name=request.POST['designation_name'])
                return JsonResponse({'success': True})

            # Handle T&C creation
            elif 'tandc_name' in request.POST:
                TandC.objects.create(
                    name=request.POST['tandc_name'],
                    description=request.POST['tandc_description']
                )
                return JsonResponse({'success': True})

            # Handle role creation
            elif 'role_name' in request.POST:
                Role.objects.create(name=request.POST['role_name'])
                return JsonResponse({'success': True})

            # Handle offer letter creation
            elif 'offer_letter_name' in request.POST:
                OfferLetter.objects.create(
                    name=request.POST['offer_letter_name'],
                    content=request.POST['offer_letter_content']
                )
                return JsonResponse({'success': True})

            return JsonResponse({'error': 'Invalid form data'}, status=400)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class OnboardingView(TemplateView):
    template_name = 'hr_management/onboarding.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['companies'] = Company.objects.all()
        context['employees'] = Employee.objects.all()
        context['offer_letters'] = OfferLetter.objects.all()
        context['roles'] = Role.objects.all()
        context['departments'] = Department.objects.all()
        context['designations'] = Designation.objects.all()
        context['tandcs'] = TandC.objects.all()
        # context['policies'] = Policy.objects.all()
        context['hiring_agreements'] = HiringAgreement.objects.all()
        context['handbooks'] = Handbook.objects.all()
        context['training_materials'] = TrainingMaterial.objects.all()
        # If token is in kwargs, this is an onboarding form request
        token = kwargs.get('token')
        if token:
            # Try to find invitation by form link
            form_link = f"{self.request.scheme}://{self.request.get_host()}/hr_management/onboarding/form/{token}/"
            try:
                # Look for invitation with matching token in form_link
                invitations = OnboardingInvitation.objects.filter(form_link__contains=token)
                if invitations.exists():
                    invitation = invitations.first()
                    context['invitation'] = invitation
                    
                    # Check if the invitation has been completed (accepted)
                    if invitation.status == 'completed':
                        context['is_onboarding_form'] = True
                        # If using a different template for the form, set it here
                        self.template_name = 'hr_management/onboarding_form.html'
                    else:
                        # Redirect to view offer page if not accepted yet
                        context['redirect_to_offer'] = True
                        context['offer_token'] = token
            except Exception as e:
                logger.error(f"Error retrieving onboarding invitation: {str(e)}", exc_info=True)
        
        # Get all invitations for the "See Invites" tab
        context['invitations'] = OnboardingInvitation.objects.all().order_by('-created_at')
        
        return context
        
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        # Check if we need to redirect to the offer view page
        if context.get('redirect_to_offer'):
            token = context.get('offer_token')
            return redirect(f"/hr_management/onboarding/view-offer/{token}/")
            
        return self.render_to_response(context)
    
    def post(self, request, *args, **kwargs):
        """Handle form submission and create employee credentials"""
        try:
            # Get token from URL
            token = kwargs.get('token')
            if not token:
                return JsonResponse({'success': False, 'message': 'Invalid request'}, status=400)
                
            # Find invitation by token
            invitation = OnboardingInvitation.objects.get(form_link__contains=token)
            
            # Process form data
            # (Implement form processing logic here)
            
            # Mark form as completed
            invitation.is_form_completed = True
            invitation.status = 'completed'
            invitation.completed_at = timezone.now()
            invitation.save()
            
            return JsonResponse({
                'success': True, 
                'message': 'Form submitted successfully. Your application is pending review.'
            })
                
        except OnboardingInvitation.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Invalid invitation'}, status=404)
            
        except Exception as e:
            logger.error(f"Error processing form submission: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    def send_credentials_email(self, invitation, password):
        """Send email with login credentials to the employee"""
        company = invitation.company
        
        # Get site URL from settings or use a default
        site_url = getattr(settings, 'SITE_URL', "https://1matrix.io")
        
        # Prepare context data for the email template
        context = {
            'name': invitation.name,
            'email': invitation.email,
            'company_name': company.company_name,
            'department': invitation.department.name if invitation.department else 'Not specified',
            'designation': invitation.designation.name if invitation.designation else 'Not specified',
            'role': invitation.role.name if invitation.role else 'Not specified',
            'login_url': f"{site_url}/hr_management/employee/login/",
            'username': invitation.email,  # Email is used as username
            'password': password,
            'current_year': timezone.now().year,
        }
        
        # Add company logo if available
        if company.company_logo:
            context['company_logo'] = company.company_logo.url
        
        try:
            # Render email template with context
            html_content = render_to_string('hr_management/email_templates/acceptance_credentials.html', context)
            text_content = strip_tags(html_content)
            
            # Send email
            subject = f"Welcome to {company.company_name} - Your Login Credentials"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [invitation.email]
            
            send_mail(
                subject=subject,
                message=text_content,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_content,
                fail_silently=False,
            )
            
            logger.info(f"Credentials email sent to {invitation.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending credentials email: {str(e)}", exc_info=True)
            return False

class AttendanceView(TemplateView):
    template_name = 'hr_management/attendance.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['employees'] = Employee.objects.all()
        context['qr_codes'] = QRCode.objects.all()
        context['companies'] = Company.objects.all()
        return context
    
class CreateCompanyView(TemplateView):
    template_name = 'hr_management/create_hr_company.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        logger.debug("Rendering create company form")
        return context

    def post(self, request, *args, **kwargs):
        logger.debug("Processing company creation request")
        try:
            # Get form data
            company_name = request.POST.get('company_name')
            company_logo = request.FILES.get('company_logo')
            company_gst_number = request.POST.get('company_gst_number')
            company_mobile_number = request.POST.get('company_mobile_number')
            company_email = request.POST.get('company_email')
            company_address = request.POST.get('company_address')
            company_identification_number = request.POST.get('company_identification_number')
            company_state = request.POST.get('company_state')
            company_pincode = request.POST.get('company_pincode')

            logger.debug(f"Received company data: name={company_name}, email={company_email}, state={company_state}, pincode={company_pincode}")
            logger.debug(f"Files received: logo={bool(company_logo)}")

            # Create company
            logger.debug("Creating company record")
            company = Company.objects.create(
                # user=request.user,
                company_name=company_name,
                company_logo=company_logo,
                company_gst_number=company_gst_number,
                company_phone=company_mobile_number,
                company_pincode=company_pincode,
                company_email=company_email,
                company_address=company_address,
                company_identification_number=company_identification_number,
                company_state=company_state
            )

            logger.info(f"Company '{company_name}' created successfully")
            return JsonResponse({
                'success': True,
                'redirect_url': '/hr_management/company/'
            })

        except Exception as e:
            logger.error(f"Error creating company: {str(e)}", exc_info=True)
            return JsonResponse({
                'error': str(e)
            }, status=400)
    
class QRCodeView(View):
    def post(self, request):
        try:
            # Parse JSON data if content type is application/json
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                # Handle form data if not JSON
                data = request.POST

            company_id = data.get('company')
            locations = data.get('locations', [])

            if not company_id or not locations:
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required data'
                }, status=400)

            # Get company instance
            company = Company.objects.get(company_id=company_id)
            
            created_qr_codes = []

            for location in locations:
                # Handle both dictionary and string inputs
                location_name = location.get('name') if isinstance(location, dict) else None
                coordinates = location.get('coordinates') if isinstance(location, dict) else None

                if not location_name or not coordinates:
                    continue

                # Generate QR code and save it
                qr_code_id = uuid.uuid4()
                secret_key = str(uuid.uuid4())

                qr_code = QRCode.objects.create(
                    qr_code_id=qr_code_id,
                    company=company,
                    location_and_coordinates={
                        'location_name': location_name,
                        'coordinates': coordinates
                    },
                    secret_key=secret_key,
                )

                # Create QR code data
                qr_data = {
                    'qr_code_id': str(qr_code.qr_code_id),
                    'company_id': str(company.company_id),
                    'company_name': company.company_name,
                    'location_data': {
                        'name': location_name,
                        'coordinates': coordinates
                    },
                    'secret_key': secret_key,
                    'created_at': qr_code.created_at.isoformat(),
                    'timestamp': timezone.now().isoformat()
                }

                # Generate and save QR code image
                qr = qrcode.QRCode(
                    version=1,
                    error_correction=qrcode.constants.ERROR_CORRECT_H,
                    box_size=10,
                    border=4,
                )
                qr.add_data(json.dumps(qr_data))
                qr.make(fit=True)
                qr_image = qr.make_image(fill_color="black", back_color="white")

                # Save QR code image
                buffer = BytesIO()
                qr_image.save(buffer, format='PNG')
                buffer.seek(0)
                
                filename = f'qr_code_{company.company_name}_{location_name}_{qr_code_id}.png'
                qr_code.qr_code_image.save(filename, ContentFile(buffer.getvalue()), save=True)

                created_qr_codes.append({
                    'id': str(qr_code.qr_code_id),
                    'location': location_name,
                    'image_url': qr_code.qr_code_image.url
                })

            return JsonResponse({
                'success': True,
                'message': 'QR Codes generated successfully',
                'qr_codes': created_qr_codes
            })

        except Company.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Company not found'
            }, status=404)
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class EmployeeAttendanceView(TemplateView):
    template_name = 'hr_management/mark_attendance.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            action = data.get('action')
            
            if action == 'send_otp':
                return self.send_otp(request, data)
            elif action == 'verify_otp':
                return self.verify_otp(request, data)
            elif action == 'upload_photo':
                return self.upload_photo(request, data)
            elif action == 'mark_attendance':
                return self.mark_attendance(request, data)
            
            return JsonResponse({'error': 'Invalid action'}, status=400)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)

    def send_otp(self, request, data):
        try:
            email = data.get('email')
            
            if not email:
                return JsonResponse({'success': False, 'error': 'Email is required'}, status=400)

            # Add debug logging
            print(f"Attempting to send OTP to email: {email}")

            # Don't modify this line - it's using the hr.models.Employee
            employee = Employee.objects.filter(employee_email=email).first()
            if not employee:
                return JsonResponse({'success': False, 'error': 'Employee not found'}, status=404)

            otp = ''.join(random.choices('0123456789', k=6))
            request.session['attendance_otp'] = {
                'code': otp,
                'email': email,
                'timestamp': timezone.now().isoformat()
            }

            try:
                # Add more descriptive email subject and body
                subject = f'{employee.company.company_name} - Attendance OTP'
                message = (
                    f'Hello {employee.name},\n\n'
                    f'Your OTP for attendance verification is: {otp}\n'
                    f'This OTP will expire in 5 minutes.\n\n'
                    f'If you did not request this OTP, please ignore this email.'
                )
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [email],
                    fail_silently=False,
                )
                print(f"OTP sent successfully to {email}")
                return JsonResponse({'success': True, 'message': 'OTP sent successfully'})
            except Exception as e:
                print(f"Failed to send OTP: {str(e)}")
                return JsonResponse({
                    'success': False, 
                    'error': f'Failed to send OTP email: {str(e)}'
                }, status=500)

        except Exception as e:
            print(f"Error in send_otp: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def verify_otp(self, request, data):
        try:
            entered_otp = data.get('otp')
            email = data.get('email')

            stored_otp = request.session.get('attendance_otp', {})
            
            if not stored_otp or stored_otp['email'] != email:
                return JsonResponse({'success': False, 'error': 'Invalid session'}, status=400)

            otp_timestamp = datetime.fromisoformat(stored_otp['timestamp'])
            if timezone.now() - otp_timestamp > timedelta(minutes=5):
                return JsonResponse({'success': False, 'error': 'OTP expired'}, status=400)

            if entered_otp != stored_otp['code']:
                return JsonResponse({'success': False, 'error': 'Invalid OTP'}, status=400)

            device_id = str(uuid.uuid4())
            return JsonResponse({
                'success': True,
                'message': 'OTP verified successfully',
                'device_id': device_id
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def upload_photo(self, request, data):
        try:
            print(f"Starting photo upload for request: {request}")
            photo_data = data.get('attendance_image')  # From frontend
            device_id = data.get('device_id')
            email = data.get('email') or request.session.get('attendance_otp', {}).get('email')  # Get email from request or session

            if not photo_data or not device_id or not email:
                print(f"Missing data - photo_data: {bool(photo_data)}, device_id: {bool(device_id)}, email: {bool(email)}")
                return JsonResponse({'success': False, 'error': 'Missing required data'}, status=400)

            print(f"Processing photo for device ID: {device_id} and email: {email}")
            
            # Handle base64 data with or without prefix
            if 'base64,' in photo_data:
                format, imgstr = photo_data.split('base64,')
                ext = format.split('/')[-1].split(';')[0]
            else:
                imgstr = photo_data
                ext = 'jpg'

            # Clean base64 string
            imgstr = imgstr.strip()
            
            try:
                # Convert base64 to file
                photo = ContentFile(base64.b64decode(imgstr), name=f'attendance_{device_id}.{ext}')
                
                # Save to Employee model using the correct field name
                # Don't modify this line - it's using the hr.models.Employee
                employee = Employee.objects.get(employee_email=email)
                employee.attendance_photo = photo  # Using attendance_photo to match model field
                employee.save()
                
                print(f"Successfully saved attendance photo for employee: {employee.email}")
                
                return JsonResponse({
                    'success': True, 
                    'message': 'Photo uploaded successfully',
                    'photo_url': employee.attendance_photo.url if employee.attendance_photo else None
                })
                
            except Employee.DoesNotExist:
                print(f"Employee not found with email: {email}")
                return JsonResponse({'success': False, 'error': 'Employee not found'}, status=404)
            except Exception as e:
                print(f"Error processing photo data: {str(e)}")
                return JsonResponse({'success': False, 'error': 'Invalid photo data format'}, status=400)

        except Exception as e:
            print(f"Error uploading photo: {str(e)}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    def mark_attendance(self, request, data):
        try:
            qr_data = data.get('qr_data')
            current_location = data.get('location')
            device_id = data.get('device_id')
            email = data.get('email')

            if not all([qr_data, current_location, device_id, email]):
                return JsonResponse({'success': False, 'error': 'Missing required data'}, status=400)

            # Get employee and verify QR code
            try:
                # Don't modify this line - it's using the hr.models.Employee
                employee = Employee.objects.get(employee_email=email)
                qr_code = QRCode.objects.get(qr_code_id=qr_data['qr_code_id'])
            except (Employee.DoesNotExist, QRCode.DoesNotExist):
                return JsonResponse({'success': False, 'error': 'Invalid employee or QR code'}, status=400)

            # Check if attendance was marked today
            now = timezone.now()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            
            if employee.attendance_status == 'completed':
                return JsonResponse({
                    'success': False,
                    'error': 'You have already completed attendance for today'
                }, status=400)

            # If last attendance was marked within 15 minutes
            if (employee.last_attendance_time and 
                employee.attendance_status == 'marked' and 
                (now - employee.last_attendance_time).total_seconds() < 900):  # 15 minutes = 900 seconds
                return JsonResponse({
                    'success': False,
                    'error': 'You have already marked attendance. Please wait 15 minutes before unmarking.'
                }, status=400)

            # Verify location and other checks (keeping existing code)
            qr_location_data = qr_code.location_and_coordinates
            qr_location_name = qr_location_data['location_name']
            qr_coordinates = qr_location_data['coordinates']

            if current_location['name'] != qr_location_name:
                return JsonResponse({
                    'success': False, 
                    'error': 'Location mismatch. Please ensure you are at the correct location.'
                }, status=400)

            current_coords = (current_location['latitude'], current_location['longitude'])
            qr_coords = tuple(map(float, qr_coordinates.split(',')))
            distance = geodesic(current_coords, qr_coords).meters
            print(distance)
            if distance > 15:  # 10 meters radius check
                return JsonResponse({
                    'success': False, 
                    'error': 'You are not within the allowed range'
                }, status=400)

            # Update attendance based on current status
            if employee.attendance_status == 'not_marked':
                employee.number_of_days_attended += 1
                employee.attendance_status = 'marked'
                message = 'Attendance marked successfully!'
            elif employee.attendance_status == 'marked':
                employee.number_of_days_attended -= 1
                employee.attendance_status = 'completed'
                message = 'Attendance unmarked successfully. You cannot mark attendance again today.'

            employee.last_attendance_time = now
            employee.save()

            return JsonResponse({
                'success': True,
                'message': message,
                'status': employee.attendance_status
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

            # Mark Attendance Flow:
            # 1. User scans QR code at their work location which contains:
            #    - Location name and coordinates
            #    - Company details
            #    - QR code creation timestamp and validity
            
            # 2. Frontend collects:
            #    - User's email
            #    - Current GPS coordinates
            #    - Device ID
            #    - QR code data
            
            # 3. Backend validation:
            #    - Verifies employee exists and belongs to company
            #    - Checks if employee already marked attendance in last 15 mins
            #    - Validates QR code location matches current location name
            #    - Ensures user is within 10m radius of QR code coordinates
            
            # 4. Attendance marking logic:
            #    - If status = 'not_marked': 
            #      * Increments days attended
            #      * Sets status to 'marked'
            #      * Returns success with "Attendance marked" message
            
            #    - If status = 'marked':
            #      * Decrements days attended  
            #      * Sets status to 'completed'
            #      * Returns success with "Attendance unmarked" message
            
            # 5. Updates employee record with:
            #    - New attendance status
            #    - Last attendance timestamp
            #    - Number of days attended


class CreateFolderView(View):
    def post(self, request, *args, **kwargs):
        try:
            # Get form data
            name = request.POST.get('folderTitle', '').strip()
            description = request.POST.get('folderDescription', '').strip()
            
            # Validate input
            if not name:
                return JsonResponse({'success': False, 'error': 'Folder name is required'})
            
            # Generate unique folder ID
            folder_id = str(uuid.uuid4())
            
            # Handle file upload
            logo = request.FILES.get('folderLogo')
            logo_path = None
            
            if logo:
                try:
                    # Validate file type
                    if not logo.content_type.startswith('image/'):
                        return JsonResponse({
                            'success': False, 
                            'error': 'Invalid file type. Please upload an image.'
                        })

                    # Generate unique filename
                    file_ext = os.path.splitext(logo.name)[1]
                    unique_filename = f"folder_logos/{folder_id}{file_ext}"
                    
                    # Save file using default storage
                    logo_path = default_storage.save(
                        unique_filename,
                        ContentFile(logo.read())
                    )
                except Exception as e:
                    logger.error(f"Error processing logo: {str(e)}")
                    return JsonResponse({
                        'success': False,
                        'error': f'Error processing logo: {str(e)}'
                    })

            try:
                # Create folder object
                folder = Folder.objects.create(
                    folder_id=folder_id,
                    name=name,
                    description=description,
                    logo=logo_path,
                    created_at=timezone.now()
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Folder created successfully',
                    'folder_id': folder.folder_id,
                    'name': folder.name,
                    'description': folder.description,
                    'logo_url': folder.logo.url if folder.logo else None
                })
                
            except Exception as e:
                # Clean up uploaded file if folder creation fails
                if logo_path:
                    default_storage.delete(logo_path)
                logger.error(f"Error creating folder: {str(e)}")
                raise e

        except Exception as e:
            logger.error(f"Error in CreateFolderView: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Error creating folder: {str(e)}'
            })

    def get(self, request, *args, **kwargs):
        try:
            folders = Folder.objects.all().order_by('-created_at')
            context = {
                'folders': folders,
                'app_name': 'Folders'
            }
            return render(request, 'hr_management/creation.html', context)
        except Exception as e:
            logger.error(f"Error in get folders: {str(e)}")
            return render(request, 'hr_management/creation.html', {'error': str(e)})
        
        
class FolderView(TemplateView):
    template_name = 'hr_management/folder.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        folder_id = kwargs.get('folder_id')
        folder = Folder.objects.get(folder_id=folder_id)
        context['app_name'] = folder.name
        context['folder'] = folder
        return context

    def post(self, request, *args, **kwargs):
        try:
            folder_id = kwargs.get('folder_id')
            folder = Folder.objects.get(folder_id=folder_id)

            data = json.loads(request.body)
            title = data.get('title')
            content = data.get('content')

            if not title or not content:
                return JsonResponse({
                    'success': False,
                    'error': 'Title and content are required'
                }, status=400)

            # Initialize json_data if None
            if folder.json_data is None:
                folder.json_data = {}

            # Add new key-value pair
            folder.json_data[title] = content
            folder.save()

            return JsonResponse({
                'success': True,
                'message': 'Data added successfully',
                'title': title,
                'content': content
            })

        except Folder.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Folder not found'
            }, status=404)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False, 
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error adding folder data: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Error adding data: {str(e)}'
            }, status=500)

    def delete(self, request, *args, **kwargs):
        try:
            folder_id = kwargs.get('folder_id')
            folder = Folder.objects.get(folder_id=folder_id)

            data = json.loads(request.body)
            title = data.get('title')

            if not title:
                return JsonResponse({
                    'success': False,
                    'error': 'Title is required for deletion'
                }, status=400)

            if folder.json_data and title in folder.json_data:
                del folder.json_data[title]
                folder.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Data deleted successfully'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Title not found in folder data'
                }, status=404)

        except Folder.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Folder not found'
            }, status=404)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error deleting folder data: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Error deleting data: {str(e)}'
            }, status=500)

    def put(self, request, *args, **kwargs):
        try:
            folder_id = kwargs.get('folder_id')
            folder = Folder.objects.get(folder_id=folder_id)

            data = json.loads(request.body)
            original_title = data.get('originalTitle')
            new_title = data.get('newTitle')
            new_content = data.get('newContent')

            if not original_title or not new_title or not new_content:
                return JsonResponse({
                    'success': False,
                    'error': 'Original title, new title and new content are required'
                }, status=400)

            if folder.json_data and original_title in folder.json_data:
                # Delete old key and add new key-value pair
                del folder.json_data[original_title]
                folder.json_data[new_title] = new_content
                folder.save()

                return JsonResponse({
                    'success': True,
                    'message': 'Data updated successfully',
                    'title': new_title,
                    'content': new_content
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Title not found in folder data'
                }, status=404)

        except Folder.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Folder not found'
            }, status=404)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data'
            }, status=400)
        except Exception as e:
            logger.error(f"Error updating folder data: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': f'Error updating data: {str(e)}'
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class OnboardingInvitationView(View):
    def post(self, request, *args, **kwargs):
        try:
            # Handle form data with potential file uploads
            if 'multipart/form-data' in request.content_type:
                # Get form data
                company_id = request.POST.get('company')
                name = request.POST.get('name')
                email = request.POST.get('email')
                department_id = request.POST.get('department')
                designation_id = request.POST.get('designation')
                role_id = request.POST.get('role')
                offer_letter_id = request.POST.get('offer_letter')
                policies_json = request.POST.get('policies')
                
                # Parse policies JSON if present
                policies = json.loads(policies_json) if policies_json else []
                
                # Get photo if uploaded
                photo = request.FILES.get('photo')
            # Parse the JSON data if content type is application/json
            elif request.content_type == 'application/json':
                data = json.loads(request.body)
                
                # Get form data
                company_id = data.get('company')
                name = data.get('name')
                email = data.get('email')
                department_id = data.get('department')
                designation_id = data.get('designation')
                role_id = data.get('role')
                offer_letter_id = data.get('offer_letter')
                policies = data.get('policies', [])
                
                # No photo in JSON request
                photo = None
            else:
                # Regular form submission
                data = request.POST
                
                # Get form data
                company_id = data.get('company')
                name = data.get('name')
                email = data.get('email')
                department_id = data.get('department')
                designation_id = data.get('designation')
                role_id = data.get('role')
                offer_letter_id = data.get('offer_letter')
                policies = data.get('policies', [])
                
                # No photo in regular form post
                photo = None
            
            # Validate required fields
            if not company_id or not name or not email:
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required fields: company, name, email'
                }, status=400)
            
            # Get company instance
            try:
                company = Company.objects.get(company_id=company_id)
            except Company.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Company not found'
                }, status=404)
            
            # Get department, designation, role instances if provided
            department = None
            designation = None
            role = None
            
            if department_id:
                try:
                    department = Department.objects.get(department_id=department_id)
                except Department.DoesNotExist:
                    logger.warning(f"Department with ID {department_id} not found")
            
            if designation_id:
                try:
                    designation = Designation.objects.get(designation_id=designation_id)
                except Designation.DoesNotExist:
                    logger.warning(f"Designation with ID {designation_id} not found")
            
            if role_id:
                try:
                    role = Role.objects.get(role_id=role_id)
                except Role.DoesNotExist:
                    logger.warning(f"Role with ID {role_id} not found")
            
            # Get offer letter instance if provided
            offer_letter = None
            if offer_letter_id:
                try:
                    offer_letter = OfferLetter.objects.get(offer_letter_id=offer_letter_id)
                except OfferLetter.DoesNotExist:
                    logger.warning(f"Offer letter with ID {offer_letter_id} not found")
            
            # Generate a unique form link with token
            token = str(uuid.uuid4())
            form_link = f"{request.scheme}://{request.get_host()}/hr_management/onboarding/form/{token}/"
            
            # Create onboarding invitation
            invitation = OnboardingInvitation.objects.create(
                company=company,
                name=name,
                email=email,
                department=department,
                designation=designation,
                role=role,
                offer_letter_template=offer_letter,
                form_link=form_link,
                policies=policies,
                photo=photo,
            )
            
            # Send email
            logger.info(f"Attempting to send invitation email to {email}")
            email_sent = self.send_invitation_email(invitation)
            
            # Update invitation status
            if email_sent:
                invitation.status = 'sent'
                invitation.sent_at = timezone.now()
                invitation.save()
                logger.info(f"Invitation status updated to 'sent' for {email}")
                
                return JsonResponse({
                    'success': True,
                    'message': 'Invitation sent successfully',
                    'invitation_id': str(invitation.invitation_id)
                })
            else:
                # Email failed, but invitation was created
                logger.warning(f"Invitation created but email failed for {email}")
                return JsonResponse({
                    'success': True,
                    'warning': 'Invitation created but email could not be sent',
                    'invitation_id': str(invitation.invitation_id)
                })
            
        except Exception as e:
            logger.error(f"Error sending onboarding invitation: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            }, status=500)
    
    def send_invitation_email(self, invitation):
        """Send onboarding invitation email"""
        try:
            company = invitation.company
            
            # Get site URL from settings or use a default
            site_url = getattr(settings, 'SITE_URL', "https://1matrix.io")
            
            # Generate a random password for the user
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            
            # Extract token from form_link
            token = invitation.form_link.split('/')[-2]
            
            # Create view offer link
            view_offer_link = f"{site_url}/hr_management/onboarding/view-offer/{token}/"
            
            # Prepare context data for the email template
            context = {
                'name': invitation.name,
                'email': invitation.email,
                'company_name': company.company_name,
                'department': invitation.department.name if invitation.department else 'Not specified',
                'designation': invitation.designation.name if invitation.designation else 'Not specified',
                'role': invitation.role.name if invitation.role else 'Not specified',
                'login_url': f"{site_url}/hr_management/employee/login/",
                'form_link': invitation.form_link,
                'view_offer_link': view_offer_link,
                'username': invitation.email,  # Email is used as username
                'password': password,
                'current_year': timezone.now().year,
            }
            
            # Add company logo if available
            if company.company_logo:
                context['company_logo'] = company.company_logo.url
            
            # Log that we're about to render the template
            logger.info(f"Preparing to send invitation email to {invitation.email}")
            
            # Check if template exists
            template_path = 'hr_management/email_templates/onboarding_invitation.html'
            
            # Render email template with context
            try:
                html_content = render_to_string(template_path, context)
                text_content = strip_tags(html_content)
                
                # Log email content for debugging
                logger.debug(f"Email HTML content: {html_content[:100]}...")
                
                # Send email
                subject = f"Welcome to {company.company_name} - Onboarding Invitation"
                from_email = settings.DEFAULT_FROM_EMAIL
                
                if not from_email:
                    logger.error("DEFAULT_FROM_EMAIL is not set in settings")
                    from_email = "noreply@1matrix.io"
                
                recipient_list = [invitation.email]
                
                logger.info(f"Sending email to {invitation.email} with subject '{subject}' from {from_email}")
                
                send_mail(
                    subject=subject,
                    message=text_content,
                    from_email=from_email,
                    recipient_list=recipient_list,
                    html_message=html_content,
                    fail_silently=False,
                )
                
                logger.info(f"Onboarding invitation email sent successfully to {invitation.email}")
                return True
                
            except Exception as template_error:
                logger.error(f"Error rendering or sending email template: {str(template_error)}", exc_info=True)
                return False
                
        except Exception as e:
            logger.error(f"Error in send_invitation_email: {str(e)}", exc_info=True)
            return False

@method_decorator(csrf_exempt, name='dispatch')
class OnboardingInvitationStatusView(View):
    def post(self, request, invitation_id, *args, **kwargs):
        """Update invitation status"""
        try:
            invitation = OnboardingInvitation.objects.get(invitation_id=invitation_id)
            
            # Parse request data
            try:
                data = json.loads(request.body)
                status = data.get('status')
                completion_data = data.get('completion_data', {})
            except (ValueError, json.JSONDecodeError):
                # Try to get from POST data if not JSON
                status = request.POST.get('status')
                completion_data = {}
            
            # Check status
            if status not in ['completed', 'rejected', 'accepted']:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid status provided'
                }, status=400)
            
            # Update invitation
            invitation.status = status
            
            # Set appropriate timestamp based on status
            if status == 'completed':
                invitation.completed_at = timezone.now()
                invitation.is_form_completed = True
            elif status == 'rejected':
                invitation.rejected_at = timezone.now()
            elif status == 'accepted':
                invitation.accepted_at = timezone.now()
            
            # Handle additional data if provided
            if status == 'rejected' and completion_data.get('rejection_reason'):
                invitation.rejection_reason = completion_data.get('rejection_reason')
            
            # Save the invitation
            invitation.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Invitation status updated to {status}'
            })
            
        except OnboardingInvitation.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invitation not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error updating invitation status: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

class DepartmentTemplateView(TemplateView):
    template_name = 'hr_management/templates/department.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['departments'] = Department.objects.all()
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            department_name = request.POST.get('department_name')
            if department_name:
                Department.objects.create(name=department_name)
                return JsonResponse({'success': True})
            return JsonResponse({'error': 'Department name is required'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class DesignationTemplateView(TemplateView):
    template_name = 'hr_management/templates/designation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['designations'] = Designation.objects.all()
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            designation_name = request.POST.get('designation_name')
            if designation_name:
                Designation.objects.create(name=designation_name)
                return JsonResponse({'success': True})
            return JsonResponse({'error': 'Designation name is required'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class RoleTemplateView(TemplateView):
    template_name = 'hr_management/templates/role.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = Role.objects.all()
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            role_name = request.POST.get('role_name')
            if role_name:
                Role.objects.create(name=role_name)
                return JsonResponse({'success': True})
            return JsonResponse({'error': 'Role name is required'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class OfferLetterTemplateView(TemplateView):
    template_name = 'hr_management/templates/offerletter.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['offerletters'] = OfferLetter.objects.all()
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            name = request.POST.get('offer_letter_name')
            content = request.POST.get('offer_letter_content')
            if name and content:
                OfferLetter.objects.create(name=name, content=content)
                return JsonResponse({'success': True})
            return JsonResponse({'error': 'Name and content are required'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class PolicyTemplateView(TemplateView):
    template_name = 'hr_management/templates/policy.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['policies'] = TandC.objects.all()
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            name = request.POST.get('policy_name')
            description = request.POST.get('policy_description')
            if name and description:
                TandC.objects.create(name=name, description=description)
                return JsonResponse({'success': True})
            return JsonResponse({'error': 'Name and description are required'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class HiringAgreementTemplateView(TemplateView):
    template_name = 'hr_management/templates/hiring_agreement.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['agreements'] = HiringAgreement.objects.all()
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            name = request.POST.get('agreement_name')
            content = request.POST.get('agreement_content')
            if name and content:
                HiringAgreement.objects.create(name=name, content=content)
                return JsonResponse({'success': True})
            return JsonResponse({'error': 'Name and content are required'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class HandbookTemplateView(TemplateView):
    template_name = 'hr_management/templates/handbook.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['handbooks'] = Handbook.objects.all()
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            name = request.POST.get('handbook_name')
            content = request.POST.get('handbook_content')
            if name and content:
                Handbook.objects.create(name=name, content=content)
                return JsonResponse({'success': True})
            return JsonResponse({'error': 'Name and content are required'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class TrainingMaterialTemplateView(TemplateView):
    template_name = 'hr_management/templates/training_material.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['materials'] = TrainingMaterial.objects.all()
        return context
    
    def post(self, request, *args, **kwargs):
        try:
            name = request.POST.get('material_name')
            content = request.POST.get('material_content')
            if name and content:
                TrainingMaterial.objects.create(name=name, content=content)
                return JsonResponse({'success': True})
            return JsonResponse({'error': 'Name and content are required'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

class OfferLetterPreviewView(View):
    def get(self, request, template_id):
        try:
            template = OfferLetter.objects.get(offer_letter_id=template_id)
            return JsonResponse({
                'success': True,
                'content': template.content
            })
        except OfferLetter.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Template not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

class HiringAgreementPreviewView(View):
    def get(self, request, template_id):
        try:
            template = HiringAgreement.objects.get(hiring_agreement_id=template_id)
            return JsonResponse({
                'success': True,
                'content': template.content
            })
        except HiringAgreement.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Template not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

class HandbookPreviewView(View):
    def get(self, request, template_id):
        try:
            template = Handbook.objects.get(handbook_id=template_id)
            return JsonResponse({
                'success': True,
                'content': template.content
            })
        except Handbook.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Template not found'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class OnboardingInvitationDetailView(View):
    def get(self, request, invitation_id, *args, **kwargs):
        """View an invitation and provide accept/reject options"""
        try:
            invitation = OnboardingInvitation.objects.get(invitation_id=invitation_id)
            
            # For HTML template rendering
            if 'application/json' not in request.META.get('HTTP_ACCEPT', ''):
                context = {
                    'invitation': invitation,
                    'current_year': timezone.now().year,
                }
                return render(request, 'hr_management/invitation_view.html', context)
            
            # For API/JSON response (maintaining backward compatibility)
            invitation_data = {
                'invitation_id': str(invitation.invitation_id),
                'name': invitation.name,
                'email': invitation.email,
                'department': invitation.department.name if invitation.department else None,
                'designation': invitation.designation.name if invitation.designation else None,
                'role': invitation.role.name if invitation.role else None,
                'status': invitation.status,
                'sent_at': invitation.sent_at.isoformat() if invitation.sent_at else None,
                'completed_at': invitation.completed_at.isoformat() if invitation.completed_at else None,
                'rejected_at': invitation.rejected_at.isoformat() if invitation.rejected_at else None,
            }
            
            return JsonResponse({
                'success': True,
                'invitation': invitation_data
            })
        except OnboardingInvitation.DoesNotExist:
            if 'application/json' not in request.META.get('HTTP_ACCEPT', ''):
                # For HTML template
                context = {
                    'error': 'Invitation not found',
                    'current_year': timezone.now().year,
                }
                return render(request, 'hr_management/error.html', context)
            
            # For API/JSON
            return JsonResponse({
                'success': False,
                'message': 'Invitation not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error retrieving invitation details: {str(e)}", exc_info=True)
            
            if 'application/json' not in request.META.get('HTTP_ACCEPT', ''):
                # For HTML template
                context = {
                    'error': 'An error occurred',
                    'current_year': timezone.now().year,
                }
                return render(request, 'hr_management/error.html', context)
            
            # For API/JSON
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class OnboardingInvitationAcceptView(View):
    def post(self, request, invitation_id, *args, **kwargs):
        """Accept an invitation and generate employee credentials"""
        try:
            invitation = OnboardingInvitation.objects.get(invitation_id=invitation_id)
            
            # Parse request data if present
            try:
                data = json.loads(request.body)
                action = data.get('action', '')
                from_status = data.get('from_status', '')
                to_status = data.get('to_status', '')
            except (ValueError, json.JSONDecodeError):
                data = {}
                action = ''
                from_status = ''
                to_status = ''
            
            # Check if invitation is already processed
            if invitation.status in ['rejected', 'cancelled']:
                return JsonResponse({
                    'success': False,
                    'message': f'This invitation cannot be accepted as it is {invitation.status}'
                }, status=400)

            # Handle special case: Approving a completed invitation
            if action == 'approve_completed' and invitation.status == 'completed' and to_status == 'accepted':
                # Update invitation status to accepted
                invitation.status = 'accepted'
                invitation.save()
                
                # Find or create the employee record
                try:
                    # Use hr.models.Employee for the lookup
                    employee = Employee.objects.get(employee_email=invitation.email)
                    # Update existing employee
                    employee.is_active = True
                    employee.is_approved = True
                    employee.save()
                    
                    # Generate a new password for the existing employee
                    password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                    employee.password = make_password(password)
                    employee.save()
                    
                    # Send credentials email to the existing employee too
                    self.send_acceptance_email(invitation, password)
                    logger.info(f"Updated existing employee record for {invitation.email} and sent credentials email")
                except Employee.DoesNotExist:
                    # Generate random password
                    password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                    hashed_password = make_password(password)
                    
                    # Create new employee with fields from hr.models.Employee
                    employee = Employee.objects.create(
                        employee_email=invitation.email,
                        employee_name=invitation.name,
                        company=invitation.company,
                        password=hashed_password,
                        is_active=True,
                        is_approved=True
                    )
                    
                    # Send credentials email
                    self.send_acceptance_email(invitation, password)
                    logger.info(f"Created new employee record for {invitation.email}")
                
                return JsonResponse({
                    'success': True,
                    'message': 'Employee approved and granted dashboard access'
                })
            
            # Original flow: Handle pending/sent invitations
            # Generate random password
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
            hashed_password = make_password(password)
            
            # Create employee account if doesn't exist
            employee, created = Employee.objects.get_or_create(
                employee_email=invitation.email,
                defaults={
                    'employee_name': invitation.name,
                    'company': invitation.company,
                    'password': hashed_password,
                    'is_active': True,
                    'is_approved': True
                }
            )
            
            if not created:
                # Update existing employee
                employee.is_active = True
                employee.is_approved = True
                # Set a new password for the existing employee
                employee.password = hashed_password
                employee.save()
            
            # Update invitation status
            invitation.status = 'accepted'
            invitation.accepted_at = timezone.now()
            invitation.save()
            
            # Send credentials email to both new and existing employees
            self.send_acceptance_email(invitation, password)
            logger.info(f"Sent credentials email to {invitation.email}")
            
            return JsonResponse({
                'success': True,
                'message': 'Invitation accepted and credentials sent to employee'
            })
            
        except OnboardingInvitation.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invitation not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error accepting invitation: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    def send_acceptance_email(self, invitation, password):
        """Send email with login credentials to the accepted employee"""
        company = invitation.company
        
        # Get site URL from settings or use a default
        site_url = getattr(settings, 'SITE_URL', "https://1matrix.io")
        
        # Prepare context data for the email template
        context = {
            'name': invitation.name,
            'email': invitation.email,
            'company_name': company.company_name,
            'department': invitation.department.name if invitation.department else 'Not specified',
            'designation': invitation.designation.name if invitation.designation else 'Not specified',
            'role': invitation.role.name if invitation.role else 'Not specified',
            'login_url': f"{site_url}/hr_management/employee/login/",
            'username': invitation.email,  # Email is used as username
            'password': password,
            'current_year': timezone.now().year,
        }
        
        # Add company logo if available
        if company.company_logo:
            context['company_logo'] = company.company_logo.url
        
        try:
            # Render email template with context
            html_content = render_to_string('hr_management/email_templates/acceptance_credentials.html', context)
            text_content = strip_tags(html_content)
            
            # Send email
            subject = f"Welcome to {company.company_name} - Your Login Credentials"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [invitation.email]
            
            send_mail(
                subject=subject,
                message=text_content,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_content,
                fail_silently=False,
            )
            
            logger.info(f"Acceptance email with credentials sent to {invitation.email}")
        except Exception as e:
            logger.error(f"Error sending acceptance email: {str(e)}", exc_info=True)
            # Don't raise the exception as the employee is already created
            # Just log the error for monitoring

@method_decorator(csrf_exempt, name='dispatch')
class OnboardingInvitationRejectView(View):
    def post(self, request, invitation_id, *args, **kwargs):
        """Reject an invitation"""
        try:
            invitation = OnboardingInvitation.objects.get(invitation_id=invitation_id)
            
            # Parse request data if present
            try:
                data = json.loads(request.body)
                action = data.get('action', '')
                from_status = data.get('from_status', '')
                to_status = data.get('to_status', '')
                rejection_reason = data.get('rejection_reason', '')
            except (ValueError, json.JSONDecodeError):
                data = {}
                action = ''
                from_status = ''
                to_status = ''
                rejection_reason = ''
            
            # Check if invitation can be rejected
            if invitation.status in ['accepted', 'cancelled']:
                return JsonResponse({
                    'success': False,
                    'message': f'This invitation cannot be rejected as it is {invitation.status}'
                }, status=400)
            
            # Handle special case: Rejecting a completed invitation
            if action == 'reject_completed' and invitation.status == 'completed' and to_status == 'rejected':
                # Update invitation status to rejected
                invitation.status = 'rejected'
                invitation.rejected_at = timezone.now()
                invitation.rejection_reason = rejection_reason
                invitation.save()
                
                # Update any existing employee record to inactive if it exists
                try:
                    # Don't modify this line - it's using the hr.models.Employee
                    employee = Employee.objects.get(employee_email=invitation.email)
                    employee.is_active = False
                    employee.is_approved = False
                    employee.rejection_reason = rejection_reason
                    employee.save()
                    
                    logger.info(f"Deactivated employee record for {invitation.email}")
                except Employee.DoesNotExist:
                    logger.info(f"No employee record found for {invitation.email}")
                
                # Send rejection notification email
                self.send_rejection_email(invitation)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Employee application rejected successfully'
                })
            
            # Original flow: Handle pending/sent invitations
            # Update invitation status
            invitation.status = 'rejected'
            invitation.rejected_at = timezone.now()
            invitation.rejection_reason = rejection_reason
            invitation.save()
            
            # Send rejection email
            self.send_rejection_email(invitation)
            
            logger.info(f"Invitation rejected for {invitation.email}")
            
            return JsonResponse({
                'success': True,
                'message': 'Invitation rejected and notification sent'
            })
            
        except OnboardingInvitation.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invitation not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error rejecting invitation: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    def send_rejection_email(self, invitation):
        """Send rejection email to the applicant"""
        company = invitation.company
        
        # Prepare context data for the email template
        context = {
            'name': invitation.name,
            'email': invitation.email,
            'company_name': company.company_name,
            'rejection_reason': invitation.rejection_reason,
            'current_year': timezone.now().year,
        }
        
        # Add company logo if available
        if company.company_logo:
            context['company_logo'] = company.company_logo.url
        
        try:
            # Render email template with context
            html_content = render_to_string('hr_management/email_templates/rejection_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Send email
            subject = f"Update Regarding Your Application to {company.company_name}"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [invitation.email]
            
            send_mail(
                subject=subject,
                message=text_content,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_content,
                fail_silently=False,
            )
            
            logger.info(f"Rejection email sent to {invitation.email}")
        except Exception as e:
            logger.error(f"Error sending rejection email: {str(e)}", exc_info=True)
            # Don't raise the exception as the invitation is already rejected
            # Just log the error for monitoring

@method_decorator(csrf_exempt, name='dispatch')
class OnboardingInvitationDeleteView(View):
    def post(self, request, invitation_id, *args, **kwargs):
        """Delete an invitation"""
        try:
            invitation = OnboardingInvitation.objects.get(invitation_id=invitation_id)
            
            # Save details for logging
            name = invitation.name
            email = invitation.email
            
            # Delete the invitation
            invitation.delete()
            
            # Log the deletion
            logger.info(f"Invitation for {name} ({email}) was deleted")
            
            return JsonResponse({
                'success': True,
                'message': 'Invitation deleted successfully'
            })
        except OnboardingInvitation.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invitation not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error deleting invitation: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

@class_employee_login_required
class EmployeeDashboardView(TemplateView):
    template_name = 'hr_management/employee_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get employee from session or request
        employee_id = self.request.session.get('employee_id')
        
        if not employee_id:
            # Redirect to login if no employee is logged in
            return context
        
        try:
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            context['employee'] = employee
            
            # Today's date
            today = timezone.now().date()
            context['today_date'] = today
            
            # Attendance statistics
            month_start = today.replace(day=1)
            month_days = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            month_days = month_days.day
            
            # Get attendance for current month
            attendances = EmployeeAttendance.objects.filter(
                employee=employee,
                date__gte=month_start,
                date__lte=today
            )
            
            present_days = attendances.filter(status='present').count()
            
            context['attendance_stats'] = {
                'present': present_days,
                'total': month_days,
            }
            
            # Check today's status
            today_attendance = attendances.filter(date=today).first()
            context['today_status'] = today_attendance.status if today_attendance else 'not_marked'
            context['checked_out'] = today_attendance.check_out_time if today_attendance else False
            
            # Leave balance (example values, should be calculated from policy)
            context['leave_balance'] = {
                'casual': 7,
                'sick': 5,
                'annual': 14,
                'total': 26,
            }
            
            context['leave_policy'] = {
                'casual': 10,
                'sick': 7,
                'annual': 15,
            }
            
            # Pending requests
            pending_leaves = LeaveApplication.objects.filter(
                employee=employee, 
                status='pending'
            ).count()
            
            pending_reimbursements = ReimbursementRequest.objects.filter(
                employee=employee, 
                status='pending'
            ).count()
            
            context['pending_counts'] = {
                'leave': pending_leaves,
                'reimbursement': pending_reimbursements,
                'total': pending_leaves + pending_reimbursements,
            }
            
            # Latest salary slip
            latest_slip = SalarySlip.objects.filter(
                employee=employee
            ).order_by('-year', '-month').first()
            
            context['last_salary'] = latest_slip
            context['latest_slip'] = latest_slip
            
            # Recent Activities (collect recent activities for the employee)
            activities = []
            
            # Recent attendances
            recent_attendances = EmployeeAttendance.objects.filter(
                employee=employee
            ).order_by('-date', '-check_in_time')[:5]
            
            for attendance in recent_attendances:
                activity_type = "check_out" if attendance.check_out_time else "check_in"
                time_display = attendance.check_out_time if activity_type == "check_out" else attendance.check_in_time
                if time_display:
                    time_str = time_display.strftime('%I:%M %p')
                    activities.append({
                        'type': activity_type,
                        'icon': 'check' if activity_type == "check_in" else 'sign-out-alt',
                        'color': 'green' if activity_type == "check_in" else 'blue',
                        'title': 'Attendance Marked' if activity_type == "check_in" else 'Checked Out',
                        'description': f'You checked in at {time_str}' if activity_type == "check_in" else f'You checked out at {time_str}',
                        'timestamp': time_display,
                        'time_ago': self.get_time_ago(time_display)
                    })
            
            # Recent leave applications
            recent_leaves = LeaveApplication.objects.filter(
                employee=employee
            ).order_by('-created_at')[:3]
            
            for leave in recent_leaves:
                status_colors = {
                    'pending': 'amber',
                    'approved': 'green',
                    'rejected': 'red',
                    'cancelled': 'slate'
                }
                color = status_colors.get(leave.status, 'amber')
                activities.append({
                    'type': 'leave',
                    'icon': 'calendar-check',
                    'color': color,
                    'title': f'Leave Request {leave.status.capitalize()}',
                    'description': f'Your {leave.leave_type} leave from {leave.start_date.strftime("%d %b")} to {leave.end_date.strftime("%d %b")}',
                    'timestamp': leave.created_at,
                    'time_ago': self.get_time_ago(leave.created_at)
                })
            
            # Recent reimbursement requests
            recent_reimbursements = ReimbursementRequest.objects.filter(
                employee=employee
            ).order_by('-created_at')[:3]
            
            for reimbursement in recent_reimbursements:
                status_colors = {
                    'pending': 'amber',
                    'approved': 'green',
                    'rejected': 'red'
                }
                color = status_colors.get(reimbursement.status, 'amber')
                activities.append({
                    'type': 'reimbursement',
                    'icon': 'receipt',
                    'color': color,
                    'title': f'Reimbursement {reimbursement.status.capitalize()}',
                    'description': f'{reimbursement.currency} {reimbursement.amount} for {reimbursement.category}',
                    'timestamp': reimbursement.created_at,
                    'time_ago': self.get_time_ago(reimbursement.created_at)
                })
            
            # Recent salary slips
            if latest_slip:
                activities.append({
                    'type': 'salary',
                    'icon': 'file-invoice-dollar',
                    'color': 'emerald',
                    'title': 'Salary Slip Generated',
                    'description': f'{latest_slip.get_month_name} {latest_slip.year} salary slip has been generated',
                    'timestamp': latest_slip.created_at,
                    'time_ago': self.get_time_ago(latest_slip.created_at)
                })
            
            # Sort activities by timestamp (most recent first)
            activities.sort(key=lambda x: x['timestamp'], reverse=True)
            
            # Take only the top 10 activities
            context['activities'] = activities[:10]
            context['recent_activities'] = activities[:3]  # For the dashboard card
            
            # Get any pending invitations for this employee's email
            pending_invitations = OnboardingInvitation.objects.filter(
                email=employee.employee_email,
                status__in=['pending', 'sent']
            ).order_by('-created_at')
            
            context['invitations'] = pending_invitations
            
        except (Employee.DoesNotExist, Exception) as e:
            logger.error(f"Error preparing employee dashboard: {str(e)}", exc_info=True)
        
        return context
        
    def get_time_ago(self, timestamp):
        """Helper method to calculate human-readable time ago string"""
        if not timestamp:
            return ''
            
        now = timezone.now()
        diff = now - timestamp
        
        if diff.days > 365:
            years = diff.days // 365
            return f"{years}y ago"
        elif diff.days > 30:
            months = diff.days // 30
            return f"{months}mo ago"
        elif diff.days > 0:
            return f"{diff.days}d ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours}h ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes}m ago"
        else:
            return "just now"

@class_employee_login_required
class EmployeeProfileView(TemplateView):
    template_name = 'hr_management/employee_profile.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee_id = self.request.session.get('employee_id')
        
        if not employee_id:
            return context
        
        try:
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            context['employee'] = employee
        except Exception as e:
            logger.error(f"Error retrieving employee profile: {str(e)}", exc_info=True)
        
        return context
    
    def post(self, request, *args, **kwargs):
        # Handle profile update
        employee_id = request.session.get('employee_id')
        if not employee_id:
            return JsonResponse({'success': False, 'message': 'Not logged in'}, status=401)
        
        try:
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            
            # Update basic info
            if 'name' in request.POST:
                employee.name = request.POST.get('name')
            if 'phone' in request.POST:
                employee.phone_number = request.POST.get('phone')
            if 'address' in request.POST:
                employee.address = request.POST.get('address')
            
            # Handle profile photo if uploaded
            if 'photo' in request.FILES:
                employee.profile_photo = request.FILES.get('photo')
            
            employee.save()
            
            return JsonResponse({'success': True, 'message': 'Profile updated successfully'})
        except Exception as e:
            logger.error(f"Error updating employee profile: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@class_employee_login_required
class EmployeeLeaveView(TemplateView):
    template_name = 'hr_management/employee_leave.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee_id = self.request.session.get('employee_id')
        
        if not employee_id:
            return context
        
        try:
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            context['employee'] = employee
            
            # Get all leave applications for this employee
            leave_applications = LeaveApplication.objects.filter(
                employee=employee
            ).order_by('-created_at')
            
            context['leave_applications'] = leave_applications
            
            # Get leave types
            context['leave_types'] = dict(LeaveApplication.LEAVE_TYPES)
            
            # Leave balance (example values, should be calculated from policy)
            context['leave_balance'] = {
                'casual': 7,
                'sick': 5,
                'annual': 14,
                'total': 26,
            }
        except Exception as e:
            logger.error(f"Error retrieving employee leave data: {str(e)}", exc_info=True)
        
        return context

@class_employee_login_required
class EmployeeReimbursementView(TemplateView):
    template_name = 'hr_management/employee_reimbursement.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee_id = self.request.session.get('employee_id')
        
        if not employee_id:
            return context
        
        try:
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            context['employee'] = employee
            
            # Get all reimbursement requests for this employee
            reimbursement_requests = ReimbursementRequest.objects.filter(
                employee=employee
            ).order_by('-created_at')
            
            context['reimbursement_requests'] = reimbursement_requests
            
            # Get expense categories
            context['expense_categories'] = dict(ReimbursementRequest.EXPENSE_CATEGORIES)
        except Exception as e:
            logger.error(f"Error retrieving employee reimbursement data: {str(e)}", exc_info=True)
        
        return context

@class_employee_login_required
class EmployeeSalarySlipsView(TemplateView):
    template_name = 'hr_management/employee_salary_slips.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee_id = self.request.session.get('employee_id')
        
        if not employee_id:
            return context
        
        try:
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            context['employee'] = employee
            
            # Get all salary slips for this employee
            salary_slips = SalarySlip.objects.filter(
                employee=employee
            ).order_by('-year', '-month')
            
            context['salary_slips'] = salary_slips
        except Exception as e:
            logger.error(f"Error retrieving employee salary slips: {str(e)}", exc_info=True)
        
        return context

@class_employee_login_required
class EmployeeResignationView(TemplateView):
    template_name = 'hr_management/employee_resignation.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee_id = self.request.session.get('employee_id')
        
        if not employee_id:
            return context
        
        try:
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            context['employee'] = employee
            
            # Check if employee has any existing resignation requests
            resignation = Resignation.objects.filter(
                employee=employee
            ).order_by('-created_at').first()
            
            context['resignation'] = resignation
            context['has_resignation'] = resignation is not None
            
            # Get resignation status choices
            context['resignation_statuses'] = dict(Resignation.RESIGNATION_STATUS)
        except Exception as e:
            logger.error(f"Error retrieving employee resignation data: {str(e)}", exc_info=True)
        
        return context

@class_employee_login_required
class EmployeeDocumentsView(TemplateView):
    template_name = 'hr_management/employee_documents.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        employee_id = self.request.session.get('employee_id')
        
        if not employee_id:
            return context
        
        try:
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            context['employee'] = employee
            
            # Get all relevant documents
            context['company_policies'] = TandC.objects.all()
            context['handbooks'] = Handbook.objects.all()
            context['hiring_agreements'] = HiringAgreement.objects.all()
            context['training_materials'] = TrainingMaterial.objects.all()
        except Exception as e:
            logger.error(f"Error retrieving employee documents: {str(e)}", exc_info=True)
        
        return context

class EmployeeLogoutView(View):
    def post(self, request, *args, **kwargs):
        # Clear employee session
        if 'employee_id' in request.session:
            del request.session['employee_id']
        
        # Redirect to login page
        return redirect('employee_login')

# API Views for Employee Dashboard
@method_decorator(csrf_exempt, name='dispatch')
class MarkAttendanceAPIView(View):
    def post(self, request, *args, **kwargs):
        employee_id = request.session.get('employee_id')
        if not employee_id:
            return JsonResponse({'success': False, 'message': 'Not logged in'}, status=401)
        
        try:
            data = json.loads(request.body)
            action = data.get('action', 'check_in')
            method = data.get('method', 'manual')
            location = data.get('location', {})
            qr_code = data.get('qr_code', '')
            
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            
            today = timezone.now().date()
            
            # Check if attendance already exists for today
            attendance = EmployeeAttendance.objects.filter(
                employee=employee,
                date=today
            ).first()
            
            # Validate check-out action
            if action == 'check_out' and (not attendance or not attendance.check_in_time):
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot check out without checking in first'
                }, status=400)
            
            # Validate check-in action
            if action == 'check_in' and attendance and attendance.check_in_time and not attendance.check_out_time:
                return JsonResponse({
                    'success': False,
                    'message': 'Already checked in for today, please check out first'
                }, status=400)
            
            # Validate if already checked out
            if attendance and attendance.check_out_time:
                return JsonResponse({
                    'success': False,
                    'message': 'Attendance already marked for today and checked out'
                }, status=400)
            
            # Extract location information if provided
            location_string = ""
            if isinstance(location, dict) and location.get('latitude') and location.get('longitude'):
                location_string = f"lat:{location.get('latitude')},lng:{location.get('longitude')}"
            
            # Create or update attendance record
            if attendance:
                # Update existing attendance record (check out)
                attendance.check_out_time = timezone.now()
                attendance.check_out_method = method
                attendance.check_out_location = location_string
                attendance.save()
                message = 'Checked out successfully'
            else:
                # Create new attendance record (check in)
                attendance = EmployeeAttendance.objects.create(
                    employee=employee,
                    date=today,
                    status='present',
                    check_in_time=timezone.now(),
                    check_in_method=method,
                    check_in_location=location_string,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    device_info=request.META.get('HTTP_USER_AGENT')
                )
                message = 'Attendance marked successfully'
            
            return JsonResponse({
                'success': True,
                'message': message,
                'attendance_id': str(attendance.attendance_id),
                'check_in': attendance.check_in_time.isoformat(),
                'check_out': attendance.check_out_time.isoformat() if attendance.check_out_time else None
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Error marking attendance: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class LeaveApplicationAPIView(View):
    def post(self, request, *args, **kwargs):
        employee_id = request.session.get('employee_id')
        if not employee_id:
            return JsonResponse({'success': False, 'message': 'Not logged in'}, status=401)
        
        try:
            data = json.loads(request.body)
            leave_type = data.get('leave_type')
            start_date_str = data.get('start_date')
            end_date_str = data.get('end_date')
            reason = data.get('reason')
            
            # Validate required fields
            if not all([leave_type, start_date_str, end_date_str, reason]):
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required fields'
                }, status=400)
            
            # Parse dates
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }, status=400)
            
            # Validate date range
            today = timezone.now().date()
            if start_date < today:
                return JsonResponse({
                    'success': False,
                    'message': 'Start date cannot be in the past'
                }, status=400)
            
            if end_date < start_date:
                return JsonResponse({
                    'success': False,
                    'message': 'End date cannot be before start date'
                }, status=400)
            
            # Calculate leave days
            leave_days = (end_date - start_date).days + 1
            
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            
            # Check if there are overlapping leave applications
            overlapping_leaves = LeaveApplication.objects.filter(
                employee=employee,
                status__in=['pending', 'approved'],
                start_date__lte=end_date,
                end_date__gte=start_date
            ).exists()
            
            if overlapping_leaves:
                return JsonResponse({
                    'success': False,
                    'message': 'You already have a leave application for these dates'
                }, status=400)
            
            # Create leave application
            leave = LeaveApplication.objects.create(
                employee=employee,
                leave_type=leave_type,
                start_date=start_date,
                end_date=end_date,
                reason=reason,
                status='pending'
            )
            
            # Optional: Save attachments if provided
            attachments = request.FILES.getlist('attachments')
            if attachments:
                for attachment in attachments:
                    LeaveApplication.objects.create(
                        leave=leave,
                        file=attachment
                    )
            
            return JsonResponse({
                'success': True,
                'message': 'Leave application submitted successfully',
                'leave_id': str(leave.leave_id)
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Error submitting leave application: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class CancelLeaveAPIView(View):
    def post(self, request, leave_id, *args, **kwargs):
        employee_id = request.session.get('employee_id')
        if not employee_id:
            return JsonResponse({'success': False, 'message': 'Not logged in'}, status=401)
        
        try:
            # Get employee
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            
            # Get the leave application
            try:
                leave = LeaveApplication.objects.get(leave_id=leave_id, employee=employee)
            except LeaveApplication.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Leave application not found'
                }, status=404)
            
            # Check if leave can be cancelled
            if leave.status not in ['pending', 'approved']:
                return JsonResponse({
                    'success': False,
                    'message': f'Cannot cancel leave in {leave.status} status'
                }, status=400)
            
            # Check if leave has already started
            today = timezone.now().date()
            if leave.start_date <= today:
                return JsonResponse({
                    'success': False,
                    'message': 'Cannot cancel a leave that has already started or completed'
                }, status=400)
            
            # Update leave status to cancelled
            leave.status = 'cancelled'
            leave.updated_at = timezone.now()
            leave.save()
            
            # Optional: Parse and save cancellation reason if provided
            try:
                data = json.loads(request.body)
                cancellation_reason = data.get('reason')
                if cancellation_reason:
                    # You might need to add a field to the model for cancellation reason
                    # For now, we'll append it to the review notes
                    leave.review_notes = f"Cancelled by employee. Reason: {cancellation_reason}"
                    leave.save()
            except json.JSONDecodeError:
                pass  # No reason provided, that's fine
            
            return JsonResponse({
                'success': True,
                'message': 'Leave application cancelled successfully'
            })
            
        except Exception as e:
            logger.error(f"Error cancelling leave application: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ReimbursementRequestAPIView(View):
    def post(self, request, *args, **kwargs):
        employee_id = request.session.get('employee_id')
        if not employee_id:
            return JsonResponse({'success': False, 'message': 'Not logged in'}, status=401)
        
        try:
            # Parse JSON data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                # Handle form-data for file uploads
                data = request.POST.dict()
            
            # Get form fields
            amount = data.get('amount')
            currency = data.get('currency', 'INR')
            category = data.get('category')
            expense_date_str = data.get('expense_date')
            description = data.get('description')
            
            # Validate required fields
            if not all([amount, category, expense_date_str, description]):
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required fields'
                }, status=400)
            
            # Validate amount is numeric
            try:
                amount = float(amount)
                if amount <= 0:
                    raise ValueError("Amount must be positive")
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid amount'
                }, status=400)
            
            # Parse expense date
            try:
                expense_date = datetime.strptime(expense_date_str, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }, status=400)
            
            # Validate expense date not in future
            today = timezone.now().date()
            if expense_date > today:
                return JsonResponse({
                    'success': False,
                    'message': 'Expense date cannot be in the future'
                }, status=400)
            
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            
            # Create reimbursement request
            reimbursement = ReimbursementRequest.objects.create(
                employee=employee,
                amount=amount,
                currency=currency,
                category=category,
                expense_date=expense_date,
                description=description,
                status='pending'
            )
            
            # Handle file uploads
            receipts = request.FILES.getlist('receipts')
            if receipts:
                for receipt in receipts:
                    ReimbursementRequest.objects.create(
                        reimbursement=reimbursement,
                        file=receipt
                    )
            
            return JsonResponse({
                'success': True,
                'message': 'Reimbursement request submitted successfully',
                'reimbursement_id': str(reimbursement.reimbursement_id)
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Error submitting reimbursement request: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class DeleteDocumentAPIView(View):
    def delete(self, request, document_id, *args, **kwargs):
        try:
            # Get employee from session
            employee_id = request.session.get('employee_id')
            if not employee_id:
                return JsonResponse({'success': False, 'message': 'Authentication required'}, status=401)
            
            # Get the document
            document = EmployeeDocument.objects.get(id=document_id, employee_id=employee_id)
            
            # Delete the file
            if document.file:
                if os.path.isfile(document.file.path):
                    os.remove(document.file.path)
            
            # Delete the document
            document.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Document deleted successfully'
            })
            
        except EmployeeDocument.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Document not found'}, status=404)
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

# Employee login required decorator
def employee_login_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        employee_id = request.session.get('employee_id')
        if not employee_id:
            return redirect('hr_employee_login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

# Class-based view decorator

class HREmployeeLoginView(View):
    def get(self, request):
        # If already logged in, redirect to dashboard
        if 'employee_id' in request.session:
            return redirect('employee_dashboard')
        
        return render(request, 'hr_management/employee_login.html')
    
    def post(self, request):
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not email or not password:
            messages.error(request, 'Please provide both email and password')
            return render(request, 'hr_management/employee_login.html')
            
        try:
            # Try to get employee with matching email
            employee = Employee.objects.get(employee_email=email)
            
            # Verify password
            if check_password(password, employee.password):
                # Set session
                request.session['employee_id'] = str(employee.employee_id)
                
                # Redirect to dashboard
                return redirect('employee_dashboard')
            else:
                messages.error(request, 'Invalid password')
        except Employee.DoesNotExist:
            messages.error(request, 'No account found with this email')
            
        return render(request, 'hr_management/employee_login.html')

@method_decorator(csrf_exempt, name='dispatch')
class OnboardingInvitationsListView(View):
    def get(self, request, *args, **kwargs):
        try:
            # Get all invitations, ordered by most recent first
            invitations = OnboardingInvitation.objects.all().order_by('-created_at')
            
            # Convert to a list of dictionaries for JSON response
            invitations_data = []
            for invitation in invitations:
                invitations_data.append({
                    'invitation_id': str(invitation.invitation_id),
                    'name': invitation.name,
                    'email': invitation.email,
                    'department': invitation.department.name if invitation.department else '',
                    'designation': invitation.designation.name if invitation.designation else '',
                    'role': invitation.role.name if invitation.role else '',
                    'status': invitation.status,
                    'sent_at': invitation.sent_at.isoformat() if invitation.sent_at else None,
                    'form_link': invitation.form_link
                })
            
            return JsonResponse({
                'success': True,
                'invitations': invitations_data
            })
        except Exception as e:
            logger.error(f"Error fetching invitations: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': f"Error fetching invitations: {str(e)}"
            }, status=500)

class ViewOfferView(TemplateView):
    template_name = 'hr_management/view_offer.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        token = kwargs.get('token')
        if not token:
            logger.error("No token provided for view offer")
            return context
            
        try:
            # Find invitation by token in form_link
            invitations = OnboardingInvitation.objects.filter(form_link__contains=token)
            if not invitations.exists():
                logger.error(f"No invitation found with token {token}")
                return context
                
            invitation = invitations.first()
            context['invitation'] = invitation
            context['company_name'] = invitation.company.company_name
            
            # Add company logo if available
            if invitation.company.company_logo:
                context['company_logo'] = invitation.company.company_logo.url
                
            # Get offer letter content
            if invitation.offer_letter_template:
                offer_letter_content = invitation.offer_letter_template.content
                # Replace placeholders with actual values
                offer_letter_content = offer_letter_content.replace('[Employee Name]', invitation.name)
                offer_letter_content = offer_letter_content.replace('[Designation]', invitation.designation.name if invitation.designation else '')
                offer_letter_content = offer_letter_content.replace('[Company Name]', invitation.company.company_name)
                offer_letter_content = offer_letter_content.replace('[Start Date]', 'To be determined')
                
                context['offer_letter_content'] = offer_letter_content
            else:
                context['offer_letter_content'] = '<p>No offer letter template was selected for this invitation.</p>'
                
            # Get policies if any
            if invitation.policies:
                try:
                    policy_ids = json.loads(invitation.policies)
                    policies = []
                    for policy_id in policy_ids:
                        try:
                            policy = TandC.objects.get(tandc_id=policy_id)
                            policies.append(policy)
                        except TandC.DoesNotExist:
                            continue
                    context['policies'] = policies
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in policies field: {invitation.policies}")
                    
        except Exception as e:
            logger.error(f"Error retrieving offer details: {str(e)}", exc_info=True)
            
        return context


@method_decorator(csrf_exempt, name='dispatch')
class OfferResponseView(View):
    def post(self, request, invitation_id, *args, **kwargs):
        try:
            # Get the invitation
            invitation = OnboardingInvitation.objects.get(invitation_id=invitation_id)
            
            # Get response type
            response = request.POST.get('response')
            
            if response == 'accept':
                # Update status to completed
                invitation.status = 'completed'  # Keep as 'completed' for backward compatibility
                invitation.completed_at = timezone.now()
                invitation.save()
                
                # Redirect to onboarding form
                token = invitation.form_link.split('/')[-2]
                return redirect(f"/hr_management/onboarding/form/{token}/")
                
            elif response == 'reject':
                # Get rejection reason
                reason = request.POST.get('reason', '')
                
                # Update status to rejected
                invitation.status = 'rejected'
                invitation.rejected_at = timezone.now()
                invitation.rejection_reason = reason
                invitation.save()
                
                # Return a success page
                return render(request, 'hr_management/offer_response_success.html', {
                    'response': 'reject',
                    'company_name': invitation.company.company_name,
                    'invitation_id': invitation.invitation_id
                })
                
            elif response == 'discuss':
                # Get discussion message
                message = request.POST.get('message', '')
                
                # Update status to need discussion
                invitation.status = 'need_discussion'
                invitation.discussion_message = message
                invitation.save()
                
                # Return a success page
                return render(request, 'hr_management/offer_response_success.html', {
                    'response': 'discuss',
                    'company_name': invitation.company.company_name,
                    'invitation_id': invitation.invitation_id
                })
                
            else:
                logger.error(f"Invalid response type: {response}")
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid response type'
                }, status=400)
                
        except OnboardingInvitation.DoesNotExist:
            logger.error(f"Invitation not found: {invitation_id}")
            return JsonResponse({
                'success': False,
                'message': 'Invitation not found'
            }, status=404)
            
        except Exception as e:
            logger.error(f"Error processing offer response: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class ResignationAPIView(View):
    def post(self, request, *args, **kwargs):
        employee_id = request.session.get('employee_id')
        if not employee_id:
            return JsonResponse({'success': False, 'message': 'Not logged in'}, status=401)
        
        try:
            # Parse the JSON-encoded request body to extract the data sent by the client
            data = json.loads(request.body)
            last_working_date = data.get('last_working_date')
            reason = data.get('reason')
            additional_notes = data.get('additional_notes')
            
            # Validate input
            if not all([last_working_date, reason]):
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required fields'
                }, status=400)
            
            # Convert date
            try:
                last_working_date = datetime.strptime(last_working_date, '%Y-%m-%d').date()
            except ValueError:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid date format. Use YYYY-MM-DD'
                }, status=400)
            
            # Validate notice period (at least 2 weeks)
            resignation_date = timezone.now().date()
            notice_period = (last_working_date - resignation_date).days
            
            if notice_period < 14:
                return JsonResponse({
                    'success': False,
                    'message': 'Notice period must be at least 14 days'
                }, status=400)
            
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            
            # Check if employee already has a pending resignation
            existing_resignation = Resignation.objects.filter(
                employee=employee,
                status__in=['pending', 'acknowledged', 'processing']
            ).exists()
            
            if existing_resignation:
                return JsonResponse({
                    'success': False,
                    'message': 'You already have a pending resignation request'
                }, status=400)
            
            # Create resignation request
            resignation = Resignation.objects.create(
                employee=employee,
                resignation_date=resignation_date,
                last_working_date=last_working_date,
                reason=reason,
                additional_notes=additional_notes,
                status='pending'
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Resignation submitted successfully',
                'resignation_id': str(resignation.resignation_id),
                'status': resignation.status,
                'notice_period_days': resignation.notice_period_days
            })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Error submitting resignation: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class CancelResignationAPIView(View):
    def post(self, request, *args, **kwargs):
        employee_id = request.session.get('employee_id')
        if not employee_id:
            return JsonResponse({'success': False, 'message': 'Not logged in'}, status=401)
        
        try:
            # Get employee
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            
            # Get the resignation request
            resignation = Resignation.objects.filter(
                employee=employee,
                status__in=['pending', 'acknowledged', 'processing']
            ).order_by('-created_at').first()
            
            if not resignation:
                return JsonResponse({
                    'success': False,
                    'message': 'No active resignation request found'
                }, status=404)
            
            # Get optional cancellation reason
            cancellation_reason = None
            try:
                data = json.loads(request.body)
                cancellation_reason = data.get('reason')
            except json.JSONDecodeError:
                pass  # No JSON data, that's fine
            
            # Update resignation status to cancelled
            resignation.status = 'cancelled'
            
            # Add cancellation reason to feedback if provided
            if cancellation_reason:
                resignation.feedback = f"Cancelled by employee. Reason: {cancellation_reason}"
            
            resignation.updated_at = timezone.now()
            resignation.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Resignation request cancelled successfully'
            })
            
        except Exception as e:
            logger.error(f"Error cancelling resignation: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class UpdateProfileAPIView(View):
    def post(self, request, *args, **kwargs):
        employee_id = request.session.get('employee_id')
        if not employee_id:
            return JsonResponse({'success': False, 'message': 'Not logged in'}, status=401)
        
        try:
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            
            # Parse data based on content type
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                # Handle form-data for file uploads
                data = request.POST.dict()
                
            # Update basic information
            if 'name' in data:
                employee.name = data.get('name')
            if 'phone_number' in data:
                employee.phone_number = data.get('phone_number')
            if 'address' in data:
                employee.address = data.get('address')
            if 'emergency_contact_name' in data:
                employee.emergency_contact_name = data.get('emergency_contact_name')
            if 'emergency_contact_phone' in data:
                employee.emergency_contact_phone = data.get('emergency_contact_phone')
            if 'date_of_birth' in data:
                try:
                    date_of_birth = datetime.strptime(data.get('date_of_birth'), '%Y-%m-%d').date()
                    employee.date_of_birth = date_of_birth
                except ValueError:
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid date format for date of birth. Use YYYY-MM-DD'
                    }, status=400)
                    
            # Handle file uploads
            if 'photo' in request.FILES:
                employee.photo = request.FILES.get('photo')
                
            # Save changes
            employee.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Profile updated successfully'
            })
            
        except Exception as e:
            logger.error(f"Error updating profile: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class UpdatePasswordAPIView(View):
    def post(self, request, *args, **kwargs):
        employee_id = request.session.get('employee_id')
        if not employee_id:
            return JsonResponse({'success': False, 'message': 'Not logged in'}, status=401)
        
        try:
            data = json.loads(request.body)
            current_password = data.get('current_password')
            new_password = data.get('new_password')
            confirm_password = data.get('confirm_password')
            
            # Validate required fields
            if not all([current_password, new_password, confirm_password]):
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required fields'
                }, status=400)
                
            # Validate new password matches confirmation
            if new_password != confirm_password:
                return JsonResponse({
                    'success': False,
                    'message': 'New password and confirmation do not match'
                }, status=400)
                
            # Validate password complexity
            if len(new_password) < 8:
                return JsonResponse({
                    'success': False,
                    'message': 'Password must be at least 8 characters long'
                }, status=400)
                
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            
            # Verify current password
            from django.contrib.auth.hashers import check_password, make_password
            if not check_password(current_password, employee.password):
                return JsonResponse({
                    'success': False,
                    'message': 'Current password is incorrect'
                }, status=400)
                
            # Update password
            employee.password = make_password(new_password)
            employee.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Password updated successfully'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON data'}, status=400)
        except Exception as e:
            logger.error(f"Error updating password: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class UploadDocumentAPIView(View):
    def post(self, request, *args, **kwargs):
        employee_id = request.session.get('employee_id')
        if not employee_id:
            return JsonResponse({'success': False, 'message': 'Not logged in'}, status=401)
        
        try:
            from employee.models import Employee
            employee = Employee.objects.get(id=employee_id)
            
            # Get form data
            document_type = request.POST.get('document_type')
            document_name = request.POST.get('document_name')
            notes = request.POST.get('notes', '')
            
            # Validate required fields
            if not all([document_type, document_name]) or 'file' not in request.FILES:
                return JsonResponse({
                    'success': False,
                    'message': 'Missing required fields'
                }, status=400)
            
            document_file = request.FILES.get('file')
            
            # Validate file size (max 10MB)
            if document_file.size > 10 * 1024 * 1024:
                return JsonResponse({
                    'success': False,
                    'message': 'File size exceeds 10MB limit'
                }, status=400)
            
            # Create document
            document = EmployeeDocument.objects.create(
                employee=employee,
                document_type=document_type,
                document_name=document_name,
                notes=notes,
                file=document_file,
                file_size=f"{document_file.size / 1024:.1f} KB"
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Document uploaded successfully',
                'document_id': document.id,
                'document_name': document.document_name,
                'document_type': document.document_type,
                'upload_date': document.uploaded_at.strftime('%Y-%m-%d %H:%M')
            })
            
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}", exc_info=True)
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

@method_decorator(csrf_exempt, name='dispatch')
class FormCompletedActionView(View):
    """
    View to handle actions when an employee completes an onboarding form.
    Provides the UI and API for accept/reject actions.
    """
    
    def get(self, request, invitation_id, *args, **kwargs):
        """Render the UI for Accept/Reject buttons after form completion"""
        try:
            invitation = OnboardingInvitation.objects.get(invitation_id=invitation_id)
            
            # Check if the form is completed
            if not invitation.is_form_completed:
                return JsonResponse({
                    'success': False,
                    'message': 'The form has not been completed yet'
                }, status=400)
                
            # If the invitation is already processed
            if invitation.status in ['accepted', 'rejected']:
                status_message = f"This application has already been {invitation.status}"
                return render(request, 'hr_management/form_action_result.html', {
                    'success': True,
                    'invitation': invitation,
                    'status_message': status_message
                })
                
            # Render the UI for accept/reject options
            return render(request, 'hr_management/form_action.html', {
                'invitation': invitation
            })
            
        except OnboardingInvitation.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invitation not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error rendering form action UI: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    def post(self, request, invitation_id, *args, **kwargs):
        """Handle accept/reject actions"""
        try:
            invitation = OnboardingInvitation.objects.get(invitation_id=invitation_id)
            
            # Parse request data
            try:
                data = json.loads(request.body)
                action = data.get('action', '')
                rejection_reason = data.get('rejection_reason', '')
            except (ValueError, json.JSONDecodeError):
                # Try to get from POST data if not JSON
                action = request.POST.get('action', '')
                rejection_reason = request.POST.get('rejection_reason', '')
            
            # Check if the form is completed
            if not invitation.is_form_completed:
                return JsonResponse({
                    'success': False,
                    'message': 'The form has not been completed yet'
                }, status=400)
                
            # Process the action
            if action == 'accept':
                # Use the model method for acceptance
                invitation.accept_invitation()
                
                # Generate random password
                password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                hashed_password = make_password(password)
                
                # Create employee account if doesn't exist
                employee, created = Employee.objects.get_or_create(
                    employee_email=invitation.email,
                    defaults={
                        'employee_name': invitation.name,
                        'company': invitation.company,
                        'password': hashed_password,
                        'is_active': True,
                        'is_approved': True
                    }
                )
                
                if not created:
                    # Update existing employee
                    employee.is_active = True
                    employee.is_approved = True
                    employee.password = hashed_password
                    employee.save()
                
                # Send acceptance email with login credentials
                success = self.send_acceptance_email(invitation, password)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Application accepted and credentials sent to employee',
                    'email_sent': success
                })
                
            elif action == 'reject':
                # Use the model method for rejection
                invitation.reject_invitation(rejection_reason)
                
                # Send rejection email
                success = self.send_rejection_email(invitation)
                
                return JsonResponse({
                    'success': True,
                    'message': 'Application rejected and notification sent to applicant',
                    'email_sent': success
                })
                
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid action specified'
                }, status=400)
                
        except OnboardingInvitation.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Invitation not found'
            }, status=404)
        except Exception as e:
            logger.error(f"Error processing form action: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    def send_acceptance_email(self, invitation, password):
        """Send email with login credentials to the accepted employee"""
        company = invitation.company
        
        # Get site URL from settings or use a default
        site_url = getattr(settings, 'SITE_URL', "https://1matrix.io")
        
        # Prepare context data for the email template
        context = {
            'name': invitation.name,
            'email': invitation.email,
            'company_name': company.company_name,
            'department': invitation.department.name if invitation.department else 'Not specified',
            'designation': invitation.designation.name if invitation.designation else 'Not specified',
            'role': invitation.role.name if invitation.role else 'Not specified',
            'login_url': f"{site_url}/hr_management/employee/login/",
            'username': invitation.email,  # Email is used as username
            'password': password,
            'current_year': timezone.now().year,
        }
        
        # Add company logo if available
        if company.company_logo:
            context['company_logo'] = company.company_logo.url
        
        try:
            # Render email template with context
            html_content = render_to_string('hr_management/email_templates/acceptance_credentials.html', context)
            text_content = strip_tags(html_content)
            
            # Send email
            subject = f"Welcome to {company.company_name} - Your Login Credentials"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [invitation.email]
            
            send_mail(
                subject=subject,
                message=text_content,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_content,
                fail_silently=False,
            )
            
            logger.info(f"Acceptance email with credentials sent to {invitation.email}")
            return True
        except Exception as e:
            logger.error(f"Error sending acceptance email: {str(e)}", exc_info=True)
            # Don't raise the exception as the employee is already created
            # Just log the error for monitoring
            return False
    
    def send_rejection_email(self, invitation):
        """Send rejection email to the applicant"""
        company = invitation.company
        
        # Prepare context data for the email template
        context = {
            'name': invitation.name,
            'email': invitation.email,
            'company_name': company.company_name,
            'rejection_reason': invitation.rejection_reason,
            'current_year': timezone.now().year,
        }
        
        # Add company logo if available
        if company.company_logo:
            context['company_logo'] = company.company_logo.url
        
        try:
            # Render email template with context
            html_content = render_to_string('hr_management/email_templates/rejection_notification.html', context)
            text_content = strip_tags(html_content)
            
            # Send email
            subject = f"Update Regarding Your Application to {company.company_name}"
            from_email = settings.DEFAULT_FROM_EMAIL
            recipient_list = [invitation.email]
            
            send_mail(
                subject=subject,
                message=text_content,
                from_email=from_email,
                recipient_list=recipient_list,
                html_message=html_content,
                fail_silently=False,
            )
            
            logger.info(f"Rejection email sent to {invitation.email}")
            return True
        except Exception as e:
            logger.error(f"Error sending rejection email: {str(e)}", exc_info=True)
            # Don't raise the exception as the invitation is already rejected
            # Just log the error for monitoring
            return False

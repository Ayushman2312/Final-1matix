from django.views.generic import TemplateView
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
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.utils.decorators import method_decorator
import logging
from django.core.files.storage import default_storage
import os
from django.shortcuts import render
logger = logging.getLogger(__name__)

# Create your views here.
class CompanyView(TemplateView):
    template_name = 'hr_management/company.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'Company'
        context['companies'] = Company.objects.all()
        context['qr_codes'] = QRCode.objects.all()
        return context

class CreationView(TemplateView):
    template_name = 'hr_management/creation.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'Templates'
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
        context['app_name'] = 'Onboarding'
        context['companies'] = Company.objects.all()
        context['employees'] = Employee.objects.all()
        context['offer_letters'] = OfferLetter.objects.all()
        context['departments'] = Department.objects.all()
        context['designations'] = Designation.objects.all()
        context['tandcs'] = TandC.objects.all()
        return context

class AttendanceView(TemplateView):
    template_name = 'hr_management/attendance.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'Attendance'
        context['employees'] = Employee.objects.all()
        context['qr_codes'] = QRCode.objects.all()
        context['companies'] = Company.objects.all()
        return context
    
class CreateCompanyView(TemplateView):
    template_name = 'hr_management/create_hr_company.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['app_name'] = 'Create Company'
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
        context['app_name'] = 'Mark Attendance'
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
                    f'Hello {employee.employee_name},\n\n'
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
                employee = Employee.objects.get(employee_email=email)
                employee.attendance_photo = photo  # Using attendance_photo to match model field
                employee.save()
                
                print(f"Successfully saved attendance photo for employee: {employee.employee_email}")
                
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

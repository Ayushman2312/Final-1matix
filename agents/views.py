from django.shortcuts import render, redirect
from django.views.generic import TemplateView
from django.utils import timezone
from django.http import JsonResponse
from .models import *
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAdminUser
from .serializer import *
from django.contrib.auth.hashers import make_password
from django.views import View
from django.contrib.auth.hashers import check_password
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import authenticate, login as django_login
import json
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.conf import settings
import base64
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import datetime
from django.core.mail import send_mail
import random
import os
import ffmpeg
import logging
from masteradmin.models import *


logger = logging.getLogger(__name__)

from django.views.decorators.csrf import csrf_protect

def convert_audio(input_path, output_path):
    """Convert any uploaded audio file to a valid MP3 format."""
    try:
        (
            ffmpeg
            .input(input_path)
            .output(output_path, format="mp3", audio_bitrate="192k")
            .run(overwrite_output=True)
        )
    except ffmpeg.Error as e:
        print("FFmpeg error:", e)

@csrf_exempt
def save_audio(request):
    if request.method == "POST" and request.FILES.get("audio_file"):
        audio_file = request.FILES["audio_file"]

        # Create a temporary path to save the uploaded file
        temp_path = f"/tmp/{audio_file.name}"
        with open(temp_path, "wb") as f:
            for chunk in audio_file.chunks():
                f.write(chunk)

        # Define the final converted MP3 file path
        converted_filename = f"meeting_audio_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.mp3"
        converted_path = f"/tmp/{converted_filename}"

        # Convert the audio file
        convert_audio(temp_path, converted_path)

        # Save the converted file to Django's storage
        final_storage_path = f"agents/meeting_audio/{converted_filename}"
        with open(converted_path, "rb") as f:
            default_storage.save(final_storage_path, ContentFile(f.read()))


        # Cleanup temp files
        os.remove(temp_path)
        os.remove(converted_path)

        return JsonResponse({"message": "Audio saved successfully!", "file_path": final_storage_path})
    
    return JsonResponse({"error": "Invalid request"}, status=400)

def AgentLogin(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        
        if not email:
            messages.error(request, 'Please provide both email and password')
            return render(request, 'agents/agent_login.html')
            
        try:
            user = AgentUser.objects.get(email=email)
            password = check_password(password, user.password)
            if password:
                request.session['agent_id'] = str(user.id)
                return redirect('agent_dashboard')
            else:
                messages.error(request, 'Invalid password')
        except AgentUser.DoesNotExist:
            messages.error(request, 'Invalid credentials')
            
    return render(request, 'agents/agent_login.html')


class AgentReadView(View):
    def post(self, request, agent_id):
        try:
            notification = AgentNotification.objects.get(id=agent_id)
            notification.is_read = True
            notification.save()
            return JsonResponse({'status': 'success'})
        except AgentNotification.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Notification not found'}, status=404)
        except Exception as e:
            logger.error(f"Error updating notification status: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Internal server error'}, status=500)


# class AgentLoginView(TemplateView):
#     template_name = "agents/agent_login.html"

#     @method_decorator(csrf_exempt)
#     def dispatch(self, request, *args, **kwargs):
#         return super().dispatch(request, *args, **kwargs)

#     @staticmethod
#     def send_otp(request):
#         try:
#             data = json.loads(request.body)
#             email = data.get('email')
            
#             if not email:
#                 return JsonResponse({'error': 'Email is required.'}, status=400)

#             try:
#                 user = AgentUser.objects.get(email=email, is_active=True, is_approved=True)
#             except AgentUser.DoesNotExist:
#                 return JsonResponse({'error': 'Account not found or not approved.'}, status=404)

#             # Generate OTP and store in session with timestamp
#             otp = str(random.randint(100000, 999999))
#             request.session['otp'] = {
#                 'code': otp,
#                 'email': email,
#                 'timestamp': timezone.now().timestamp(),
#                 'attempts': 0
#             }
#             print(request.session['otp'])
#             try:
#                 # Configure email settings
#                 send_mail(
#                     subject='Your OTP Code',
#                     message=f'Your OTP code is {otp}. Valid for 5 minutes.',
#                     from_email=settings.EMAIL_HOST_USER,
#                     recipient_list=[email],
#                     fail_silently=False,
#                     auth_user=settings.EMAIL_HOST_USER,
#                     auth_password=settings.EMAIL_HOST_PASSWORD,
#                     connection=None
#                 )
#                 logger.info(f"OTP email sent successfully to {email}")
#                 return JsonResponse({'status': 'success', 'message': 'OTP sent to your email.'})
#             except Exception as e:
#                 logger.error(f"Failed to send OTP email: {str(e)}")
#                 return JsonResponse({'error': 'Failed to send OTP email.'}, status=500)

#         except Exception as e:
#             logger.error(f"Error in send_otp: {str(e)}")
#             return JsonResponse({'error': 'Internal server error.'}, status=500)

#     @staticmethod
#     def verify_otp(request):
#         try:
#             data = json.loads(request.body)
#             entered_otp = data.get('otp')
            
#             if not entered_otp:
#                 return JsonResponse({'error': 'OTP is required.'}, status=400)

#             otp_data = request.session.get('otp')
#             if not otp_data:
#                 return JsonResponse({'error': 'No OTP found. Please request a new one.'}, status=400)

#             # Check if OTP is expired (5 minutes)
#             current_time = timezone.now().timestamp()
#             if current_time - otp_data['timestamp'] > 300:  # 5 minutes
#                 del request.session['otp']
#                 return JsonResponse({'error': 'OTP has expired. Please request a new one.'}, status=400)

#             # Check attempts
#             if otp_data['attempts'] >= 3:
#                 del request.session['otp']
#                 return JsonResponse({'error': 'Too many attempts. Please request a new OTP.'}, status=400)

#             # Increment attempts
#             otp_data['attempts'] += 1
#             request.session['otp'] = otp_data

#             if entered_otp == otp_data['code']:
#                 # Store email for login step
#                 request.session['verified_email'] = otp_data['email']
#                 del request.session['otp']
#                 return JsonResponse({'status': 'success', 'message': 'OTP verified successfully.'})
            
#             return JsonResponse({'error': 'Invalid OTP.'}, status=400)

#         except Exception as e:
#             logger.error(f"Error in verify_otp: {str(e)}")
#             return JsonResponse({'error': 'Internal server error.'}, status=500)

#     @staticmethod
#     def login(request):
#         try:
#             from django.contrib.auth.hashers import check_password
            
#             data = json.loads(request.body)
#             email = data.get('email')
#             password = data.get('password')
            
#             if not email or not password:
#                 return JsonResponse({'error': 'Email and password are required.'}, status=400)

#             # Verify email matches the OTP-verified email
#             # verified_email = request.session.get('verified_email')
#             # if not verified_email or verified_email != email:
#             #     return JsonResponse({'error': 'Please verify your email with OTP first.'}, status=400)

#             # Get the user directly first to check if they exist and are approved
#             try:
#                 agent = AgentUser.objects.get(email=email)
#                 if not agent.is_active or not agent.is_approved:
#                     return JsonResponse({'error': 'Account not approved or inactive.'}, status=403)
                
#                 # Check hashed password directly
#                 if check_password(password, agent.password):
#                     # Set session variables for custom login
#                     request.session['agent_id'] = str(agent.id)
#                     request.session['agent_email'] = agent.email
#                     request.session['is_authenticated'] = True

#                     request.session.modified = True
                    
#                     # Clear OTP verification data
#                     request.session.pop('verified_email', None)
                    
#                     return JsonResponse({'status': 'success', 'redirect_url': '/agents/dashboard/'})
#                 else:
#                     return JsonResponse({'error': 'Invalid password.'}, status=403)

#             except AgentUser.DoesNotExist:
#                 return JsonResponse({'error': 'Account not found.'}, status=404)

#         except json.JSONDecodeError:
#             return JsonResponse({'error': 'Invalid JSON data.'}, status=400)
#         except Exception as e:
#             logger.error(f"Error in login: {str(e)}")
#             return JsonResponse({'error': 'Internal server error.'}, status=500)
        
def logout(request):
    request.session.clear()
    return redirect('/agents/')

class AgentProfileView(TemplateView):
    template_name = "agents/agent_profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agent_id = self.request.session.get('agent_id')
        if agent_id:
            try:
                agent = AgentUser.objects.get(id=agent_id)
                context['user'] = agent
            except AgentUser.DoesNotExist:
                context['user'] = None
        else:
            context['user'] = None
            
        return context

class AgentDashboardView(TemplateView):
    template_name = "agents/agent_dashboard.html"

    @method_decorator(csrf_protect)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['notifications'] = WhatsOnMind.objects.filter(department_type='agents')
        agent_user = self.request.session.get('agent_id')
        print(f"Agent user: {agent_user}")
        context['agent_notifications'] = AgentNotification.objects.filter(agent_user=agent_user)
        if agent_user:
            context['user'] = agent_user
        else:
            context['user'] = None  # or handle unauthenticated user as needed
        return context

@csrf_exempt
def save_audio(request):
    if request.method == "POST":
        audio_file = request.FILES["audio_file"]
        file_path = f"meeting_recordings/{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.wav"
        default_storage.save(file_path, ContentFile(audio_file.read()))
        return JsonResponse({"message": "Audio saved successfully!", "file_path": file_path})
    return JsonResponse({"error": "Invalid request"}, status=400)

@method_decorator(csrf_exempt, name='dispatch')
class MeetingsView(View):
    template_name = "agents/meetings.html"

    def get(self, request, *args, **kwargs):
        context = {}
        agent_email = request.session.get("agent_email")
        print(f"Agent email from session: {agent_email}")  # Debug print

        if not agent_email:
            print("❌ No agent email in session - redirecting to login")
            return redirect('/agents/login/')

        try:
            agent = AgentUser.objects.get(email=agent_email)
            active_meeting = Meeting.objects.filter(agent_user=agent, end_time__isnull=True).first()

            if active_meeting:
                print(f"✅ Active meeting found for agent: {agent_email}, Meeting ID: {active_meeting.id}")
                context["active_meeting"] = active_meeting
            else:
                print(f"❌ No active meeting found for agent: {agent_email}")
                context["active_meeting"] = None
        except AgentUser.DoesNotExist:
            print("❌ Agent not found in database")
            return redirect('/agents/login/')

        return render(request, self.template_name, context)
    
    def post(self, request, *args, **kwargs):
        try:
            # Check authentication first
            agent_email = request.session.get('agent_email')
            if not agent_email:
                print("❌ No agent email in session")
                return JsonResponse({'error': 'Not authenticated'}, status=401)

            # Handle JSON data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                action = data.get('action')
            else:
                # For form data, get action from POST
                data = request.POST
                action = data.get('action')

            print(f"Received action: {action} from agent: {agent_email}")  # Debug print

            if action == 'start':
                return self.start_meeting(request)
            elif action == 'end':
                return self.end_meeting(request)
            elif action == 'upload_audio':
                return self.upload_audio(request)
            elif action == 'upload_photo':
                return self.upload_photo(request, data)
            elif action == "start_demo":
                print("Starting demo...")
                return self.start_demo(request, data)
            elif action=="start_demo_otp":
                return self.start_demo_otp(request, data)
            elif action == "verify_demo_otp":
                return self.verify_demo_otp(request, data)
            elif action == "end_demo":
                return self.end_demo(request, data)
            elif action == "send_otp":
                return self.send_demo_otp(request, data)
            else:
                print(f"Invalid action received: {action}")  # Debug print
                return JsonResponse({'error': 'Invalid action'}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            print(f"Error in processing request: {e}")
            return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)

    def start_meeting(self, request):
        print("Starting meeting...")
        agent_email = self.request.session.get('agent_email')
        print(f"Agent email from session: {agent_email}")
        if not agent_email:
            print("❌ No agent email found in session")
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        
        try:
            print(f"Looking up agent with email: {agent_email}")
            agent_user = AgentUser.objects.get(email=agent_email)
            
            # Check for existing active meeting
            existing_meeting = Meeting.objects.filter(agent_user=agent_user, end_time__isnull=True).first()
            if existing_meeting:
                print(f"❌ Active meeting already exists for agent: {agent_email}")
                return JsonResponse({'error': 'Active meeting already exists'}, status=400)
                
            meeting = Meeting.objects.create(
                agent_user=agent_user,
                start_time=timezone.now(),
                is_active=True,
                is_completed=False
            )
            print(f"✅ Created new meeting with ID: {meeting.id}")
            request.session['meeting_id'] = str(meeting.id)
            request.session.modified = True

            return JsonResponse({
                'status': 'success',
                'meeting_id': str(meeting.id)
            })
        except AgentUser.DoesNotExist:
            print(f"❌ Agent not found with email: {agent_email}")
            return JsonResponse({'error': 'Agent not found'}, status=404)

    def end_meeting(self, request):
        print("Attempting to end meeting...")

        agent_email = request.session.get('agent_email')
        if not agent_email:
            print("❌ No agent email found in session")
            return JsonResponse({'error': 'Not authenticated'}, status=401)

        try:
            # Find the agent
            agent_user = AgentUser.objects.get(email=agent_email)

            # Fetch the latest active meeting for this agent
            meeting = Meeting.objects.filter(agent_user=agent_user, end_time__isnull=True).order_by('-start_time').first()

            if not meeting:
                print(f"❌ No active meeting found for agent: {agent_email}")
                return JsonResponse({'error': 'No active meeting found'}, status=400)

            # End the meeting
            meeting.end_time = timezone.now()
            meeting.is_active = False
            meeting.is_completed = True
            meeting.meeting_duration = meeting.end_time - meeting.start_time
            meeting.save()

           # Remove session meeting_id if exists
            if 'meeting_id' in request.session:
                del request.session['meeting_id']
                request.session.modified = True

            print(f"✅ Successfully ended meeting {meeting.id} for agent {agent_email}")
            return JsonResponse({
                'message': 'Meeting ended successfully',
                'duration': str(meeting.meeting_duration)
            })

        except AgentUser.DoesNotExist:
            print(f"❌ Agent not found with email: {agent_email}")
            return JsonResponse({'error': 'Agent not found'}, status=404)

        except Exception as e:
            print(f"❌ Error ending meeting: {str(e)}")
            return JsonResponse({'error': f'Error ending meeting: {str(e)}'}, status=500)


    def upload_audio(self, request):
        print("Uploading audio...")
        meeting_id = request.POST.get('meeting_id') or request.session.get('meeting_id')
        if not meeting_id:
            print("❌ No meeting ID found in POST data or session")
            return JsonResponse({'error': 'No active meeting found'}, status=400)
            
        audio_file = request.FILES.get('audio_file')
        print(f"Audio file received: {audio_file.name if audio_file else None}")
        
        try:
            print(f"Looking up meeting with ID: {meeting_id}")
            meeting = Meeting.objects.get(id=meeting_id)
            
            # Save audio file
            if audio_file:
                print("Saving audio file...")
                meeting.meeting_audio.save(
                    f'meeting_{meeting_id}_audio.mp3',
                    audio_file,
                    save=True
                )
                meeting.save()
                print(f"✅ Audio file saved successfully")
            
            return JsonResponse({
                'message': 'Audio uploaded successfully',
                'audio_url': meeting.meeting_audio.url if meeting.meeting_audio else None
            })

        except Meeting.DoesNotExist:
            print(f"❌ Meeting not found with ID: {meeting_id}")
            return JsonResponse({'error': 'Meeting not found'}, status=404)
        except Exception as e:
            print(f"❌ Error saving audio: {str(e)}")
            return JsonResponse({'error': f'Error saving audio: {str(e)}'}, status=500)

    def upload_photo(self, request, data):
        print("Uploading photo...")
        meeting_id = data.get('meeting_id')
        if not meeting_id:
            print("❌ No meeting ID provided in data")
            return JsonResponse({'error': 'No meeting ID provided'}, status=400)

        photo_data = data.get('photo')
        if not photo_data:
            print("❌ No photo data provided")
            return JsonResponse({'error': 'No photo data provided'}, status=400)

        try:
            print(f"Looking up meeting with ID: {meeting_id}")
            meeting = Meeting.objects.get(id=meeting_id)
            
            # Handle base64 data with or without prefix
            if 'base64,' in photo_data:
                format, imgstr = photo_data.split('base64,')
                ext = format.split('/')[-1].split(';')[0]  # Handle format like "data:image/jpeg;base64,"
            else:
                imgstr = photo_data
                ext = 'jpg'  # Default extension if not specified
                
            # Clean base64 string by removing any whitespace/newlines
            imgstr = imgstr.strip()
            
            try:
                # Convert base64 to file
                print("Converting base64 to file...")
                photo_file = ContentFile(base64.b64decode(imgstr), name=f'meeting_{meeting_id}_photo.{ext}')
            except Exception as e:
                print(f"❌ Error decoding base64: {str(e)}")
                return JsonResponse({'error': 'Invalid photo data format'}, status=400)
            
            # Save photo
            print("Saving photo...")
            meeting.meeting_image = photo_file
            meeting.save()
            print("✅ Photo saved successfully")
            
            return JsonResponse({
                'message': 'Photo uploaded successfully',
                'photo_url': meeting.meeting_image.url if meeting.meeting_image else None
            })

        except Meeting.DoesNotExist:
            print(f"❌ Meeting not found with ID: {meeting_id}")
            return JsonResponse({'error': 'Meeting not found'}, status=404)
        except Exception as e:
            print(f"❌ Error saving photo: {str(e)}")
            return JsonResponse({'error': f'Error saving photo: {str(e)}'}, status=500)

    def start_demo(self, request, data):
        print("Starting demo...")
        try:
            client_name = data.get("client_name")
            client_email = data.get("client_email")
            client_phone = data.get("client_phone")

            print(f"Client details - Name: {client_name}, Email: {client_email}, Phone: {client_phone}")

            if not client_name or not client_email or not client_phone:
                print("❌ Missing required fields")
                return JsonResponse({"error": "All fields are required"}, status=400)

            # Validate email format
            try:
                validate_email(client_email)
            except ValidationError:
                print("❌ Invalid email format")
                return JsonResponse({"error": "Invalid email format"}, status=400)

            otp = str(random.randint(100000, 999999))

            agent_email = request.session.get("agent_email")
            if not agent_email:
                print("❌ Agent not authenticated")
                return JsonResponse({"error": "Agent not authenticated"}, status=403)

            try:
                print(f"Looking up agent with email: {agent_email}")
                agent = AgentUser.objects.get(email=agent_email)
                demo_session = DemoSession.objects.create(
                    agent_user=agent,
                    client_name=client_name,
                    client_email=client_email,
                    client_phone=client_phone,
                    otp=otp,
                )

                print(f"✅ Generated OTP: {otp} for client {client_email}")

                try:
                    send_mail(
                        subject="Your OTP for Demo Verification",
                        message=f"Your OTP is {otp}. Please enter it to start the demo.",
                        from_email=settings.EMAIL_HOST_USER,
                        recipient_list=[client_email],
                        fail_silently=False,
                    )
                    print("✅ OTP email sent successfully to", client_email)
                except Exception as email_error:
                    print(f"❌ Failed to send email: {str(email_error)}")
                    demo_session.delete()  # Cleanup the demo session if email fails
                    return JsonResponse({"error": "Failed to send OTP email"}, status=500)

                return JsonResponse({"message": "OTP sent to email", "demo_id": str(demo_session.id)})
            except AgentUser.DoesNotExist:
                print(f"❌ Agent not found in DB with email: {agent_email}")
                return JsonResponse({"error": "Agent not found"}, status=404)

        except Exception as e:
            print(f"❌ Error in start_demo: {str(e)}")
            return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)

    def verify_demo_otp(self, request, data):
        print("Verifying demo OTP...")
        try:
            demo_id = data.get("demo_id")
            entered_otp = data.get("otp")

            print(f"Demo ID: {demo_id}, Entered OTP: {entered_otp}")

            if not demo_id or not entered_otp:
                print("❌ Missing OTP or Demo ID")
                return JsonResponse({"error": "OTP and Demo ID are required"}, status=400)

            try:
                print(f"Looking up demo session with ID: {demo_id}")
                demo = DemoSession.objects.get(id=demo_id)
                if demo.otp == entered_otp:
                    demo.is_verified = True
                    demo.demo_url = f"https://{request.get_host()}/demo/{demo.id}/"
                    demo.save()

                    print(f"✅ Demo OTP verified for {demo.client_email}, Demo URL: {demo.demo_url}")

                    send_mail(
                        "Your Demo Access",
                        f"Your demo link: {demo.demo_url}. Please access it before it expires.",
                        settings.EMAIL_HOST_USER,
                        [demo.client_email],
                        fail_silently=False,
                    )
                    print("✅ Demo access email sent successfully")

                    return JsonResponse({"message": "OTP verified", "demo_url": demo.demo_url})
                else:
                    print("❌ Invalid OTP entered")
                    return JsonResponse({"error": "Invalid OTP"}, status=400)
            except DemoSession.DoesNotExist:
                print(f"❌ Demo session not found with ID: {demo_id}")
                return JsonResponse({"error": "Demo session not found"}, status=404)

        except Exception as e:
            print(f"❌ Error in verify_demo_otp: {str(e)}")
            return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)

    def end_demo(self, request, data):
        print("Ending demo...")
        try:
            demo_id = data.get("demo_id")
            print(f"Demo ID: {demo_id}")

            if not demo_id:
                print("❌ Missing Demo ID")
                return JsonResponse({"error": "Demo ID is required"}, status=400)

            try:
                print(f"Looking up demo session with ID: {demo_id}")
                demo = DemoSession.objects.get(id=demo_id)
                demo.expire_demo()

                print(f"✅ Demo ended for {demo.client_email}, Demo URL expired.")

                return JsonResponse({"message": "Demo ended successfully"})
            except DemoSession.DoesNotExist:
                print(f"❌ Demo session not found with ID: {demo_id}")
                return JsonResponse({"error": "Demo not found"}, status=404)

        except Exception as e:
            print(f"❌ Error in end_demo: {str(e)}")
            return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)

    def send_demo_otp(self, request, data):
        print("Sending demo OTP...")
        try:
            client_email = data.get("client_email")
            print(f"Client email: {client_email}")
            
            if not client_email:
                print("❌ Client email is required")
                return JsonResponse({"error": "Client email is required"}, status=400)

            otp = str(random.randint(100000, 999999))
            print(f"Generated OTP: {otp}")
            
            # Store OTP in session for verification
            request.session['demo_otp'] = {
                'code': otp,
                'email': client_email,
                'timestamp': timezone.now().timestamp()
            }

            # Send OTP email
            send_mail(
                "Your OTP for Demo Verification",
                f"Your OTP is {otp}. Please enter it to start the demo.",
                settings.EMAIL_HOST_USER,
                [client_email],
                fail_silently=False,
            )
            print("✅ OTP email sent successfully")

            return JsonResponse({"message": "OTP sent successfully"})
        except Exception as e:
            print(f"❌ Error in send_demo_otp: {str(e)}")
            return JsonResponse({"error": f"Server error: {str(e)}"}, status=500)
        

class RegisterView(TemplateView):
    template_name = "agents/register.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            passcode = self.kwargs.get('passcode')
            agent = AgentUser.objects.filter(agent_passcode=passcode).first()
            if agent:
                if agent.name and agent.phone_number and agent.dob:
                    context['agent_error'] = 'Agent has already registered'
                else:
                    context['email'] = agent.email
                    context['agent_passcode'] = passcode
                    context['departments'] = agent.department.terms_and_conditions
            else:
                context['error'] = 'Agent not found'
        except Exception as e:
            context['error'] = str(e)
        return context

    def post(self, request, *args, **kwargs):
        try:
            passcode = self.kwargs.get('passcode')
            agent = AgentUser.objects.filter(agent_passcode=passcode).first()
            
            if not agent:
                return JsonResponse({'error': 'Agent not found'}, status=404)
            
            if agent.name and agent.phone_number and agent.dob:
                return JsonResponse({'error': 'Agent has already registered'}, status=400)

            # Update basic information
            agent.name = request.POST.get('name')
            agent.phone_number = request.POST.get('phone_number')
            agent.dob = request.POST.get('dob')
            agent.qualification = request.POST.get('qualification')
            agent.address = request.POST.get('address')
            agent.experience = request.POST.get('experience_type')
            agent.pan_number = request.POST.get('pan_number')
            agent.aadhar_number = request.POST.get('aadhar_number')
            agent.gender = request.POST.get('gender')

            # Update bank details
            agent.bank_account_holder_name = request.POST.get('bank_account_holder_name')
            agent.bank_account_number = request.POST.get('bank_account_number')
            agent.bank_name = request.POST.get('bank_name')
            agent.branch_name = request.POST.get('branch_name')
            agent.bank_ifsc_code = request.POST.get('bank_ifsc_code')

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
                    setattr(agent, model_field, request.FILES[form_field])

            # Set password if provided
            if request.POST.get('password'):
                agent.password = make_password(request.POST.get('password'))

            # Save the agent
            agent.save()

            # Delete existing references before creating new ones
            AgentCoorporate.objects.filter(agent_user=agent).delete()
            AgentFamily.objects.filter(agent_user=agent).delete()

            # Handle corporate references
            for i in range(1, 3):
                corporate_data = {
                    'name': request.POST.get(f'corporate_ref{i}_name', '').strip(),
                    'email': request.POST.get(f'corporate_ref{i}_email', '').strip(),
                    'phone_number': request.POST.get(f'corporate_ref{i}_phone', '').strip(),
                    'address': request.POST.get(f'corporate_ref{i}_address', '').strip()
                }
                
                # Check if at least name and phone are provided
                if corporate_data['name'] and corporate_data['phone_number']:
                    AgentCoorporate.objects.create(
                        agent_user=agent,
                        name=corporate_data['name'],
                        email=corporate_data['email'],
                        phone_number=corporate_data['phone_number'],
                        address=corporate_data['address']
                    )

            # Handle family references
            for i in range(1, 3):
                family_data = {
                    'name': request.POST.get(f'family_ref{i}_name', '').strip(),
                    'email': request.POST.get(f'family_ref{i}_email', '').strip(),
                    'phone_number': request.POST.get(f'family_ref{i}_phone', '').strip(),
                    'address': request.POST.get(f'family_ref{i}_address', '').strip()
                }
                
                # Check if at least name and phone are provided
                if family_data['name'] and family_data['phone_number']:
                    AgentFamily.objects.create(
                        agent_user=agent,
                        name=family_data['name'],
                        email=family_data['email'],
                        phone_number=family_data['phone_number'],
                        address=family_data['address']
                    )

            return redirect('agent_success', passcode=passcode)

        except Exception as e:
            logger.error(f"Error in registration: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Error during registration: {str(e)}'
            }, status=500)
class MasterNotificationsView(TemplateView):
    template_name = "agents/master_notifications.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        agent_user = self.request.session.get("agent_id")
        if agent_user:
            context['agent_notifications'] = AgentNotification.objects.filter(
                agent_user=agent_user, is_read=False
            ).select_related('agent_user')  # This optimizes the query
        else:
            context['agent_notifications'] = AgentNotification.objects.none()
        return context

class Success(TemplateView):
    template_name = "agents/success.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        passcode = self.kwargs.get('passcode')
        try:
            agent = AgentUser.objects.get(agent_passcode=passcode)
            context['email'] = agent.email
            context['passcode'] = passcode
        except AgentUser.DoesNotExist:
            context['email'] = ''
            context['passcode'] = passcode
        return context
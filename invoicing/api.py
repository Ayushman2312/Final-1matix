from django.http import JsonResponse
from django.contrib.auth.hashers import check_password, make_password
from .models import Recipent
from django.views.decorators.csrf import csrf_exempt
import json
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def verify_professional(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        data = json.loads(request.body)
        combined_input = data.get('combined_input', '').strip()
        
        if not combined_input:
            return JsonResponse({'success': False, 'error': 'Please provide mobile number and security code'})
        
        # Extract mobile number (first 10 digits) and security code (remaining characters)
        if len(combined_input) <= 10:
            return JsonResponse({'success': False, 'error': 'Invalid input format. Please provide both mobile number and security code'})
            
        mobile_number = combined_input[:10]
        security_code = combined_input[10:]
        
        if not mobile_number.isdigit() or len(mobile_number) != 10:
            return JsonResponse({'success': False, 'error': 'Invalid mobile number format'})
        
        if not security_code:
            return JsonResponse({'success': False, 'error': 'Security code is required'})
        
        # Find recipient by mobile number
        recipient = Recipent.objects.filter(recipent_mobile_number=mobile_number).first()
        
        if not recipient:
            logger.warning(f"No recipient found for mobile number: {mobile_number}")
            return JsonResponse({'success': False, 'error': 'Invalid mobile number'})
        
        # Verify security code using check_password
        if check_password(security_code, recipient.security_code):
            # Store recipient_id in session for later use
            request.session['recipent_id'] = str(recipient.recipent_id)
            return JsonResponse({'success': True})
        
        logger.warning(f"Invalid security code attempt for mobile: {mobile_number}")
        return JsonResponse({'success': False, 'error': 'Invalid security code'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        logger.error(f"Error in verify_professional: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'An error occurred while processing your request'})

@csrf_exempt
def verify_passcode(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
    
    try:
        data = json.loads(request.body)
        passcode = data.get('passcode', '').strip()
        recipient_id = request.session.get('recipent_id')
        
        if not passcode:
            return JsonResponse({'success': False, 'error': 'Passcode is required'})
        
        if not recipient_id:
            return JsonResponse({'success': False, 'error': 'Session expired. Please verify your mobile number again'})
        
        recipient = Recipent.objects.filter(recipent_id=recipient_id).first()
        
        if not recipient:
            logger.error(f"No recipient found for ID: {recipient_id}")
            return JsonResponse({'success': False, 'error': 'Invalid session'})
        
        # Direct comparison since passcode is not hashed
        if passcode == recipient.passcode:
            return JsonResponse({
                'success': True,
                'redirectUrl': f'/invoice-reports/{recipient_id}/'
            })
        
        logger.warning(f"Invalid passcode attempt for recipient ID: {recipient_id}")
        return JsonResponse({'success': False, 'error': 'Invalid passcode'})
        
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
    except Exception as e:
        logger.error(f"Error in verify_passcode: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': 'An error occurred while processing your request'})
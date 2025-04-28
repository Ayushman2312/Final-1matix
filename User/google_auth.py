import requests
import json
import os
from django.conf import settings
from django.shortcuts import redirect
from django.urls import reverse
from .models import User
from django.utils import timezone
import uuid
import logging

logger = logging.getLogger(__name__)

# Get these from your Google Cloud Console
GOOGLE_CLIENT_ID = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['client_id']
GOOGLE_CLIENT_SECRET = settings.SOCIALACCOUNT_PROVIDERS['google']['APP']['secret']

def get_google_auth_url(request):
    """Generate Google OAuth URL"""
    # Store a random state value in session for security
    state = str(uuid.uuid4())
    request.session['google_oauth_state'] = state
    
    # Define redirect URI
    redirect_uri = request.build_absolute_uri(reverse('google_callback'))
    
    # Create OAuth URL
    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"state={state}&"
        f"scope=email profile&"
        f"access_type=online"
    )
    
    return auth_url

def handle_google_callback(request):
    """Process Google OAuth callback"""
    try:
        # Security check - verify state parameter
        received_state = request.GET.get('state', '')
        stored_state = request.session.get('google_oauth_state', '')
        
        if received_state != stored_state:
            logger.error("State parameter mismatch")
            return None, "Security verification failed"
        
        # Get authorization code
        code = request.GET.get('code')
        if not code:
            logger.error("No authorization code received")
            return None, "No authorization code received"
        
        # Exchange code for tokens
        redirect_uri = request.build_absolute_uri(reverse('google_callback'))
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            'code': code,
            'client_id': GOOGLE_CLIENT_ID,
            'client_secret': GOOGLE_CLIENT_SECRET,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code'
        }
        
        token_response = requests.post(token_url, data=token_data)
        if not token_response.ok:
            logger.error(f"Token exchange failed: {token_response.text}")
            return None, "Failed to exchange authorization code for token"
        
        token_json = token_response.json()
        access_token = token_json.get('access_token')
        
        # Get user info
        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {'Authorization': f'Bearer {access_token}'}
        userinfo_response = requests.get(userinfo_url, headers=headers)
        
        if not userinfo_response.ok:
            logger.error(f"Failed to get user info: {userinfo_response.text}")
            return None, "Failed to get user information"
        
        user_data = userinfo_response.json()
        
        # Extract user info
        email = user_data.get('email')
        name = user_data.get('name')
        
        if not email:
            logger.error("No email in Google user data")
            return None, "Email not provided by Google"
        
        # Find or create user
        try:
            user = User.objects.filter(email=email).first()
            if not user:
                # Generate a random username if needed
                user = User(
                    name=name,
                    email=email,
                    is_active=True,
                    created_at=timezone.now()
                )
                user.save()
                logger.info(f"Created new user via Google: {email}")
            
            return user, None
        except Exception as e:
            logger.error(f"Error creating/retrieving user: {str(e)}")
            return None, f"Error processing user data: {str(e)}"
            
    except Exception as e:
        logger.exception("Google callback error")
        return None, f"Authentication error: {str(e)}"
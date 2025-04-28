from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.utils import timezone
from .models import User

class CustomSocialAccountAdapter(DefaultSocialAccountAdapter):
    def save_user(self, request, sociallogin, form=None):
        """
        Custom user creation when signing up with social account
        """
        user = super().save_user(request, sociallogin, form)
        
        # Get user data from social account
        user_data = sociallogin.account.extra_data
        email = user_data.get('email')
        name = user_data.get('name', '')
        phone = user_data.get('phone', '')
        
        # Create our custom User model
        try:
            # Check if user already exists
            custom_user = User.objects.filter(email=email).first()
            
            if not custom_user:
                custom_user = User(
                    name=name,
                    email=email,
                    phone=phone,
                    is_active=True,
                    created_at=timezone.now()
                )
                custom_user.save()
        except Exception as e:
            print(f"Error creating custom user: {e}")
        
        return user
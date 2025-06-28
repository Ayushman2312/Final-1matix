import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', '1matrix.settings')
django.setup()

from User.models import User

# Get a user by email or whatever identifier you prefer
# You can modify this to select a specific user by email or ID
# Example: first_user = User.objects.get(email='your_admin@example.com')
first_user = User.objects.first()

if first_user:
    first_user.is_staff = True
    first_user.save()
    print(f"User '{first_user.name or first_user.email}' has been made a staff user.")
    print(f"Email: {first_user.email}")
else:
    print("No users found in the database.")
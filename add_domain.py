import os
import django
import uuid

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'matrix.settings')
django.setup()

# Import models
from website.models import CustomDomain, Website

# Get the first website
website = Website.objects.first()
if not website:
    print("No websites found in the database")
    exit(1)

# Check if domain already exists
if CustomDomain.objects.filter(domain='1matrix.io').exists():
    print("Domain 1matrix.io already exists")
    # Update the domain to verified status
    domain = CustomDomain.objects.get(domain='1matrix.io')
    domain.verification_status = 'verified'
    domain.save()
    print("Updated domain verification status to 'verified'")
else:
    # Create new domain
    domain = CustomDomain.objects.create(
        website=website,
        domain='1matrix.io',
        verification_status='verified',
        verification_code=str(uuid.uuid4()),
        ssl_status=False
    )
    print(f"Created new domain: {domain.domain} with verification status: {domain.verification_status}")

print("Done!") 
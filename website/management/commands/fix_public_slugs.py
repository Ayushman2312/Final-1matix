from django.core.management.base import BaseCommand
from website.models import Website
import uuid
from django.utils.text import slugify

class Command(BaseCommand):
    help = 'Fix any websites with missing or None public_slug values'

    def handle(self, *args, **options):
        # Get all websites with None, 'None' or empty public_slug
        websites = Website.objects.filter(public_slug__isnull=True) | Website.objects.filter(public_slug='None') | Website.objects.filter(public_slug='')
        fixed_count = 0
        
        for website in websites:
            # Generate a new slug
            base_slug = slugify(f"{website.user.username}-site")
            unique_id = str(uuid.uuid4())[:8]
            website.public_slug = f"{base_slug}-{unique_id}"
            website.save()
            fixed_count += 1
            
            self.stdout.write(self.style.SUCCESS(
                f'Fixed website ID {website.id} - New slug: {website.public_slug}'
            ))
        
        self.stdout.write(self.style.SUCCESS(
            f'Fixed {fixed_count} websites with missing public slugs'
        )) 
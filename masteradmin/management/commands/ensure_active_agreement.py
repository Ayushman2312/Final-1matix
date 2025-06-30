from django.core.management.base import BaseCommand
from masteradmin.models import UserAgreement
from django.utils import timezone

class Command(BaseCommand):
    help = 'Ensures that there is at least one active user agreement in the database.'

    def handle(self, *args, **options):
        # Check if an active user agreement already exists.
        if UserAgreement.objects.filter(is_active=True).exists():
            self.stdout.write(self.style.SUCCESS('An active user agreement already exists. No action needed.'))
            return

        # If no active agreement exists, create a new one.
        self.stdout.write(self.style.WARNING('No active user agreement found. Creating a default one.'))

        # Deactivate any existing agreements to ensure only one is active.
        UserAgreement.objects.update(is_active=False)

        UserAgreement.objects.create(
            title="Standard Terms and Conditions",
            content="""
            <h1>Terms and Conditions</h1>
            <p>Last updated: {date}</p>
            <p>Please read these terms and conditions carefully before using Our Service.</p>
            
            <h2>Interpretation and Definitions</h2>
            <p>...</p>
            
            <h2>Acknowledgment</h2>
            <p>These are the Terms and Conditions governing the use of this Service and the agreement that operates between You and the Company...</p>
            
            <h2>Contact Us</h2>
            <p>If you have any questions about these Terms and Conditions, You can contact us.</p>
            """.format(date=timezone.now().strftime('%B %d, %Y')),
            is_active=True
        )

        self.stdout.write(self.style.SUCCESS('Successfully created a new active user agreement.')) 
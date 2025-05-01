from django.core.management.base import BaseCommand, CommandError
from website.models import Website
from website.utils import WebsiteDeployer
import sys
import time

class Command(BaseCommand):
    help = 'Deploy a website or multiple websites to production'

    def add_arguments(self, parser):
        parser.add_argument('website_ids', nargs='*', type=int, help='IDs of websites to deploy (leave empty for all)')
        parser.add_argument('--all', action='store_true', help='Deploy all websites')
        parser.add_argument('--environment', type=str, default='production', choices=['production', 'staging', 'development'], 
                            help='Environment to deploy to')
        parser.add_argument('--force', action='store_true', help='Force deployment even if validation fails')
        parser.add_argument('--backup-only', action='store_true', help='Only create backup, do not deploy')
        parser.add_argument('--no-backup', action='store_true', help='Skip backup creation')

    def handle(self, *args, **options):
        website_ids = options['website_ids']
        deploy_all = options['all']
        environment = options['environment']
        force = options['force']
        backup_only = options['backup_only']
        no_backup = options['no_backup']
        
        if not website_ids and not deploy_all:
            self.stdout.write(self.style.WARNING('No website IDs provided and --all not specified. Use --all to deploy all websites.'))
            return
            
        # Get websites to deploy
        if deploy_all:
            websites = Website.objects.all()
            self.stdout.write(f"Found {websites.count()} websites to deploy")
        else:
            websites = Website.objects.filter(id__in=website_ids)
            found_ids = set(websites.values_list('id', flat=True))
            missing_ids = set(website_ids) - found_ids
            
            if missing_ids:
                self.stdout.write(self.style.WARNING(f"Warning: Could not find websites with IDs: {', '.join(map(str, missing_ids))}"))
                
            if not websites:
                self.stdout.write(self.style.ERROR('Error: No websites found with the provided IDs'))
                return
                
        # Process each website
        success_count = 0
        failed_count = 0
        
        for website in websites:
            self.stdout.write(f"\nDeploying website: {website.name} (ID: {website.id})")
            
            # Create deployer
            deployer = WebsiteDeployer(website)
            
            try:
                # Create deployment record
                deployment = deployer.create_deployment(environment=environment)
                self.stdout.write(f"Created deployment: {deployment.id}")
                
                if backup_only:
                    # Only create backup
                    backup = deployer._create_backup(deployment)
                    self.stdout.write(self.style.SUCCESS(f"Backup created successfully: {backup.id}"))
                    success_count += 1
                    continue
                
                # Start spinner
                self.stdout.write("Deploying", ending='')
                sys.stdout.flush()
                
                # Deploy website
                success, message = deployer.deploy(deployment=deployment, environment=environment)
                
                # Clear spinner line
                self.stdout.write("\r", ending='')
                sys.stdout.flush()
                
                if success:
                    self.stdout.write(self.style.SUCCESS(message))
                    success_count += 1
                else:
                    self.stdout.write(self.style.ERROR(message))
                    failed_count += 1
                    
                # Show deployment log
                self.stdout.write("\nDeployment log:")
                self.stdout.write("---------------")
                self.stdout.write(deployment.logs)
                self.stdout.write("---------------\n")
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error deploying website {website.id}: {str(e)}"))
                failed_count += 1
                
        # Summary
        self.stdout.write("\nDeployment Summary:")
        self.stdout.write(f"Total: {len(websites)}")
        self.stdout.write(self.style.SUCCESS(f"Successful: {success_count}"))
        
        if failed_count > 0:
            self.stdout.write(self.style.ERROR(f"Failed: {failed_count}"))
        else:
            self.stdout.write(f"Failed: {failed_count}")
            
        if backup_only:
            self.stdout.write("\nNote: Only backups were created, no actual deployments performed.") 
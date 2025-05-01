from django.core.management.base import BaseCommand, CommandError
from website.models import Website
from website.utils import check_website_health
import json
from django.utils import timezone

class Command(BaseCommand):
    help = 'Check the health of websites and generate reports'

    def add_arguments(self, parser):
        parser.add_argument('website_ids', nargs='*', type=int, help='IDs of websites to check (leave empty for all)')
        parser.add_argument('--all', action='store_true', help='Check all websites')
        parser.add_argument('--format', type=str, default='text', choices=['text', 'json'], help='Output format')
        parser.add_argument('--save', action='store_true', help='Save reports to files')
        parser.add_argument('--threshold', type=int, default=70, help='Health score threshold to consider healthy (0-100)')

    def handle(self, *args, **options):
        website_ids = options['website_ids']
        check_all = options['all']
        output_format = options['format']
        save_reports = options['save']
        threshold = options['threshold']
        
        if not website_ids and not check_all:
            self.stdout.write(self.style.WARNING('No website IDs provided and --all not specified. Use --all to check all websites.'))
            return
            
        # Get websites to check
        if check_all:
            websites = Website.objects.all()
            self.stdout.write(f"Found {websites.count()} websites to check")
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
        reports = {}
        
        for website in websites:
            self.stdout.write(f"\nChecking website: {website.name} (ID: {website.id})")
            
            try:
                # Generate health report
                report = check_website_health(website)
                reports[website.id] = report
                
                # Display report based on format
                if output_format == 'text':
                    self._display_text_report(website, report, threshold)
                else:  # json
                    self._display_json_report(website, report)
                    
                # Save report if requested
                if save_reports:
                    self._save_report(website, report)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error checking website {website.id}: {str(e)}"))
                
        # Summary
        healthy_count = sum(1 for report in reports.values() if report['metrics'].get('health_score', 0) >= threshold)
        warning_count = sum(1 for report in reports.values() if report['status'] == 'warning')
        critical_count = sum(1 for report in reports.values() if report['status'] == 'critical')
        
        self.stdout.write("\nHealth Check Summary:")
        self.stdout.write(f"Total: {len(websites)}")
        self.stdout.write(self.style.SUCCESS(f"Healthy: {healthy_count}"))
        
        if warning_count > 0:
            self.stdout.write(self.style.WARNING(f"Warning: {warning_count}"))
        else:
            self.stdout.write(f"Warning: {warning_count}")
            
        if critical_count > 0:
            self.stdout.write(self.style.ERROR(f"Critical: {critical_count}"))
        else:
            self.stdout.write(f"Critical: {critical_count}")
            
    def _display_text_report(self, website, report, threshold):
        """Display health report in text format"""
        # Display header
        self.stdout.write("\nHealth Report")
        self.stdout.write("-" * 50)
        
        # Display basic info
        self.stdout.write(f"Website: {website.name} (ID: {website.id})")
        self.stdout.write(f"Health Score: {report['metrics'].get('health_score', 0)}/100")
        
        # Display status with appropriate color
        status = report['status']
        if status == 'healthy':
            self.stdout.write(f"Status: {self.style.SUCCESS(status.upper())}")
        elif status == 'warning':
            self.stdout.write(f"Status: {self.style.WARNING(status.upper())}")
        else:  # critical
            self.stdout.write(f"Status: {self.style.ERROR(status.upper())}")
            
        # Display SEO score if available
        if 'seo_score' in report['metrics']:
            self.stdout.write(f"SEO Score: {report['metrics']['seo_score']}/100")
            
        # Display uptime
        self.stdout.write(f"Uptime: {report.get('uptime', 0)}%")
            
        # Display issues
        if report['issues']:
            self.stdout.write("\nIssues:")
            
            # Group issues by severity
            severity_order = ['critical', 'high', 'medium', 'low']
            for severity in severity_order:
                severity_issues = [issue for issue in report['issues'] if issue['severity'] == severity]
                
                if severity_issues:
                    # Display severity header with appropriate color
                    if severity in ['critical', 'high']:
                        self.stdout.write(f"\n{self.style.ERROR(severity.upper())}")
                    elif severity == 'medium':
                        self.stdout.write(f"\n{self.style.WARNING(severity.upper())}")
                    else:  # low
                        self.stdout.write(f"\n{severity.upper()}")
                        
                    # Display each issue
                    for i, issue in enumerate(severity_issues):
                        self.stdout.write(f"  {i+1}. {issue['description']}")
        else:
            self.stdout.write("\nNo issues found!")
            
    def _display_json_report(self, website, report):
        """Display health report in JSON format"""
        output = {
            'website_id': website.id,
            'website_name': website.name,
            'report': report,
            'generated_at': timezone.now().isoformat()
        }
        
        self.stdout.write(json.dumps(output, indent=2))
        
    def _save_report(self, website, report):
        """Save health report to a file"""
        import os
        from django.conf import settings
        from datetime import datetime
        
        # Create reports directory if it doesn't exist
        reports_dir = os.path.join(settings.MEDIA_ROOT, 'website_health')
        os.makedirs(reports_dir, exist_ok=True)
        
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"health_report_{website.id}_{timestamp}.json"
        filepath = os.path.join(reports_dir, filename)
        
        # Save report to file
        with open(filepath, 'w') as f:
            json.dump({
                'website_id': website.id,
                'website_name': website.name,
                'report': report,
                'generated_at': timezone.now().isoformat()
            }, f, indent=2)
            
        self.stdout.write(f"Report saved to {filepath}") 
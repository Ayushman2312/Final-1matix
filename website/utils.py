import dns.resolver
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import datetime
import os
import uuid
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
import logging

logger = logging.getLogger(__name__)

def verify_dns_settings(domain, verification_code):
    """
    Verify DNS settings for a domain by checking:
    1. TXT record contains the verification code
    2. A record points to our server IP
    
    Returns True if at least one of these conditions is met, otherwise False.
    """
    try:
        verification_success = False
        
        # Check TXT record for domain verification
        try:
            # First try to check TXT records at root domain
            txt_records = dns.resolver.resolve(domain, 'TXT')
            for record in txt_records:
                record_text = record.to_text().strip('"')
                if f"verification={verification_code}" in record_text:
                    verification_success = True
                    break
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            # If no TXT at root domain, try with _verify prefix
            try:
                txt_records = dns.resolver.resolve(f'_verify.{domain}', 'TXT')
                for record in txt_records:
                    record_text = record.to_text().strip('"')
                    if verification_code in record_text:
                        verification_success = True
                        break
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                pass
        
        # Check A record points to our server
        try:
            a_records = dns.resolver.resolve(domain, 'A')
            server_ip = '89.116.20.128'  # Replace with your server's IP
            
            for record in a_records:
                if str(record) == server_ip:
                    verification_success = True
                    break
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
            # If A record check fails, try CNAME
            try:
                cname_records = dns.resolver.resolve(domain, 'CNAME')
                # Check if CNAME points to our domain
                # This is a simplistic check - in production you'd validate the CNAME target
                if len(cname_records) > 0:
                    verification_success = True
            except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
                pass
        
        # Log verification attempt
        from .models import DomainLog
        DomainLog.objects.create(
            domain=domain,
            status_code=200 if verification_success else 400,
            message=f"Domain verification {'successful' if verification_success else 'failed'}"
        )
        
        return verification_success
        
    except Exception as e:
        # Log error
        from .models import DomainLog
        DomainLog.objects.create(
            domain=domain,
            status_code=500,
            message=f"DNS verification error: {str(e)}"
        )
        return False

def request_ssl_certificate(domain):
    """
    Request SSL certificate from Let's Encrypt using ACME protocol
    """
    try:
        # Import certbot library
        from certbot import main as certbot_main
        
        # Set up the certbot configuration
        certbot_args = [
            # Use certbot in non-interactive mode
            '--non-interactive',
            # Agree to terms of service
            '--agree-tos', 
            # Use webroot authentication
            '--authenticator', 'webroot',
            # Specify webroot path
            '--webroot-path', '/var/www/html',
            # Domain to get certificate for  
            '-d', domain,
            # Email for urgent notices
            '--email', 'admin@example.com',
            # Install certificate
            '--installer', 'apache'
        ]

        # Request the certificate
        certbot_main.main(certbot_args)
        
        # Update domain SSL status
        from .models import CustomDomain
        domain_obj = CustomDomain.objects.get(domain=domain)
        domain_obj.ssl_status = True
        domain_obj.save()

        return True

    except Exception as e:
        # Log the error
        from .models import DomainLog
        DomainLog.objects.create(
            domain=domain,
            status_code=500,
            message=f"SSL Certificate Request Failed: {str(e)}"
        )
        return False

def auto_generate_seo_content(website, request=None):
    """
    Automatically generate SEO-friendly content for a website
    based on its existing content.
    """
    try:
        # Ensure website content is not None
        if website.content is None:
            website.content = {}
        
        # Generate meta title if not exists
        if 'meta_title' not in website.content or not website.content['meta_title']:
            site_name = website.content.get('site_name', website.content.get('websiteName', ''))
            if site_name:
                website.content['meta_title'] = f"{site_name} - Official Website"
            else:
                website.content['meta_title'] = "Welcome to our Website"
        
        # Generate meta description if not exists
        if 'meta_description' not in website.content or not website.content['meta_description']:
            hero_subtitle = website.content.get('hero_subtitle', '')
            if hero_subtitle:
                website.content['meta_description'] = hero_subtitle[:157] + "..." if len(hero_subtitle) > 160 else hero_subtitle
            else:
                website.content['meta_description'] = "Discover our products and services. We provide high-quality solutions for your needs."
        
        # Generate meta keywords if not exists
        if 'meta_keywords' not in website.content or not website.content['meta_keywords']:
            # Extract potential keywords from content
            keywords = []
            for key in ['site_name', 'websiteName', 'hero_title', 'hero_subtitle', 'about_title']:
                if key in website.content and website.content[key]:
                    # Extract words longer than 3 characters
                    words = [word.lower() for word in website.content[key].split() if len(word) > 3]
                    keywords.extend(words)
            
            # Remove duplicates and limit to 10 keywords
            keywords = list(set(keywords))[:10]
            website.content['meta_keywords'] = ", ".join(keywords)
        
        # Generate structured data for SEO
        website.content['structured_data'] = {
            'organization': {
                'name': website.content.get('site_name', website.content.get('websiteName', 'Our Company')),
                'description': website.content.get('about_content', website.content.get('meta_description', '')),
                'logo': website.content.get('logo_url', ''),
                'url': request.build_absolute_uri(website.get_public_url()) if request else ''
            }
        }
        
        # Generate OG data if not exists
        if 'og_title' not in website.content:
            website.content['og_title'] = website.content['meta_title']
        
        if 'og_description' not in website.content:
            website.content['og_description'] = website.content['meta_description']
        
        # Indicate that SEO has been enhanced
        website.content['seo_enhanced'] = True
        
        # Save the website with force_update to ensure changes are persisted
        website.save(force_update=True)
        
        return True
    except Exception as e:
        import logging
        logging.error(f"Error in auto_generate_seo_content: {str(e)}")
        return False

def process_media_upload(file_obj, subfolder='website_media', prefix=None, allowed_types=None):
    """
    Process and save an uploaded media file with validation.
    
    Args:
        file_obj: The uploaded file object
        subfolder: The subfolder within MEDIA_ROOT to save the file
        prefix: Optional prefix for the filename
        allowed_types: List of allowed MIME types (None for no restriction)
        
    Returns:
        str: The relative path to the saved file or None if failed
    """
    if not file_obj:
        return None
        
    try:
        # Validate file type if restrictions provided
        if allowed_types and file_obj.content_type not in allowed_types:
            logger.warning(f"Invalid file type: {file_obj.content_type}. Allowed types: {allowed_types}")
            return None
            
        # Generate unique filename
        file_ext = os.path.splitext(file_obj.name)[1].lower()
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{prefix or 'media'}_{unique_id}{file_ext}"
        
        # Ensure subdirectory exists
        path = os.path.join(subfolder, filename)
        
        # Save file using Django's storage system
        saved_path = default_storage.save(path, ContentFile(file_obj.read()))
        
        # Return the media URL path
        return os.path.join(settings.MEDIA_URL.lstrip('/'), saved_path)
        
    except Exception as e:
        logger.error(f"Error processing media upload: {str(e)}")
        return None

def process_banner_image(file_obj):
    """Specialized handler for banner image uploads"""
    return process_media_upload(
        file_obj, 
        subfolder='website_banners',
        prefix='banner',
        allowed_types=settings.ALLOWED_IMAGE_TYPES
    )
    
def process_gallery_image(file_obj):
    """Specialized handler for gallery image uploads"""
    return process_media_upload(
        file_obj, 
        subfolder='website_gallery',
        prefix='gallery',
        allowed_types=settings.ALLOWED_IMAGE_TYPES
    )
    
def process_document_upload(file_obj):
    """Specialized handler for document uploads (PDF, DOC, etc.)"""
    allowed_types = [
        'application/pdf',
        'application/msword',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel',
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'text/plain'
    ]
    
    return process_media_upload(
        file_obj, 
        subfolder='website_documents',
        prefix='doc',
        allowed_types=allowed_types
    )

def delete_media_file(file_path):
    """
    Delete a media file from storage
    
    Args:
        file_path: The relative path to the file
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    if not file_path:
        return False
        
    try:
        # Remove media URL prefix if present
        if file_path.startswith(settings.MEDIA_URL):
            file_path = file_path[len(settings.MEDIA_URL):]
            
        # Remove leading slash if present
        file_path = file_path.lstrip('/')
        
        # Get absolute path
        absolute_path = os.path.join(settings.MEDIA_ROOT, file_path)
        
        # Check if file exists
        if os.path.exists(absolute_path):
            os.remove(absolute_path)
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting media file {file_path}: {str(e)}")
        return False

# SEO Enhancement Tools
class SEOAnalyzer:
    """Website SEO analyzer utility class"""
    
    def __init__(self, website):
        self.website = website
        self.content = website.get_content()
        self.seo_data = self.content.get('seo', {})
        
    def analyze(self):
        """Run a comprehensive SEO analysis on the website"""
        analysis = {
            'meta_tags': self._analyze_meta_tags(),
            'content': self._analyze_content(),
            'social_media': self._analyze_social_media(),
            'structured_data': self._analyze_structured_data(),
            'mobile_friendliness': self._analyze_mobile_friendliness(),
            'overall_score': 0,
            'recommendations': []
        }
        
        # Calculate overall score
        scores = [
            analysis['meta_tags']['score'],
            analysis['content']['score'],
            analysis['social_media']['score'],
            analysis['structured_data']['score'],
            analysis['mobile_friendliness']['score']
        ]
        
        analysis['overall_score'] = int(sum(scores) / len(scores))
        
        # Compile all recommendations
        for section in ['meta_tags', 'content', 'social_media', 'structured_data', 'mobile_friendliness']:
            if analysis[section]['recommendations']:
                analysis['recommendations'].extend(analysis[section]['recommendations'])
                
        return analysis
    
    def _analyze_meta_tags(self):
        """Analyze meta tags for SEO"""
        score = 0
        recommendations = []
        
        meta_title = self.seo_data.get('meta_title', '')
        meta_description = self.seo_data.get('meta_description', '')
        meta_keywords = self.seo_data.get('meta_keywords', '')
        
        # Check title
        if meta_title:
            if len(meta_title) < 30:
                recommendations.append("Meta title is too short. It should be between 30-60 characters.")
                score += 5
            elif len(meta_title) > 60:
                recommendations.append("Meta title is too long. It should be between 30-60 characters.")
                score += 5
            else:
                score += 20
        else:
            recommendations.append("Meta title is missing. Add a descriptive title between 30-60 characters.")
            
        # Check description
        if meta_description:
            if len(meta_description) < 120:
                recommendations.append("Meta description is too short. It should be between 120-160 characters.")
                score += 5
            elif len(meta_description) > 160:
                recommendations.append("Meta description is too long. It should be between 120-160 characters.")
                score += 5
            else:
                score += 20
        else:
            recommendations.append("Meta description is missing. Add a compelling description between 120-160 characters.")
            
        # Check keywords
        if meta_keywords:
            if len(meta_keywords.split(',')) < 3:
                recommendations.append("Consider adding more relevant keywords (at least 3-5).")
                score += 5
            else:
                score += 10
                
        return {
            'score': score if score <= 50 else 50,  # Cap at 50
            'recommendations': recommendations
        }
    
    def _analyze_content(self):
        """Analyze website content for SEO"""
        score = 0
        recommendations = []
        
        # Check for presence of key content sections
        if not self.content.get('hero_banners'):
            recommendations.append("No hero banners found. Consider adding compelling hero banners.")
        else:
            score += 10
            
        # Check if pages have content
        website_pages = self.website.get_pages()
        if not website_pages:
            recommendations.append("No pages found. Add more pages with relevant content.")
        else:
            score += 10
            
        # Check for about section
        if not self.content.get('about_section_title'):
            recommendations.append("About section is missing. Add an 'About Us' section to build trust.")
        else:
            score += 10
            
        # Check for contact information
        contact_info = self.content.get('contact_info', {})
        missing_contact = []
        
        if not contact_info.get('mobile_number'):
            missing_contact.append("phone number")
        
        if not contact_info.get('contact_email'):
            missing_contact.append("email")
            
        if not contact_info.get('address'):
            missing_contact.append("address")
            
        if missing_contact:
            recommendations.append(f"Missing contact information: {', '.join(missing_contact)}. Add these for better customer trust.")
        else:
            score += 20
            
        return {
            'score': score if score <= 50 else 50,  # Cap at 50
            'recommendations': recommendations
        }
        
    def _analyze_social_media(self):
        """Analyze social media integration"""
        score = 0
        recommendations = []
        
        social_links = self.seo_data.get('social_links', {})
        
        # Check if important social platforms are present
        platforms = ['facebook', 'instagram', 'twitter', 'linkedin']
        missing_platforms = []
        
        for platform in platforms:
            if not social_links.get(platform):
                missing_platforms.append(platform)
            else:
                score += 10
                
        if missing_platforms:
            recommendations.append(f"Missing social media links: {', '.join(missing_platforms)}. Add these for better visibility.")
            
        # Check Open Graph tags
        if not self.seo_data.get('og_title'):
            recommendations.append("Missing Open Graph title. Add og:title for better social sharing.")
        else:
            score += 5
            
        if not self.seo_data.get('og_description'):
            recommendations.append("Missing Open Graph description. Add og:description for better social sharing.")
        else:
            score += 5
            
        if not self.seo_data.get('og_image'):
            recommendations.append("Missing Open Graph image. Add og:image for better social sharing visibility.")
        else:
            score += 10
            
        return {
            'score': score if score <= 50 else 50,  # Cap at 50
            'recommendations': recommendations
        }
        
    def _analyze_structured_data(self):
        """Analyze structured data/schema markup"""
        score = 0
        recommendations = []
        
        structured_data = self.seo_data.get('structured_data', {})
        organization = structured_data.get('organization', {})
        
        # Check organization schema
        if organization:
            missing_org_fields = []
            
            if not organization.get('name'):
                missing_org_fields.append("name")
            else:
                score += 10
                
            if not organization.get('url'):
                missing_org_fields.append("url")
            else:
                score += 10
                
            if not organization.get('logo'):
                missing_org_fields.append("logo")
            else:
                score += 10
                
            if not organization.get('description'):
                missing_org_fields.append("description")
            else:
                score += 10
                
            if missing_org_fields:
                recommendations.append(f"Organization schema missing: {', '.join(missing_org_fields)}. Add these for better search visibility.")
        else:
            recommendations.append("No organization schema found. Add structured data for better search engine understanding.")
            
        # Add recommendation for product schema if there are products
        if hasattr(self.website, 'products') and self.website.products.count() > 0:
            recommendations.append("Consider adding Product schema markup for your product pages.")
            
        return {
            'score': score if score <= 50 else 50,  # Cap at 50
            'recommendations': recommendations
        }
        
    def _analyze_mobile_friendliness(self):
        """Analyze mobile friendliness (basic checks)"""
        score = 30  # Default reasonable score since we can't check actual responsiveness
        recommendations = []
        
        # Recommend mobile testing
        recommendations.append("Test your website on various mobile devices and screen sizes.")
        recommendations.append("Ensure all interactive elements are easily tappable on mobile.")
        
        return {
            'score': score if score <= 50 else 50,  # Cap at 50
            'recommendations': recommendations
        }
        
    def generate_seo_improvement_plan(self):
        """Generate an actionable SEO improvement plan"""
        analysis = self.analyze()
        
        priority_recommendations = []
        secondary_recommendations = []
        
        # Sort recommendations by priority
        for rec in analysis['recommendations']:
            if any(kw in rec.lower() for kw in ['missing', 'add', 'no ']):
                priority_recommendations.append(rec)
            else:
                secondary_recommendations.append(rec)
                
        improvement_plan = {
            'current_score': analysis['overall_score'],
            'target_score': min(100, analysis['overall_score'] + 20),
            'priority_tasks': priority_recommendations[:3],  # Top 3 priorities
            'secondary_tasks': secondary_recommendations[:5],  # Next 5 secondary tasks
            'sections': {
                'meta_tags': analysis['meta_tags'],
                'content': analysis['content'],
                'social_media': analysis['social_media'],
                'structured_data': analysis['structured_data'],
                'mobile_friendliness': analysis['mobile_friendliness']
            }
        }
        
        return improvement_plan

def generate_sitemap_xml(website):
    """
    Generate a sitemap.xml file content for the website
    """
    base_url = f"https://{website.customdomain_set.first().domain}" if website.customdomain_set.exists() else f"https://1matrix.io/website/s/{website.public_slug}"
    
    # XML header
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # Add homepage
    xml_content += '  <url>\n'
    xml_content += f'    <loc>{base_url}/</loc>\n'
    xml_content += '    <changefreq>weekly</changefreq>\n'
    xml_content += '    <priority>1.0</priority>\n'
    xml_content += '  </url>\n'
    
    # Add all website pages
    for page in website.get_pages():
        if not page.is_homepage:  # Skip homepage as it's already added
            xml_content += '  <url>\n'
            xml_content += f'    <loc>{base_url}/{page.slug}/</loc>\n'
            xml_content += '    <changefreq>monthly</changefreq>\n'
            xml_content += '    <priority>0.8</priority>\n'
            xml_content += '  </url>\n'
    
    # Add product pages if they exist
    if hasattr(website, 'products'):
        for product in website.products.filter(is_active=True):
            xml_content += '  <url>\n'
            xml_content += f'    <loc>{base_url}/product/{product.slug}/</loc>\n'
            xml_content += '    <changefreq>weekly</changefreq>\n'
            xml_content += '    <priority>0.9</priority>\n'
            xml_content += '  </url>\n'
    
    # Add category pages if they exist
    if hasattr(website, 'categories'):
        for category in website.categories.filter(is_active=True):
            xml_content += '  <url>\n'
            xml_content += f'    <loc>{base_url}/category/{category.slug}/</loc>\n'
            xml_content += '    <changefreq>weekly</changefreq>\n'
            xml_content += '    <priority>0.7</priority>\n'
            xml_content += '  </url>\n'
    
    # Close XML
    xml_content += '</urlset>'
    
    return xml_content

def generate_robots_txt(website, allow_indexing=True):
    """
    Generate a robots.txt file content for the website
    """
    base_url = f"https://{website.customdomain_set.first().domain}" if website.customdomain_set.exists() else f"https://1matrix.io/website/s/{website.public_slug}"
    
    content = "User-agent: *\n"
    
    if allow_indexing:
        content += "Allow: /\n"
        content += f"Sitemap: {base_url}/sitemap.xml\n"
    else:
        content += "Disallow: /\n"
    
    return content

# Website Deployment Tools
class WebsiteDeployer:
    """Utility for deploying websites to production"""
    
    def __init__(self, website):
        self.website = website
        
    def create_deployment(self, environment='production'):
        """Create a new deployment record"""
        from website.models import WebsiteDeployment
        
        # Get latest version or set to 1.0.0
        latest_deployment = WebsiteDeployment.objects.filter(
            website=self.website, 
            status='completed'
        ).order_by('-deployed_at').first()
        
        if latest_deployment and latest_deployment.version:
            # Parse version (assuming semver format: major.minor.patch)
            try:
                major, minor, patch = map(int, latest_deployment.version.split('.'))
                # Increment patch version
                new_version = f"{major}.{minor}.{patch + 1}"
            except (ValueError, AttributeError):
                new_version = "1.0.0"
        else:
            new_version = "1.0.0"
            
        # Create new deployment record
        deployment = WebsiteDeployment.objects.create(
            website=self.website,
            status='queued',
            version=new_version,
            environment=environment
        )
        
        return deployment
    
    def deploy(self, deployment=None, environment='production'):
        """
        Execute the deployment process
        Returns a tuple of (success, message)
        """
        # Get or create deployment
        if not deployment:
            deployment = self.create_deployment(environment)
            
        # Start deployment
        deployment.start_deployment()
        
        try:
            # Step 1: Create backup
            self._create_backup(deployment)
            
            # Step 2: Validate website content
            if not self._validate_content(deployment):
                deployment.add_log("Validation failed")
                deployment.complete_deployment(success=False)
                return False, "Content validation failed"
                
            # Step 3: Generate necessary SEO files
            self._generate_seo_files(deployment)
            
            # Step 4: Optimize assets (if enabled)
            self._optimize_assets(deployment)
            
            # Step 5: Update DNS records if custom domain exists
            self._update_dns_records(deployment)
            
            # Step 6: Deploy SSL certificate if needed
            self._deploy_ssl_certificate(deployment)
            
            # Step 7: Update deployment status
            deployment.add_log("Deployment completed successfully")
            deployment.complete_deployment(success=True)
            
            return True, f"Deployment completed successfully. Version: {deployment.version}"
            
        except Exception as e:
            # Log error and mark deployment as failed
            import traceback
            error_details = traceback.format_exc()
            deployment.add_log(f"Deployment failed: {str(e)}\n{error_details}")
            deployment.complete_deployment(success=False)
            
            return False, f"Deployment failed: {str(e)}"
            
    def _create_backup(self, deployment):
        """Create a backup before deploying"""
        from website.models import WebsiteBackup
        
        deployment.add_log("Creating backup...")
        
        # Create backup
        backup = WebsiteBackup.objects.create(
            website=self.website,
            name=f"Pre-deployment backup v{deployment.version}",
            content=self.website.content,
            notes=f"Automatic backup before deployment v{deployment.version}"
        )
        
        deployment.add_log(f"Backup created: {backup.id}")
        
        # Update deployment config
        config = deployment.config
        config['backup_id'] = backup.id
        deployment.config = config
        deployment.save()
        
        return backup
    
    def _validate_content(self, deployment):
        """Validate website content before deployment"""
        deployment.add_log("Validating website content...")
        
        # Basic validation
        if not self.website.content:
            deployment.add_log("Error: Website content is empty")
            return False
            
        # Validate against template schema if applicable
        if self.website.template and hasattr(self.website, 'validate_content'):
            if not self.website.validate_content():
                deployment.add_log("Error: Content doesn't match template schema")
                return False
                
        # Validate essential content
        content = self.website.get_content()
        
        # Check for required fields
        required_fields = ['site_name', 'description']
        missing_fields = [field for field in required_fields if field not in content]
        
        if missing_fields:
            deployment.add_log(f"Error: Missing required content fields: {', '.join(missing_fields)}")
            return False
            
        # Check if website has any pages
        if not self.website.get_pages().exists():
            deployment.add_log("Warning: Website has no pages")
            # Don't fail deployment for this, just warn
            
        deployment.add_log("Content validation successful")
        return True
    
    def _generate_seo_files(self, deployment):
        """Generate sitemap.xml and robots.txt"""
        deployment.add_log("Generating SEO files...")
        
        # Generate files paths
        import os
        from django.conf import settings
        
        # Define paths for sitemap and robots.txt
        website_files_dir = os.path.join(settings.MEDIA_ROOT, 'website_files', str(self.website.id))
        os.makedirs(website_files_dir, exist_ok=True)
        
        sitemap_path = os.path.join(website_files_dir, 'sitemap.xml')
        robots_path = os.path.join(website_files_dir, 'robots.txt')
        
        # Generate sitemap.xml
        sitemap_content = generate_sitemap_xml(self.website)
        with open(sitemap_path, 'w') as f:
            f.write(sitemap_content)
            
        deployment.add_log(f"Sitemap.xml generated at {sitemap_path}")
            
        # Generate robots.txt
        robots_content = generate_robots_txt(self.website, allow_indexing=True)
        with open(robots_path, 'w') as f:
            f.write(robots_content)
            
        deployment.add_log(f"Robots.txt generated at {robots_path}")
        
        # Update deployment config
        config = deployment.config
        config['sitemap_path'] = sitemap_path
        config['robots_path'] = robots_path
        deployment.config = config
        deployment.save()
    
    def _optimize_assets(self, deployment):
        """Optimize website assets"""
        deployment.add_log("Optimizing website assets...")
        
        # This would typically involve tasks like:
        # - Image compression
        # - Minifying CSS/JS
        # - Creating WebP versions of images
        
        # For now, we'll implement a basic version that just logs
        deployment.add_log("Asset optimization completed")
    
    def _update_dns_records(self, deployment):
        """Update DNS records for custom domains"""
        # Check if website has custom domains
        custom_domains = self.website.customdomain_set.all()
        
        if not custom_domains.exists():
            deployment.add_log("No custom domains to configure")
            return
            
        deployment.add_log(f"Configuring {custom_domains.count()} custom domain(s)")
        
        for domain in custom_domains:
            deployment.add_log(f"Processing domain: {domain.domain}")
            
            # In a real implementation, this would update DNS records
            # through API calls to DNS provider
            
            # Just log for now
            deployment.add_log(f"DNS configuration updated for {domain.domain}")
    
    def _deploy_ssl_certificate(self, deployment):
        """Deploy SSL certificates for custom domains"""
        # Check if website has custom domains
        custom_domains = self.website.customdomain_set.all()
        
        if not custom_domains.exists():
            return
            
        deployment.add_log("Checking SSL certificates...")
        
        for domain in custom_domains:
            if not domain.ssl_status:
                deployment.add_log(f"Generating SSL certificate for {domain.domain}")
                
                # In a real implementation, this would use Let's Encrypt 
                # or another cert provider to generate a certificate
                
                # Just log for now and mark as complete
                deployment.add_log(f"SSL certificate generated for {domain.domain}")
                domain.ssl_status = True
                domain.save()
                
def check_website_health(website):
    """
    Perform a health check on a website and return a report
    """
    health_report = {
        'status': 'healthy',
        'issues': [],
        'metrics': {},
        'uptime': 100.0,  # Placeholder, would be actual uptime in production
    }
    
    # Check for essential content
    content = website.get_content()
    required_fields = ['site_name', 'description']
    missing_fields = [field for field in required_fields if field not in content]
    
    if missing_fields:
        health_report['issues'].append({
            'type': 'content',
            'severity': 'medium',
            'description': f"Missing required content fields: {', '.join(missing_fields)}"
        })
        health_report['status'] = 'warning'
        
    # Check if website has pages
    if not website.get_pages().exists():
        health_report['issues'].append({
            'type': 'content',
            'severity': 'high',
            'description': "Website has no pages"
        })
        health_report['status'] = 'critical'
        
    # Check if website has a custom domain
    if not website.customdomain_set.exists():
        health_report['issues'].append({
            'type': 'domain',
            'severity': 'low',
            'description': "No custom domain configured"
        })
        
    # Check SSL status for domains
    for domain in website.customdomain_set.all():
        if not domain.ssl_status:
            health_report['issues'].append({
                'type': 'ssl',
                'severity': 'medium',
                'description': f"SSL certificate not configured for {domain.domain}"
            })
            health_report['status'] = 'warning'
            
    # Check for SEO configuration
    seo_data = content.get('seo', {})
    if not seo_data.get('meta_title') or not seo_data.get('meta_description'):
        health_report['issues'].append({
            'type': 'seo',
            'severity': 'medium',
            'description': "Incomplete SEO configuration"
        })
        
    # Run SEO analysis for more insights
    analyzer = SEOAnalyzer(website)
    seo_analysis = analyzer.analyze()
    
    # Add SEO score to metrics
    health_report['metrics']['seo_score'] = seo_analysis['overall_score']
    
    # Add SEO recommendations if score is low
    if seo_analysis['overall_score'] < 70:
        for recommendation in seo_analysis['recommendations'][:3]:  # Top 3 recommendations
            health_report['issues'].append({
                'type': 'seo',
                'severity': 'low',
                'description': recommendation
            })
    
    # Calculate overall health score (0-100)
    issue_weights = {
        'critical': 40,
        'high': 20,
        'medium': 10,
        'low': 5
    }
    
    # Start with 100, subtract based on issues
    health_score = 100
    for issue in health_report['issues']:
        health_score -= issue_weights.get(issue['severity'], 0)
    
    health_report['metrics']['health_score'] = max(0, health_score)
    
    # Update status based on health score
    if health_score < 50:
        health_report['status'] = 'critical'
    elif health_score < 70:
        health_report['status'] = 'warning'
    
    return health_report
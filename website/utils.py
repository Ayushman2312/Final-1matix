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
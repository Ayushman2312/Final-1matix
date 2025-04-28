import dns.resolver
from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import datetime

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
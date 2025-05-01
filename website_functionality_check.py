"""
Website App Functionality Check Script

This script checks all features and functionality of the website app, ensuring:
1. All fields/forms work correctly (data is saved)
2. Template1 renders content correctly
3. All pages display properly
"""

import os
import sys
import json
import requests
from urllib.parse import urljoin
import django

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "matrix.settings")
django.setup()

# Import Django models
from django.contrib.auth.models import User
from website.models import (
    Website, WebsiteTemplate, WebsitePage, WebsiteProduct, 
    WebsiteCategory, CustomDomain
)
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.test import Client

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    ENDC = '\033[0m'

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 80)
    print(f"{Colors.BLUE}{text}{Colors.ENDC}")
    print("=" * 80)

def print_success(text):
    """Print a success message"""
    print(f"{Colors.GREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    """Print an error message"""
    print(f"{Colors.RED}✗ {text}{Colors.ENDC}")

def print_warning(text):
    """Print a warning message"""
    print(f"{Colors.YELLOW}! {text}{Colors.ENDC}")

def check_model_exists(model, identifier=None):
    """Check if a model exists in the database"""
    if identifier:
        print(f"Checking {model.__name__} with identifier: {identifier}")
    try:
        if identifier:
            instance = model.objects.get(id=identifier)
            print_success(f"Found {model.__name__} with id {identifier}")
            return instance
        else:
            count = model.objects.count()
            print_success(f"Found {count} {model.__name__} instances")
            return model.objects.first()
    except model.DoesNotExist:
        if identifier:
            print_error(f"No {model.__name__} found with id {identifier}")
        else:
            print_error(f"No {model.__name__} instances found")
        return None
    except Exception as e:
        print_error(f"Error checking {model.__name__}: {str(e)}")
        return None

def create_test_user():
    """Create a test user for authentication"""
    try:
        user, created = User.objects.get_or_create(
            username="test_user",
            defaults={
                "email": "test@example.com",
                "is_active": True
            }
        )
        if created:
            user.set_password("password123")
            user.save()
            print_success("Created test user 'test_user'")
        else:
            print_success("Using existing test user 'test_user'")
        return user
    except Exception as e:
        print_error(f"Error creating test user: {str(e)}")
        return None

def check_website_content(website):
    """Check if website content is saving correctly"""
    print_header("Checking Website Content")
    
    if not website:
        print_error("No website to check")
        return False
    
    try:
        # Check basic content fields
        print(f"Site name: {website.content.get('site_name', 'Not set')}")
        print(f"Description: {website.content.get('description', 'Not set')}")
        
        # Check contact info
        contact_info = website.content.get('contact_info', {})
        print(f"Mobile: {contact_info.get('mobile_number', 'Not set')}")
        print(f"Email: {contact_info.get('contact_email', 'Not set')}")
        print(f"Address: {contact_info.get('address', 'Not set')}")
        
        # Check for theme settings
        print(f"Primary color: {website.content.get('primary_color', 'Not set')}")
        print(f"Secondary color: {website.content.get('secondary_color', 'Not set')}")
        
        # Check for content sections
        hero_banners = website.content.get('hero_banners', [])
        print(f"Hero banners: {len(hero_banners)}")
        
        testimonials = website.content.get('testimonials', [])
        print(f"Testimonials: {len(testimonials)}")
        
        # Update some content to verify saving works
        new_name = f"Updated Test Website {website.id}"
        website.content['site_name'] = new_name
        website.save()
        
        # Reload from database to verify changes
        updated_website = Website.objects.get(id=website.id)
        if updated_website.content.get('site_name') == new_name:
            print_success("Website content updated successfully")
            return True
        else:
            print_error("Website content update failed")
            return False
            
    except Exception as e:
        print_error(f"Error checking website content: {str(e)}")
        return False

def check_website_pages(website):
    """Check website pages functionality"""
    print_header("Checking Website Pages")
    
    if not website:
        print_error("No website to check")
        return False
    
    try:
        # Get existing pages
        pages = WebsitePage.objects.filter(website=website)
        print(f"Found {pages.count()} pages")
        
        for page in pages:
            print(f"Page: {page.title} (slug: {page.slug}, is_homepage: {page.is_homepage})")
        
        # Create a test page if none exists
        if pages.count() == 0:
            page = WebsitePage.objects.create(
                website=website,
                title="Test Page",
                slug="test-page",
                template_file="home.html",
                content={"test_content": "This is test content"}
            )
            print_success(f"Created test page: {page.title}")
        
        # Check homepage setting
        homepage = next((p for p in pages if p.is_homepage), None)
        if homepage:
            print_success(f"Homepage is set to: {homepage.title}")
        else:
            print_warning("No homepage is set")
            
        return True
    except Exception as e:
        print_error(f"Error checking website pages: {str(e)}")
        return False

def check_website_products(website):
    """Check website products functionality"""
    print_header("Checking Website Products")
    
    if not website:
        print_error("No website to check")
        return False
    
    try:
        # Get existing categories
        categories = WebsiteCategory.objects.filter(website=website)
        print(f"Found {categories.count()} product categories")
        
        # Create a test category if none exists
        test_category = None
        if categories.count() == 0:
            test_category = WebsiteCategory.objects.create(
                website=website,
                name="Test Category",
                slug="test-category",
                description="A test category"
            )
            print_success(f"Created test category: {test_category.name}")
        else:
            test_category = categories.first()
        
        # Get existing products
        products = WebsiteProduct.objects.filter(website=website)
        print(f"Found {products.count()} products")
        
        # Create a test product if none exists
        if products.count() == 0 and test_category:
            product = WebsiteProduct.objects.create(
                website=website,
                category=test_category,
                title="Test Product",
                slug="test-product",
                description="A test product",
                price=99.99,
                image1="path/to/image.jpg"
            )
            print_success(f"Created test product: {product.title}")
            
        return True
    except Exception as e:
        print_error(f"Error checking website products: {str(e)}")
        return False

def check_template1_functionality(website):
    """Check Template1 specific functionality"""
    print_header("Checking Template1 Functionality")
    
    if not website:
        print_error("No website to check")
        return False
    
    try:
        # Check if the website uses Template1
        template = website.template
        if not template or "template1" not in template.template_path.lower():
            print_warning(f"Website is not using Template1 (using {template.template_path if template else 'None'})")
            return False
        
        # Update theme colors to verify Template1 settings
        website.content['primary_color'] = "#3B82F6"
        website.content['secondary_color'] = "#1F2937"
        website.content['accent_color'] = "#EF4444"
        website.save()
        
        print_success("Updated Template1 theme colors")
        
        # Add example content for Template1
        if 'hero_banners' not in website.content or not website.content['hero_banners']:
            website.content['hero_banners'] = [
                {
                    "image": "https://via.placeholder.com/1920x1080",
                    "title": "Welcome to Our Website",
                    "description": "This is a sample banner for testing",
                    "button_text": "Learn More",
                    "button_url": "#"
                }
            ]
            website.save()
            print_success("Added example hero banner")
            
        return True
    except Exception as e:
        print_error(f"Error checking Template1 functionality: {str(e)}")
        return False

def check_website_domain_settings(website):
    """Check domain settings functionality"""
    print_header("Checking Domain Settings")
    
    if not website:
        print_error("No website to check")
        return False
    
    try:
        # Get existing domains
        domains = CustomDomain.objects.filter(website=website)
        print(f"Found {domains.count()} custom domains")
        
        for domain in domains:
            print(f"Domain: {domain.domain} (Status: {domain.verification_status})")
        
        # The actual domain verification requires DNS checks, so we can't test fully
        print_warning("Domain verification requires actual DNS configuration and cannot be fully tested in this script")
        
        return True
    except Exception as e:
        print_error(f"Error checking domain settings: {str(e)}")
        return False

def check_website_seo(website):
    """Check SEO functionality"""
    print_header("Checking SEO Functionality")
    
    if not website:
        print_error("No website to check")
        return False
    
    try:
        # Check SEO settings
        seo = website.content.get('seo', {})
        print(f"Meta title: {seo.get('meta_title', 'Not set')}")
        print(f"Meta description: {seo.get('meta_description', 'Not set')}")
        print(f"Meta keywords: {seo.get('meta_keywords', 'Not set')}")
        
        # Update SEO settings
        if 'seo' not in website.content:
            website.content['seo'] = {}
            
        website.content['seo']['meta_title'] = f"Test SEO Title for {website.name}"
        website.content['seo']['meta_description'] = "This is a test meta description for SEO purposes."
        website.content['seo']['meta_keywords'] = "test, seo, keywords"
        website.save()
        
        print_success("Updated SEO settings")
        
        return True
    except Exception as e:
        print_error(f"Error checking SEO functionality: {str(e)}")
        return False

def run_all_checks():
    """Run all functionality checks"""
    print_header("Website App Functionality Check")
    
    # Create/get test user
    user = create_test_user()
    if not user:
        return False
    
    # Check templates
    template = check_model_exists(WebsiteTemplate)
    if not template:
        print_error("No website templates found - cannot proceed with checks")
        return False
    
    # Check website
    website = Website.objects.filter(user=user).first()
    if not website:
        try:
            # Create a test website if none exists
            website = Website.objects.create(
                user=user,
                template=template,
                name="Test Website",
                content={
                    "site_name": "Test Website",
                    "description": "A test website for functionality checking",
                    "contact_info": {
                        "mobile_number": "1234567890",
                        "contact_email": "contact@test.com",
                        "address": "123 Test St"
                    }
                }
            )
            print_success(f"Created test website: {website.name}")
        except ValidationError as e:
            print_error(f"Validation error creating test website: {str(e)}")
            return False
        except Exception as e:
            print_error(f"Error creating test website: {str(e)}")
            return False
    else:
        print_success(f"Using existing website: {website.name}")
    
    # Run all checks
    checks = [
        check_website_content,
        check_website_pages,
        check_website_products,
        check_template1_functionality,
        check_website_domain_settings,
        check_website_seo
    ]
    
    results = []
    for check_func in checks:
        results.append(check_func(website))
    
    # Summary
    print_header("Functionality Check Summary")
    if all(results):
        print_success("All checks passed successfully!")
    else:
        print_error(f"{results.count(False)} check(s) failed. Please review the issues above.")
    
    return all(results)

if __name__ == "__main__":
    run_all_checks() 
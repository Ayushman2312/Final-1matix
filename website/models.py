from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from jsonschema import validate as json_validate
import os
import uuid
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError

# Create your models here.

class WebsiteTemplate(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    preview_image = models.ImageField(upload_to='template_previews/')
    template_path = models.CharField(max_length=255)
    content_schema = models.JSONField(help_text="JSON schema defining the expected content structure", default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
    
    def get_template_pages(self):
        """Returns list of available HTML files in the template directory"""
        # Create a path that's OS-appropriate
        template_dir = os.path.normpath(os.path.join('templates', self.template_path.strip('/')))
        
        # Check if directory exists
        if not os.path.isdir(template_dir):
            return []
        
        try:
            pages = []
            for file in os.listdir(template_dir):
                if file.endswith('.html') and file != 'base.html':
                    page_name = file.split('.')[0]
                    pages.append({
                        'file': file,
                        'name': page_name.replace('-', ' ').title(),
                        'slug': page_name
                    })
            return pages
        except (FileNotFoundError, PermissionError, NotADirectoryError):
            # Handle any potential filesystem errors
            return []

class Website(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    template = models.ForeignKey(WebsiteTemplate, on_delete=models.PROTECT, null=True, blank=True)
    content = models.JSONField(default=dict, help_text="Structured content for the website")
    public_slug = models.SlugField(max_length=100, unique=True, null=True, blank=True, help_text="Public URL slug for sharing")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user'], name='one_website_per_user')
        ]

    def __str__(self):
        return f"{self.user.username}'s website - {self.template.name}" if self.template else f"{self.user.username}'s website"

    def clean(self):
        super().clean()
        # Check for existing website, whether creating new or updating
        existing_website = Website.objects.filter(user=self.user)
        if self.pk:  # If updating
            existing_website = existing_website.exclude(pk=self.pk)
        
        if existing_website.exists():
            raise ValidationError('User already has a website. Only one website per user is allowed.')

    def save(self, *args, **kwargs):
        # Run full validation before saving
        self.full_clean()
        
        if not self.public_slug:
            # Generate a unique slug based on the website name
            base_slug = slugify(self.content.get('site_name', f"{self.user.username}'s Website"))
            unique_id = str(uuid.uuid4())[:8]
            self.public_slug = f"{base_slug}-{unique_id}"

        # Ensure content is a dictionary
        if self.content is None:
            self.content = {}

        # Initialize default content fields if they don't exist
        default_content = {
            'site_name': self.content.get('site_name', f"{self.user.username}'s Website"),
            'websiteName': self.content.get('websiteName', f"{self.user.username}'s Website"),
            'description': self.content.get('description', 'Welcome to our website'),
            'top_seller_title': self.content.get('top_seller_title', 'Top Selling Products'),
            'featured_products_title': self.content.get('featured_products_title', 'Featured Products'),
            'new_arrivals_title': self.content.get('new_arrivals_title', 'New Arrivals'),
            'about_section_title': self.content.get('about_section_title', 'About Us'),
            'contact_section_title': self.content.get('contact_section_title', 'Contact Us'),
            'footer_description': self.content.get('footer_description', 'Your trusted online store'),
            'hero_banners': self.content.get('hero_banners', [
                {
                    'image': 'https://via.placeholder.com/1920x1080',
                    'title': 'Welcome to Our Store',
                    'description': 'Discover amazing products at great prices',
                    'button_text': 'Shop Now',
                    'button_url': '/shop'
                }
            ])
        }

        # Initialize contact information if it doesn't exist
        if 'contact_info' not in self.content:
            self.content['contact_info'] = {
                'mobile_number': self.content.get('mobile_number', ''),
                'contact_email': self.content.get('contact_email', ''),
                'address': self.content.get('address', ''),
                'map_location': self.content.get('map_location', '')
            }
        else:
            # Update contact info with any new values from the form
            self.content['contact_info'].update({
                'mobile_number': self.content.get('mobile_number', self.content['contact_info'].get('mobile_number', '')),
                'contact_email': self.content.get('contact_email', self.content['contact_info'].get('contact_email', '')),
                'address': self.content.get('address', self.content['contact_info'].get('address', '')),
                'map_location': self.content.get('map_location', self.content['contact_info'].get('map_location', ''))
            })

        # Update content with default values while preserving existing ones
        for key, value in default_content.items():
            if key not in self.content:
                self.content[key] = value
            
        # Initialize SEO fields if they don't exist
        if 'seo' not in self.content:
            self.content['seo'] = {
                'meta_title': self.content.get('site_name', '') + ' - Official Website',
                'meta_description': '',
                'meta_keywords': '',
                'og_title': '',
                'og_description': '',
                'og_image': '',
                'structured_data': {
                    'organization': {
                        'name': self.content.get('site_name', ''),
                        'url': '',
                        'logo': '',
                        'description': ''
                    }
                },
                'social_links': {
                    'facebook': '',
                    'twitter': '',
                    'instagram': '',
                    'linkedin': '',
                    'youtube': ''
                }
            }
        
        # Make sure content is a new dictionary to avoid reference issues
        self.content = dict(self.content)
        
        # Make sure force_update is honored if passed
        force_update = kwargs.pop('force_update', False)
        if force_update:
            kwargs['force_update'] = True
            
        # Call the parent save method
        super().save(*args, **kwargs)

    def get_public_url(self):
        """Return the public shareable URL for this website"""
        if not self.public_slug or self.public_slug == 'None':
            # If for some reason the public_slug is still None, regenerate it and save
            self.save()
        return f"/website/s/{self.public_slug}/"
    
    def validate_content(self):
        """Validate content against template schema"""
        try:
            json_validate(instance=self.content, schema=self.template.content_schema)
            return True
        except Exception as e:
            return False
    
    def get_pages(self):
        """Get all pages for this website"""
        return WebsitePage.objects.filter(website=self)

    def update_seo_content(self, seo_data):
        """Update SEO content with validation"""
        if not isinstance(self.content, dict):
            self.content = {}
        
        if 'seo' not in self.content:
            self.content['seo'] = {}
        
        # Update SEO fields
        self.content['seo'].update({
            'meta_title': seo_data.get('meta_title', ''),
            'meta_description': seo_data.get('meta_description', ''),
            'meta_keywords': seo_data.get('meta_keywords', ''),
            'og_title': seo_data.get('og_title', ''),
            'og_description': seo_data.get('og_description', ''),
            'og_image': seo_data.get('og_image', ''),
            'structured_data': {
                'organization': {
                    'name': seo_data.get('organization_name', ''),
                    'url': seo_data.get('organization_url', ''),
                    'logo': seo_data.get('organization_logo', ''),
                    'description': seo_data.get('organization_description', '')
                }
            },
            'social_links': {
                'facebook': seo_data.get('facebook_url', ''),
                'twitter': seo_data.get('twitter_url', ''),
                'instagram': seo_data.get('instagram_url', ''),
                'linkedin': seo_data.get('linkedin_url', ''),
                'youtube': seo_data.get('youtube_url', '')
            }
        })
        
        self.save(force_update=True)

class WebsitePage(models.Model):
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='pages')
    title = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)
    template_file = models.CharField(max_length=255, help_text="HTML template file name")
    content = models.JSONField(default=dict, help_text="Page-specific content")
    is_homepage = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('website', 'slug')
        ordering = ['order', 'title']

    def __str__(self):
        return f"{self.title} - {self.website}"

    def save(self, *args, **kwargs):
        # Ensure only one homepage exists per website
        if self.is_homepage:
            WebsitePage.objects.filter(website=self.website, is_homepage=True).exclude(pk=self.pk).update(is_homepage=False)
        
        # Ensure content is a dictionary
        if self.content is None:
            self.content = {}
            
        super().save(*args, **kwargs)

class CustomDomain(models.Model):
    VERIFICATION_STATUS = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('failed', 'Failed'),
    )

    website = models.ForeignKey(Website, on_delete=models.CASCADE)
    domain = models.CharField(
        max_length=255,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$',
                message='Enter a valid domain name',
            ),
        ]
    )
    verification_status = models.CharField(
        max_length=10,
        choices=VERIFICATION_STATUS,
        default='pending'
    )
    verification_code = models.CharField(max_length=64, unique=True)
    ssl_status = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.domain

class DomainLog(models.Model):
    domain = models.CharField(max_length=255)
    status_code = models.IntegerField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.domain} - {self.status_code}"

# New models for Website Product Management

class WebsiteCategory(models.Model):
    """Category model specific for website products"""
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='website_categories/', blank=True, null=True)
    parent = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='subcategories')
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Website Categories"
        ordering = ['order', 'name']
        unique_together = ('website', 'slug')

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class WebsiteProduct(models.Model):
    """Product model specific for website"""
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(WebsiteCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    product_id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False, unique=True)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image1 = models.ImageField(upload_to='website_products/')
    image2 = models.ImageField(upload_to='website_products/', blank=True, null=True)
    image3 = models.ImageField(upload_to='website_products/', blank=True, null=True)
    image4 = models.ImageField(upload_to='website_products/', blank=True, null=True)
    hsn_code = models.CharField(max_length=255, blank=True, null=True)
    gst_percentage = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    variants = models.JSONField(null=True, blank=True)
    specifications = models.JSONField(null=True, blank=True, help_text="Product specifications as key-value pairs")
    video_link = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('website', 'slug')

    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)


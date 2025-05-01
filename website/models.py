from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
from jsonschema import validate as json_validate
import os
import uuid
from django.utils.text import slugify
from django.utils import timezone
from django.core.exceptions import ValidationError
import json

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
    name = models.CharField(max_length=100, default="My Website")
    content = models.JSONField(default=dict)
    public_slug = models.SlugField(max_length=100, unique=True, null=True, blank=True, help_text="Public URL slug for sharing")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deployed = models.BooleanField(default=False)
    last_deployed = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user'], name='one_website_per_user')
        ]

    def __str__(self):
        return self.name

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
            base_slug = slugify(self.name)
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
            'about_section_subtitle': self.content.get('about_section_subtitle', 'Our Story'),
            'about_section_content': self.content.get('about_section_content', 'Tell your story here. Share your mission, values, and what makes your business unique.'),
            'contact_section_title': self.content.get('contact_section_title', 'Contact Us'),
            'footer_description': self.content.get('footer_description', 'Your trusted online store'),
            'testimonials_title': self.content.get('testimonials_title', 'What Our Customers Say'),
            'about_button': self.content.get('about_button', {
                'label': 'Learn More',
                'url': '#'
            }),
            'hero_banners': self.content.get('hero_banners', [
                {
                    'image': 'https://via.placeholder.com/1920x1080',
                    'title': 'Welcome to Our Store',
                    'description': 'Discover amazing products at great prices',
                    'button_text': 'Shop Now',
                    'button_url': '/shop'
                }
            ]),
            'testimonials': self.content.get('testimonials', [
                {
                    'name': 'John Doe',
                    'position': 'CEO, Example Inc',
                    'content': 'This is a sample testimonial. Add real customer reviews here to build trust.',
                    'rating': 5,
                    'avatar': ''
                }
            ]),
            'theme': self.content.get('theme', {
                'colors': {
                    'primary': '#3b82f6',
                    'secondary': '#6b7280',
                    'accent': '#f59e0b',
                    'background': '#ffffff',
                    'text': '#1f2937',
                    'isDark': False
                },
                'typography': {
                    'headingFont': 'Poppins',
                    'bodyFont': 'Open Sans'
                }
            })
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

    def get_content(self):
        """Returns the content as a Python dictionary"""
        if isinstance(self.content, str):
            return json.loads(self.content)
        return self.content
    
    def set_content(self, content_dict):
        """Sets the content from a Python dictionary"""
        if isinstance(content_dict, dict):
            self.content = content_dict
        else:
            self.content = json.dumps(content_dict)
    
    @property
    def slides(self):
        """Returns the slides from the content"""
        content = self.get_content()
        return content.get('slides', [])

    def is_complete(self):
        """Check if the website has the minimum required content for deployment"""
        content = self.get_content()
        
        # Basic checks for required content
        if not content.get('site_name'):
            return False
            
        # Check if contact information is present
        contact_info = content.get('contact_info', {})
        if not contact_info.get('contact_email') and not contact_info.get('mobile_number'):
            return False
            
        # Ensure there's at least some content
        if not content.get('description'):
            return False
            
        # Check for at least one page
        if not self.get_pages().exists():
            return False
            
        return True

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

class WebsiteDeployment(models.Model):
    """Tracks website deployments and their status"""
    DEPLOYMENT_STATUS = (
        ('queued', 'Queued'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )
    
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='deployments')
    status = models.CharField(max_length=20, choices=DEPLOYMENT_STATUS, default='queued')
    version = models.CharField(max_length=20, blank=True, null=True)
    environment = models.CharField(max_length=50, default='production')
    logs = models.TextField(blank=True, null=True)
    deployed_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Deployment configurations
    config = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-deployed_at']
    
    def __str__(self):
        return f"Deployment {self.id} for {self.website.name} - {self.status}"
    
    def save(self, *args, **kwargs):
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        super().save(*args, **kwargs)
        
    def add_log(self, message):
        """Add a log message to deployment logs"""
        timestamp = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {message}\n"
        
        if not self.logs:
            self.logs = log_entry
        else:
            self.logs += log_entry
            
        self.save(update_fields=['logs'])
    
    def get_duration(self):
        """Get deployment duration in seconds"""
        if self.completed_at:
            return (self.completed_at - self.deployed_at).total_seconds()
        return None
        
    def start_deployment(self):
        """Start deployment process"""
        self.status = 'in_progress'
        self.add_log("Deployment started")
        self.save()
        
    def complete_deployment(self, success=True):
        """Mark deployment as complete"""
        self.status = 'completed' if success else 'failed'
        self.completed_at = timezone.now()
        self.add_log(f"Deployment {'completed successfully' if success else 'failed'}")
        self.save()

class WebsiteBackup(models.Model):
    """Stores website backups"""
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='backups')
    name = models.CharField(max_length=100)
    content = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Backup: {self.name} - {self.created_at.strftime('%Y-%m-%d %H:%M:%S')}"
    
    def restore(self):
        """Restore website content from this backup"""
        self.website.content = self.content
        self.website.save()
        return True

class WebsiteTheme(models.Model):
    """Pre-configured theme settings that can be applied to a website"""
    name = models.CharField(max_length=100)
    preview_image = models.ImageField(upload_to='theme_previews/', blank=True, null=True)
    description = models.TextField(blank=True)
    color_scheme = models.JSONField(help_text="JSON containing color scheme information", default=dict)
    typography = models.JSONField(help_text="JSON containing typography settings", default=dict)
    layout_settings = models.JSONField(help_text="JSON containing layout settings", default=dict)
    component_styles = models.JSONField(help_text="JSON containing component styles", default=dict)
    template = models.ForeignKey(WebsiteTemplate, on_delete=models.SET_NULL, null=True, blank=True, 
                                related_name='themes', help_text="Associated template if theme is template-specific")
    is_premium = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    def apply_to_website(self, website):
        """Apply theme settings to a website"""
        # Get current content
        content = website.get_content()
        
        # Apply theme settings
        if not 'theme' in content:
            content['theme'] = {}
            
        # Apply color scheme
        content['theme']['colors'] = self.color_scheme
        
        # Apply typography
        content['theme']['typography'] = self.typography
        
        # Apply layout settings
        content['theme']['layout'] = self.layout_settings
        
        # Apply component styles
        content['theme']['components'] = self.component_styles
        
        # Save changes
        website.set_content(content)
        website.save()
        
        return True
        
class WebsiteFont(models.Model):
    """Available fonts for website customization"""
    FONT_TYPES = (
        ('google', 'Google Font'),
        ('custom', 'Custom Font'),
        ('system', 'System Font'),
    )
    
    name = models.CharField(max_length=100)
    font_family = models.CharField(max_length=100)
    font_type = models.CharField(max_length=20, choices=FONT_TYPES, default='google')
    url = models.URLField(blank=True, null=True, help_text="URL for loading font if not a system font")
    weights_available = models.CharField(max_length=100, default="400,700", help_text="Comma-separated list of available weights")
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    def get_font_import_code(self):
        """Get CSS code for importing this font"""
        if self.font_type == 'google':
            weights = self.weights_available.replace(' ', '')
            return f'@import url("https://fonts.googleapis.com/css2?family={self.font_family.replace(" ", "+")}&display=swap");'
        elif self.font_type == 'custom' and self.url:
            return f'@import url("{self.url}");'
        else:
            return ""  # System fonts don't need imports
            
class WebsiteColorScheme(models.Model):
    """Predefined color schemes for websites"""
    name = models.CharField(max_length=100)
    primary_color = models.CharField(max_length=20, help_text="Primary brand color (hex code)")
    secondary_color = models.CharField(max_length=20, help_text="Secondary brand color (hex code)")
    accent_color = models.CharField(max_length=20, help_text="Accent color for highlights (hex code)")
    background_color = models.CharField(max_length=20, help_text="Main background color (hex code)")
    text_color = models.CharField(max_length=20, help_text="Main text color (hex code)")
    link_color = models.CharField(max_length=20, help_text="Link color (hex code)")
    button_color = models.CharField(max_length=20, help_text="Button color (hex code)")
    button_text_color = models.CharField(max_length=20, help_text="Button text color (hex code)")
    header_color = models.CharField(max_length=20, help_text="Header background color (hex code)")
    footer_color = models.CharField(max_length=20, help_text="Footer background color (hex code)")
    is_dark = models.BooleanField(default=False, help_text="Is this a dark theme?")
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    def get_colors_dict(self):
        """Return colors as dictionary for easy application to website content"""
        return {
            'primary': self.primary_color,
            'secondary': self.secondary_color,
            'accent': self.accent_color,
            'background': self.background_color,
            'text': self.text_color,
            'link': self.link_color,
            'button': self.button_color,
            'buttonText': self.button_text_color,
            'header': self.header_color,
            'footer': self.footer_color,
            'isDark': self.is_dark
        }
        
    def apply_to_website(self, website):
        """Apply this color scheme to a website"""
        content = website.get_content()
        
        if not 'theme' in content:
            content['theme'] = {}
            
        content['theme']['colors'] = self.get_colors_dict()
        
        website.set_content(content)
        website.save()
        
        return True

class WebsiteAsset(models.Model):
    """Store custom assets for website (logos, icons, banners, etc.)"""
    ASSET_TYPES = (
        ('logo', 'Logo'),
        ('favicon', 'Favicon'),
        ('banner', 'Banner'),
        ('hero', 'Hero Image'),
        ('background', 'Background Image'),
        ('icon', 'Icon'),
        ('custom', 'Custom Asset'),
    )
    
    website = models.ForeignKey(Website, on_delete=models.CASCADE, related_name='assets')
    name = models.CharField(max_length=100)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPES, default='custom')
    file = models.FileField(upload_to='website_assets/')
    alt_text = models.CharField(max_length=255, blank=True, help_text="Alternative text for accessibility")
    width = models.PositiveIntegerField(blank=True, null=True, help_text="Width in pixels")
    height = models.PositiveIntegerField(blank=True, null=True, help_text="Height in pixels")
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.name} ({self.get_asset_type_display()})"
        
    def get_url(self):
        """Get the asset URL"""
        return self.file.url


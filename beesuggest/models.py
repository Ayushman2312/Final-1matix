from django.db import models
from django.contrib.auth.models import User
import uuid

# Create your models here.

class ProductDetails(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    
    # Keywords
    focus_keywords = models.CharField(max_length=255, blank=True)
    alt_keyword_1 = models.CharField(max_length=255, blank=True)
    alt_keyword_2 = models.CharField(max_length=255, blank=True)

    # Product Title and Short Description
    product_title = models.CharField(max_length=255, blank=True)
    short_description = models.TextField(max_length=300, blank=True, help_text="Short description limited to approximately 60 words")

    # Images
    product_image_1 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    product_image_1_alt = models.CharField(max_length=255, blank=True)
    product_image_2 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    product_image_2_alt = models.CharField(max_length=255, blank=True)
    product_image_3 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    product_image_3_alt = models.CharField(max_length=255, blank=True)
    product_image_4 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    product_image_4_alt = models.CharField(max_length=255, blank=True)
    product_image_5 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    product_image_5_alt = models.CharField(max_length=255, blank=True)

    # Video URLs
    video_url_1 = models.URLField(max_length=200, blank=True)
    video_url_2 = models.URLField(max_length=200, blank=True)
    video_url_3 = models.URLField(max_length=200, blank=True)

    # Description
    product_description = models.TextField(max_length=1000, blank=True)

    # Variation Fields
    variations = models.JSONField(blank=True, null=True, default=list)

    # Usage
    uses = models.TextField(blank=True)
    best_suited_for = models.TextField(blank=True)

    # Contact & Social Media
    social_media_facebook = models.URLField(max_length=200, blank=True)
    social_media_twitter = models.URLField(max_length=200, blank=True)
    social_media_instagram = models.URLField(max_length=200, blank=True)
    website_url = models.URLField(max_length=200, blank=True)
    contact_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)

    # Organization Details
    organization = models.CharField(max_length=255, blank=True)
    gst_details = models.CharField(max_length=100, blank=True)
    map_location = models.URLField(max_length=200, blank=True)

    # FAQ
    faqs = models.JSONField(blank=True, null=True, default=list)

    # Miscellaneous
    size_chart = models.FileField(upload_to='size_charts/', blank=True, null=True)
    why_choose_us = models.TextField(blank=True)
    
    # New comparison structure - Dynamic comparisons
    comparisons = models.JSONField(blank=True, null=True, default=list, help_text="Dynamic comparison data with 'us' and 'others' fields")
    
    # Keep old comparison field for backward compatibility
    comparison = models.TextField(blank=True, help_text="Legacy comparison field - will be migrated to comparisons field")

    # Status for admin review
    is_published = models.BooleanField(default=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    published_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Product Details for {self.organization or self.user.username} ({self.user.email})"

    class Meta:
        verbose_name = "Product Detail"
        verbose_name_plural = "Product Details"
        ordering = ['-submitted_at']

    @property
    def get_images(self):
        """Return a list of all product images"""
        images = []
        for i in range(1, 6):
            image = getattr(self, f'product_image_{i}')
            alt = getattr(self, f'product_image_{i}_alt')
            if image:
                images.append({
                    'image': image.url,
                    'alt': alt or f'Product image {i}'
                })
        return images

    @property
    def get_variations_list(self):
        """Return variations as a formatted list"""
        if self.variations:
            formatted_list = []
            for var in self.variations:
                name = var.get('name', '')
                values = var.get('values', [])
                if name and values:
                    formatted_list.append(f"{name}: {', '.join(values)}")
            return formatted_list
        return []

    @property
    def get_faqs_list(self):
        """Return FAQs as a formatted list"""
        if self.faqs:
            return [{'question': faq.get('question', ''), 'answer': faq.get('answer', '')} for faq in self.faqs if faq.get('question') and faq.get('answer')]
        return []

    @property
    def get_comparisons_list(self):
        """Return comparisons as a formatted list"""
        if self.comparisons:
            return [{'us': comp.get('us', ''), 'others': comp.get('others', '')} for comp in self.comparisons if comp.get('us') or comp.get('others')]
        return []


class BeesuggestAgreement(models.Model):
    title = models.CharField(max_length=255, help_text="The title of the agreement.")
    content = models.TextField(help_text="The full content of the agreement.")
    is_active = models.BooleanField(default=True, help_text="Only one agreement can be active at a time. Activating this will deactivate others.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.is_active:
            # Deactivate all other agreements when this one is saved as active
            BeesuggestAgreement.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super(BeesuggestAgreement, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "Beesuggest Agreement"
        verbose_name_plural = "Beesuggest Agreements"
        ordering = ['-updated_at']


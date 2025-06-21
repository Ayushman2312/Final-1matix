from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import ProductDetails

@admin.register(ProductDetails)
class ProductDetailsAdmin(admin.ModelAdmin):
    list_display = [
        'organization', 'user', 'focus_keywords', 'is_published', 
        'submitted_at', 'published_at', 'view_images', 'view_faqs_count'
    ]
    list_filter = [
        'is_published', 'submitted_at', 'published_at', 'user'
    ]
    search_fields = [
        'organization', 'focus_keywords', 'alt_keyword_1', 'alt_keyword_2',
        'product_description', 'user__username', 'user__email'
    ]
    readonly_fields = [
        'id', 'submitted_at', 'updated_at', 'user',
        'view_images_preview', 'view_variations', 'view_faqs'
    ]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'submitted_at', 'updated_at')
        }),
        ('Keywords & SEO', {
            'fields': ('focus_keywords', 'alt_keyword_1', 'alt_keyword_2')
        }),
        ('Product Images', {
            'fields': (
                'view_images_preview',
                ('product_image_1', 'product_image_1_alt'),
                ('product_image_2', 'product_image_2_alt'),
                ('product_image_3', 'product_image_3_alt'),
                ('product_image_4', 'product_image_4_alt'),
                ('product_image_5', 'product_image_5_alt'),
            ),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('product_video', 'size_chart')
        }),
        ('Description', {
            'fields': ('product_description',)
        }),
        ('Variations', {
            'fields': ('view_variations', 'variations'),
            'classes': ('collapse',)
        }),
        ('Usage Information', {
            'fields': ('uses', 'best_suited_for')
        }),
        ('Contact Information', {
            'fields': (
                'organization', 'email', 'contact_number', 'address',
                'social_media_facebook', 'social_media_twitter', 'social_media_instagram'
            )
        }),
        ('Business Details', {
            'fields': ('gst_details', 'map_location', 'dimensions')
        }),
        ('FAQs', {
            'fields': ('view_faqs', 'faqs'),
            'classes': ('collapse',)
        }),
        ('Additional Information', {
            'fields': ('why_choose_us', 'comparison')
        }),
        ('Publishing', {
            'fields': ('is_published', 'published_at'),
            'classes': ('wide',)
        }),
    )
    
    actions = ['publish_products', 'unpublish_products']
    
    def view_images(self, obj):
        """Display number of images"""
        count = sum(1 for i in range(1, 6) if getattr(obj, f'product_image_{i}'))
        return f"{count}/5 images"
    view_images.short_description = "Images"
    
    def view_images_preview(self, obj):
        """Display image previews in admin"""
        html = []
        for i in range(1, 6):
            image = getattr(obj, f'product_image_{i}')
            if image:
                html.append(
                    f'<div style="display: inline-block; margin: 5px;">'
                    f'<img src="{image.url}" style="width: 100px; height: 100px; object-fit: cover; border: 1px solid #ddd;" />'
                    f'<br><small>Image {i}</small></div>'
                )
        return format_html(''.join(html)) if html else "No images"
    view_images_preview.short_description = "Image Preview"
    
    def view_faqs_count(self, obj):
        """Display FAQ count"""
        if obj.faqs:
            return f"{len(obj.faqs)} FAQs"
        return "0 FAQs"
    view_faqs_count.short_description = "FAQs"
    
    def view_faqs(self, obj):
        """Display formatted FAQs"""
        if not obj.faqs:
            return "No FAQs"
        
        html = []
        for i, faq in enumerate(obj.faqs, 1):
            html.append(
                f'<div style="margin-bottom: 10px; padding: 10px; border: 1px solid #eee;">'
                f'<strong>Q{i}:</strong> {faq.get("question", "No question")}<br>'
                f'<strong>A{i}:</strong> {faq.get("answer", "No answer")}'
                f'</div>'
            )
        return format_html(''.join(html))
    view_faqs.short_description = "FAQs Preview"
    
    def view_variations(self, obj):
        """Display formatted variations"""
        if not obj.variations:
            return "No variations"
        
        html = []
        for i, variation in enumerate(obj.variations, 1):
            html.append(
                f'<div style="margin-bottom: 5px;">'
                f'<strong>{variation.get("name", "Unknown")}:</strong> {variation.get("value", "No value")}'
                f'</div>'
            )
        return format_html(''.join(html))
    view_variations.short_description = "Variations Preview"
    
    def publish_products(self, request, queryset):
        """Publish selected products"""
        count = 0
        for product in queryset:
            if not product.is_published:
                product.is_published = True
                product.published_at = timezone.now()
                product.save()
                count += 1
        
        self.message_user(request, f'{count} product(s) published successfully.')
    publish_products.short_description = "Publish selected products"
    
    def unpublish_products(self, request, queryset):
        """Unpublish selected products"""
        count = queryset.filter(is_published=True).update(
            is_published=False, 
            published_at=None
        )
        self.message_user(request, f'{count} product(s) unpublished successfully.')
    unpublish_products.short_description = "Unpublish selected products"
    
    def save_model(self, request, obj, form, change):
        """Auto-set published_at when publishing"""
        if obj.is_published and not obj.published_at:
            obj.published_at = timezone.now()
        elif not obj.is_published:
            obj.published_at = None
        super().save_model(request, obj, form, change)

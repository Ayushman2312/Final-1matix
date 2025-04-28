from django.db import models
import uuid

# Create your models here.
class Listing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    platform_type = models.CharField(max_length=20)
    brand = models.CharField(max_length=255)
    urls = models.JSONField()
    keyword_screenshots = models.JSONField()
    product_images = models.JSONField(default=list, help_text="List of base64 encoded product images")
    product_specs = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.platform_type} - {self.brand}"
    
    

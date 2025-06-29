from django.db import models

# Create your models here.
class Apps(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    url_keyword = models.CharField(max_length=100, unique=True, null=True, blank=True, help_text="A unique keyword found in this app's URLs, e.g., 'invoicing'.")
    is_active = models.BooleanField(default=True)
    is_temporarily_disabled = models.BooleanField(default=False, help_text="Set to true to temporarily disable this app for all users.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


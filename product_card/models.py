import uuid
from django.db import models
from django.utils import timezone
from User.models import User

# Create your models here.

class ProductCategory(models.Model):
    category_id = models.AutoField(primary_key=True)
    category_name = models.CharField(max_length=255)
    category_created_at = models.DateTimeField(default=timezone.now)
    category_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.category_name


class Product(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, null=True, blank=True)
    product_id = models.UUIDField(default=uuid.uuid4,primary_key=True, editable=False, unique=True)
    product_title = models.CharField(max_length=255)
    product_description = models.TextField()
    product_price = models.DecimalField(max_digits=10, decimal_places=2)
    product_image1 = models.ImageField(upload_to='product_images/')
    product_image2 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    product_image3 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    product_image4 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    product_hsc_code = models.CharField(max_length=255, blank=True, null=True)
    product_gst_percentage = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    product_variant = models.JSONField(null=True, blank=True)
    product_video_link = models.URLField(blank=True, null=True)
    product_available = models.BooleanField(default=False)
    product_created_at = models.DateTimeField(default=timezone.now)
    product_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.product_title

class ProductCard(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    card_id = models.AutoField(primary_key=True)
    card_image = models.ImageField(upload_to='card_images/')
    card_created_at = models.DateTimeField(default=timezone.now)
    card_updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.product.product_title
from django.db import models

# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Categories"

class SubCategory(models.Model):
    name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='subcategories')
    is_exception = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    class Meta:
        verbose_name_plural = "Sub Categories"

class AmazonProgram(models.Model):
    PROGRAM_CHOICES = [
        ('EASY_SHIP', 'Easy Ship Prime'),
        ('FBA', 'FBA'),
        ('SELLER_FLEX', 'Seller Flex'),
    ]
    
    name = models.CharField(max_length=20, choices=PROGRAM_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.get_name_display()

CONDITION_CHOICES = [
    ('gte', 'Greater than or equal to'),
    ('lte', 'Less than or equal to'),
    ('eq', 'Equal to'),
    ('gt', 'Greater than'),
    ('lt', 'Less than'),
]


class FeeStructure(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE)
    referral_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    condition = models.CharField(max_length=255, choices=CONDITION_CHOICES,null=True,blank=True)
    value = models.DecimalField(max_digits=10, decimal_places=2,null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category.name} - {self.subcategory.name} (condition: {self.condition}, value: {self.value})"

    class Meta:
        constraints = []  # Ensure there's no UniqueConstraint
    
class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE)
    program = models.ForeignKey(AmazonProgram, on_delete=models.CASCADE)
    product_cost = models.FloatField()
    selling_price = models.FloatField()
    weight = models.FloatField()
    dimensions = models.JSONField()  # Stores {"length": xx, "width": xx, "height": xx}
    gst = models.FloatField()
    referral_fee = models.FloatField()
    closing_fee = models.FloatField()
    total_fee = models.FloatField()
    gross_profit = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category.name} - {self.subcategory.name}"

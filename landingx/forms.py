from django import forms
from .models import ProductDetails

class ProductDetailsForm(forms.ModelForm):
    class Meta:
        model = ProductDetails
        fields = '__all__'
        exclude = ('is_published', 'published_at') 
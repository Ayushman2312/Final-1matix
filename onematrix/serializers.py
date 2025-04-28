from rest_framework import serializers
from .models import FAQCategory, FAQItem

class FAQItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = FAQItem
        fields = ['id', 'question', 'answer', 'order', 'is_active', 'created_at', 'updated_at']

class FAQCategorySerializer(serializers.ModelSerializer):
    faq_items = FAQItemSerializer(many=True, read_only=True)
    
    class Meta:
        model = FAQCategory
        fields = ['id', 'name', 'description', 'order', 'is_active', 'created_at', 'updated_at', 'faq_items'] 
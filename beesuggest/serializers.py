from rest_framework import serializers
from .models import ProductDetails
from django.contrib.auth.models import User

class UserBasicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class ProductDetailsSerializer(serializers.ModelSerializer):
    user = UserBasicSerializer(read_only=True)
    images = serializers.SerializerMethodField()
    variations_formatted = serializers.SerializerMethodField()
    faqs_formatted = serializers.SerializerMethodField()
    comparisons_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = ProductDetails
        fields = [
            'id', 'user', 'focus_keywords', 'alt_keyword_1', 'alt_keyword_2',
            'product_title', 'short_description',
            'product_image_1', 'product_image_1_alt', 'product_image_2', 'product_image_2_alt',
            'product_image_3', 'product_image_3_alt', 'product_image_4', 'product_image_4_alt',
            'product_image_5', 'product_image_5_alt', 'video_url_1', 'video_url_2', 'video_url_3', 'product_description',
            'variations', 'variations_formatted', 'uses', 'best_suited_for',
            'social_media_facebook', 'social_media_twitter', 'social_media_instagram',
            'website_url', 'contact_number', 'email', 'address', 'organization',
            'gst_details', 'map_location', 'faqs', 'faqs_formatted', 'size_chart',
            'why_choose_us', 'comparison', 'comparisons', 'comparisons_formatted', 'is_published', 'submitted_at',
            'published_at', 'updated_at', 'images'
        ]
    
    def get_images(self, obj):
        return obj.get_images
    
    def get_variations_formatted(self, obj):
        return obj.get_variations_list
    
    def get_faqs_formatted(self, obj):
        return obj.get_faqs_list
    
    def get_comparisons_formatted(self, obj):
        return obj.get_comparisons_list

class ProductSearchSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source='focus_keywords')
    uuid = serializers.UUIDField(source='id')

    class Meta:
        model = ProductDetails
        fields = ['name', 'uuid']

class ProductCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductDetails
        exclude = ['user', 'is_published', 'published_at']
        
    def create(self, validated_data):
        # The user will be set in the view
        return ProductDetails.objects.create(**validated_data) 
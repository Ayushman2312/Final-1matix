from django.db import models
from django.contrib.auth.models import User
import uuid
import json
import logging

# Get logger
logger = logging.getLogger(__name__)

def ensure_json_serializable(data):
    """Ensure data is JSON serializable by converting problematic types"""
    if isinstance(data, dict):
        return {k: ensure_json_serializable(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [ensure_json_serializable(item) for item in data]
    elif isinstance(data, bool):
        return str(data).lower()  # Convert to "true"/"false" strings
    elif isinstance(data, (int, float, str, type(None))):
        return data
    else:
        # Convert any other types to string
        return str(data)

class SalesDataFile(models.Model):
    """Model for storing uploaded sales data files"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sales_data_files')
    file = models.FileField(upload_to='sales_data/')
    file_name = models.CharField(max_length=255)
    file_type = models.CharField(max_length=50)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.file_name} ({self.id})"

class SalesAnalysisResult(models.Model):
    """Model for storing analysis results for sales data files"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sales_data_file = models.ForeignKey(SalesDataFile, on_delete=models.CASCADE, related_name='analysis_results')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=50, default='pending')  # pending, processing, completed, failed
    error_message = models.TextField(blank=True, null=True)
    column_mappings = models.JSONField(blank=True, null=True)  # Store the detected column mappings
    analysis_data = models.JSONField(blank=True, null=True)  # Store the analysis results
    platform_type = models.CharField(max_length=50, blank=True, null=True)  # Store the marketplace platform type (Amazon, Flipkart, Meesho)
    
    def __str__(self):
        return f"Analysis for {self.sales_data_file.file_name} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Override save to ensure data is JSON serializable"""
        # Ensure column_mappings is JSON serializable
        if self.column_mappings:
            try:
                self.column_mappings = ensure_json_serializable(self.column_mappings)
            except Exception as e:
                logger.error(f"Error serializing column_mappings: {e}")
                
        # Ensure analysis_data is JSON serializable
        if self.analysis_data:
            try:
                self.analysis_data = ensure_json_serializable(self.analysis_data)
            except Exception as e:
                logger.error(f"Error serializing analysis_data: {e}")
                
        # Call the original save method
        super().save(*args, **kwargs)
    
    def get_analysis_json(self):
        """Returns the analysis data as a properly formatted JSON string"""
        if self.analysis_data:
            try:
                return json.dumps(self.analysis_data)
            except Exception as e:
                logger.error(f"Error converting analysis_data to JSON: {e}")
                return "{}"
        return "{}"

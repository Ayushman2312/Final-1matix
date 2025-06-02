from rest_framework import serializers
from .models import SalesDataFile, SalesAnalysisResult

class SalesDataFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesDataFile
        fields = ['id', 'file', 'file_name', 'file_type', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at']

class SalesAnalysisResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = SalesAnalysisResult
        fields = ['id', 'sales_data_file', 'analysis_data', 'column_mappings', 
                 'created_at', 'updated_at', 'status', 'error_message']
        read_only_fields = ['id', 'created_at', 'updated_at'] 
import os
import logging
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import datetime, date

logger = logging.getLogger(__name__)

class EnhancedJSONEncoder(DjangoJSONEncoder):
    """
    Enhanced JSON encoder that better handles special data types and potential issues
    """
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        # Handle other potential special types that might cause issues
        return super().default(obj)
    
    def encode(self, obj):
        # Special handling for dictionary keys and string values 
        if isinstance(obj, dict):
            # Create a new dict with fixed values
            fixed_dict = {}
            for key, value in obj.items():
                # Ensure option values are always properly quoted strings
                if key == 'option' and not isinstance(value, str):
                    fixed_dict[key] = str(value)
                # Handle the analysis_option key specifically
                elif key == 'analysis_option' and not isinstance(value, str):
                    fixed_dict[key] = str(value)
                # Handle numeric keys in general - convert to strings to avoid issues
                elif isinstance(key, (int, float)):
                    fixed_dict[str(key)] = value
                else:
                    fixed_dict[key] = self._fix_nested_values(value)
            return super().encode(fixed_dict)
        elif isinstance(obj, list):
            # Process lists to handle nested dicts/values
            return super().encode([self._fix_nested_values(item) for item in obj])
        return super().encode(obj)
    
    def _fix_nested_values(self, value):
        """Helper method to recursively fix nested dictionaries and lists"""
        if isinstance(value, dict):
            fixed_dict = {}
            for k, v in value.items():
                # Ensure option values are always properly quoted strings
                if k == 'option' and not isinstance(v, str):
                    fixed_dict[k] = str(v)
                else:
                    fixed_dict[k] = self._fix_nested_values(v)
            return fixed_dict
        elif isinstance(value, list):
            return [self._fix_nested_values(item) for item in value]
        return value


def get_google_api_key():
    """
    Retrieve the Google API key from environment variables.
    This allows for more secure handling of API keys.
    """
    api_key = os.getenv('GOOGLE_API_KEY', '')
    if not api_key:
        # Try loading from .env file
        try:
            with open('.env') as f:
                for line in f:
                    if line.startswith('GOOGLE_API_KEY'):
                        api_key = line.split('=')[1].strip().strip("'").strip('"')
                        break
        except Exception as e:
            logger.error(f"Error reading .env file: {str(e)}")
    
    if not api_key:
        logger.warning("Google API key not found in environment variables. Generative AI features will be disabled.")
        return None
    
    return api_key

def check_api_configuration():
    """
    Check if required API keys are configured
    """
    google_api_key = get_google_api_key()
    
    return {
        'google_api_configured': bool(google_api_key)
    }

def safe_json_dumps(data):
    """
    Safely serialize data to JSON string, handling potential serialization issues
    """
    try:
        return json.dumps(data, cls=EnhancedJSONEncoder)
    except (TypeError, ValueError, json.JSONDecodeError) as e:
        logger.error(f"JSON serialization error: {str(e)}")
        # Return a minimal valid JSON if serialization fails
        return json.dumps({
            'status': 'error',
            'error': 'JSON serialization error',
            'message': str(e)
        }) 
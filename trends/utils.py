import os
import logging
import json
import numpy as np
import pandas as pd
from django.core.serializers.json import DjangoJSONEncoder
from datetime import datetime, date
import re

logger = logging.getLogger(__name__)

class EnhancedJSONEncoder(DjangoJSONEncoder):
    """
    Enhanced JSON encoder that better handles special data types and potential issues
    """
    def default(self, obj):
        # Handle pandas and numpy types
        if isinstance(obj, pd.DataFrame):
            return obj.to_dict(orient='records')
        if isinstance(obj, pd.Series):
            return obj.to_dict()
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if pd.isna(obj) or obj is pd.NaT:
            return None
        # Handle numpy bool
        if isinstance(obj, np.bool_):
            return bool(obj)
        
        # Handle other potential special types that might cause issues
        try:
            # Try converting to a native Python type
            if hasattr(obj, 'item'):
                return obj.item()
            # For objects with a __dict__, convert to dict
            if hasattr(obj, '__dict__'):
                return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
            # If the object has a specific serialization method
            if hasattr(obj, 'to_json'):
                return obj.to_json()
        except:
            # Last resort - convert to string
            try:
                return str(obj)
            except:
                return "UNSERIALIZABLE_OBJECT"
        
        return super().default(obj)
    
    def encode(self, obj):
        # Special handling for dictionary keys and string values 
        if isinstance(obj, dict):
            # Create a new dict with fixed values
            fixed_dict = {}
            for key, value in obj.items():
                # Convert key to string if it's not already
                str_key = str(key) if not isinstance(key, str) else key
                # Handle the value with special cases
                fixed_dict[str_key] = self._fix_nested_values(value)
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
                str_k = str(k) if not isinstance(k, str) else k
                fixed_dict[str_k] = self._fix_nested_values(v)
            return fixed_dict
        elif isinstance(value, list):
            return [self._fix_nested_values(item) for item in value]
        elif isinstance(value, str):
            # Clean strings by removing control characters
            return re.sub(r'[\x00-\x1F\x7F-\x9F]', '', value)
        elif pd.isna(value) or value is pd.NaT:
            return None
        elif isinstance(value, (np.integer, np.floating, np.bool_)):
            # Convert numpy types to native Python types
            return value.item()
        elif isinstance(value, np.ndarray):
            return value.tolist()
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
        # Try serializing using enhanced encoder
        return json.dumps(data, cls=EnhancedJSONEncoder)
    except (TypeError, ValueError, json.JSONDecodeError) as e:
        logger.error(f"JSON serialization error: {str(e)}")
        
        # Try to sanitize the data with a recursive approach
        try:
            sanitized_data = sanitize_for_json(data)
            return json.dumps(sanitized_data)
        except Exception as e2:
            logger.error(f"Secondary JSON serialization error after sanitization: {str(e2)}")
            
            # Return a minimal valid JSON if all serialization attempts fail
            return json.dumps({
                'status': 'error',
                'errors': ['JSON serialization error'],
                'message': str(e)
            })

def sanitize_for_json(data):
    """Recursively sanitize data to ensure it's JSON serializable"""
    if isinstance(data, dict):
        return {str(k): sanitize_for_json(v) for k, v in data.items()}
    elif isinstance(data, list) or isinstance(data, tuple):
        return [sanitize_for_json(item) for item in data]
    elif isinstance(data, (int, float, bool, type(None), str)):
        return data
    elif isinstance(data, (datetime, date)):
        return data.isoformat()
    elif hasattr(data, 'to_dict'):
        try:
            return sanitize_for_json(data.to_dict())
        except:
            pass
    elif pd.isna(data) or data is pd.NaT:
        return None
    elif isinstance(data, (np.integer, np.floating, np.bool_)):
        return data.item()
    elif isinstance(data, np.ndarray):
        return data.tolist()
    
    # Last resort - convert to string
    try:
        return str(data)
    except:
        return "UNSERIALIZABLE_OBJECT" 
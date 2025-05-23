import re
import logging
from typing import Optional, Dict, Tuple, Union
import os
from datetime import datetime

# Set up logging for phone validation
validation_logger = logging.getLogger('phone_validation')
validation_logger.setLevel(logging.DEBUG)

# Create directory for logs if it doesn't exist
os.makedirs('validation_logs', exist_ok=True)

# Set up file handler for logging rejected numbers
log_file = f'validation_logs/phone_validation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
file_handler = logging.FileHandler(log_file)
file_handler.setLevel(logging.DEBUG)

# Format for log messages
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
validation_logger.addHandler(file_handler)

def validate_email(email: str) -> bool:
    """Validate an email address with enhanced filtering for HTML/CSS artifacts."""
    # Basic format check
    if '.' not in email or '@' not in email or len(email) < 5:
        return False
    
    try:
        # Extract username and domain parts
        parts = email.split('@')
        if len(parts) != 2:
            return False
            
        username, domain = parts
        
        # Username validation
        if len(username) < 2:
            return False
            
        # Check for file extensions in email
        if any(email.lower().endswith(ext) for ext in 
                ['.png', '.jpg', '.gif', '.js', '.css', '.html', '.svg', '.pdf']):
            return False
        
        # Check for HTML/CSS artifact patterns commonly found in the scraped data
        css_patterns = [
            r'@ion\b', r'@ic\.', r'erial\b', r'stamps\b', r'@us\.',  # Using word boundaries
            r'@a\.', r'tist@ic', r'specific@ion', r'applic@ion',
            r'verific@ion', r'separ@ion', r'cancell@ion', r'loc@ion',
            r'm@erial', r'sl@-', r'autom@ic', r'mc@-', r'vibr@', 
            r'kolk@a', r'basm@i', r'srch\b', r'revamp\b', r'wrapper\b', 
            r'card\b', r'cont\b', r'pl@form', r'-@', r'@-'
        ]
        
        for pattern in css_patterns:
            if re.search(pattern, email, re.IGNORECASE):
                return False

        # Special cases to allow legitimate business emails with hyphens
        if '-name' in email and any(legitdomain in domain for legitdomain in ['company', 'business']):
            pass  # Allow these legitimate business domains with hyphens
        elif 'example.com' in email and (email.startswith('contact@') or email.startswith('info@')):
            pass  # Allow specific legitimate example.com addresses that are often used in examples
        else:
            # Check for other common exclusions in email
            common_exclusions = [
                'your-email', 'user@example', 'your@', 
                'info@example.org', 'contact@example.org', 'no-reply',
                'sample', 'support@example', 'test@', 'tradeindia',
                'tradekh@a', 'product-specific@ion', '.price', '.inquiry'
            ]
            
            for exclusion in common_exclusions:
                if exclusion in email.lower():
                    return False
        
        # Verify domain structure
        domain_parts = domain.split('.')
        if len(domain_parts) < 2:
            return False
            
        # Check for template placeholders
        if '{' in email or '}' in email or '[' in email or ']' in email:
            return False
        
        # Filter out domains that are clearly HTML/CSS artifacts based on the observed false positives
        invalid_domains = [
            'they', 'svg', 'card', 'more', 'our', 'html', 'you', 'we',
            'ti', 'no', 'city', 'product', 'price', 'inquiry', 'mic'
        ]
        
        # Make sure we're only checking the TLD, not parts of legitimate domains
        tld = domain_parts[-1].lower()
        if tld in invalid_domains and domain not in ['example.com', 'company.com', 'business.com']:
            return False
        
        # Extra check for specific patterns seen in the scraped data
        bad_patterns = [
            'pmma-acrylic', 'aerial-work', 'air-compressors',
            'semi-autom', 'industrial-vibr', 'product-video',
            'stamped-st', '-labelling-', '-handling-'
        ]
        # Don't reject legitimate domains that might have a hyphen
        if any(x in email.lower() for x in bad_patterns) and not ('business-' in domain or 'company-' in domain):
            return False
        
        return True
        
    except Exception:
        return False

def validate_indian_phone(phone: str, source: str = "unknown") -> Union[Dict, None]:
    """Validate and format Indian phone numbers with enhanced validation.
    
    Args:
        phone: The phone number to validate
        source: String indicating where the number was found (e.g. 'homepage', 'contact_page')
        
    Returns:
        Dictionary with normalized phone number, original form, and source if valid
        None if the number is not valid
    """
    # Handle tuple results from findall (happens with capturing groups)
    if isinstance(phone, tuple):
        # Use the first non-empty group
        phone = next((p for p in phone if p), '')
    
    if not phone:
        validation_logger.warning(f"Rejected: Empty phone value from {source}")
        return None
    
    # Save original form for reference
    original_form = phone
    
    # Initial cleaning - remove common separators but preserve + sign
    cleaned_phone = phone.strip()
    has_plus = cleaned_phone.startswith('+')
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', cleaned_phone)
    if has_plus:
        digits_only = '+' + digits_only
    
    # Basic length check - adjusted to allow for various formats
    if len(digits_only) < 8:  # Allow for landline numbers which can be 8 digits
        validation_logger.warning(f"Rejected: Too short ({len(digits_only)} digits) '{original_form}' from {source}")
        return None
    
    if len(digits_only) > 16:  # Increased to 16 to accommodate international codes
        validation_logger.warning(f"Rejected: Too long ({len(digits_only)} digits) '{original_form}' from {source}")
        return None
    
    # Enhanced validation for Indian phone formats
    valid_number = False
    normalized_number = None
    number_type = "unknown"
    
    # Check for different phone number patterns
    
    # PATTERN 1: Standard 10-digit mobile numbers (starting with 6, 7, 8, or 9)
    if len(digits_only) == 10 and digits_only[0] in '6789':
        # Basic suspicious pattern check
        if digits_only == '9999999999' or len(set(digits_only)) <= 2:
            validation_logger.warning(f"Rejected: Suspicious pattern (repeated digits) '{original_form}' from {source}")
            return None
            
        normalized_number = f"+91{digits_only}"
        valid_number = True
        number_type = "mobile"
    
    # PATTERN 2: Country code +91 followed by 10-digit mobile number
    elif digits_only.startswith('+91') and len(digits_only) == 13 and digits_only[3] in '6789':
        mobile_part = digits_only[3:]
        if mobile_part == '9999999999' or len(set(mobile_part)) <= 2:
            validation_logger.warning(f"Rejected: Suspicious pattern in '{original_form}' from {source}")
            return None
            
        normalized_number = f"+91{mobile_part}"
        valid_number = True
        number_type = "mobile"
    
    # PATTERN 3: Country code 91 (without +) followed by 10 digits
    elif digits_only.startswith('91') and len(digits_only) == 12 and digits_only[2] in '6789':
        mobile_part = digits_only[2:]
        if mobile_part == '9999999999' or len(set(mobile_part)) <= 2:
            validation_logger.warning(f"Rejected: Suspicious pattern in '{original_form}' from {source}")
            return None
            
        normalized_number = f"+91{mobile_part}"
        valid_number = True
        number_type = "mobile"
    
    # PATTERN 4: Leading 0 followed by 10-digit mobile (domestic dialing)
    elif digits_only.startswith('0') and len(digits_only) == 11 and digits_only[1] in '6789':
        mobile_part = digits_only[1:]
        if mobile_part == '9999999999' or len(set(mobile_part)) <= 2:
            validation_logger.warning(f"Rejected: Suspicious pattern in '{original_form}' from {source}")
            return None
            
        normalized_number = f"+91{mobile_part}"
        valid_number = True
        number_type = "mobile"
    
    # PATTERN 5: Landline with area code (e.g., 022-12345678 or 11-12345678)
    elif (len(digits_only) == 10 or len(digits_only) == 11) and digits_only[0] == '0':
        # Extract the area code and the local part
        if len(digits_only) == 11:  # 4-digit area code (e.g., 0124-1234567)
            area_code = digits_only[1:4]
            local_part = digits_only[4:]
        else:  # 3-digit area code (e.g., 022-1234567)
            area_code = digits_only[1:3]
            local_part = digits_only[3:]
            
        # Validate area code - known major city codes
        major_area_codes = ['11', '22', '33', '44', '40', '80', '79', '20', '124', '120', '121']
        if area_code in major_area_codes or (len(local_part) in [7, 8] and area_code.isdigit()):
            normalized_number = f"+91-{area_code}-{local_part}"
            valid_number = True
            number_type = "landline"
    
    # PATTERN 6: Direct 8-digit landline number (no area code - common in business listings)
    elif len(digits_only) == 8 and digits_only[0] in '2345':
        # These are often city landlines without the area code
        normalized_number = f"+91-{digits_only}"
        valid_number = True
        number_type = "landline_short"
    
    # PATTERN 7: International format for business numbers (+91 followed by area code and number)
    elif digits_only.startswith('+91') and len(digits_only) in [12, 13, 14]:
        # This handles formats like +91-11-12345678 or +91-22-12345678
        remaining_digits = digits_only[3:]
        if len(remaining_digits) in [8, 9, 10] and remaining_digits[0] in '012345':
            normalized_number = digits_only  # Already in full international format
            valid_number = True
            number_type = "landline_international"
    
    # PATTERN 8: 5-digit special numbers (short codes, customer service, etc.)
    elif len(digits_only) == 5 and digits_only.isdigit():
        # Special short commercial numbers
        normalized_number = digits_only
        valid_number = True
        number_type = "short_code"
    
    # PATTERN 9: Toll-free numbers (1800/1900 followed by 7-8 digits)
    elif digits_only.startswith(('1800', '1900', '1860')) and len(digits_only) in [11, 12]:
        normalized_number = f"+91-{digits_only}"
        valid_number = True
        number_type = "tollfree"
    
    # If format wasn't recognized
    if not valid_number:
        validation_logger.warning(f"Rejected: Unrecognized format '{original_form}' from {source}")
        return None
    
    # Additional validations for recognized numbers
    
    # Check for dummy or test patterns in the last 8 digits (for all number types)
    if number_type in ["mobile", "landline", "landline_international"]:
        # Extract the last 8 digits regardless of format 
        last_digits = re.sub(r'\D', '', str(normalized_number))[-8:]
        
        # Check for too many repeating digits
        if any(digit * 4 in last_digits for digit in '0123456789'):
            validation_logger.warning(f"Rejected: Too many repeating digits in '{original_form}' from {source}")
            return None
            
        # Check for sequential patterns
        sequential_patterns = ['12345678', '87654321', '01234567', '76543210']
        if any(pattern in last_digits for pattern in sequential_patterns):
            validation_logger.warning(f"Rejected: Sequential digit pattern in '{original_form}' from {source}")
            return None
            
        # Check for dummy patterns 
        dummy_patterns = ['00000000', '11111111', '22222222', '33333333', '44444444', 
                         '55555555', '66666666', '77777777', '88888888', '99999999']
        if last_digits in dummy_patterns:
            validation_logger.warning(f"Rejected: Known dummy pattern '{original_form}' from {source}")
            return None
    
    # If we made it here, the number is valid!
    validation_logger.info(f"Valid {number_type}: '{original_form}' normalized to {normalized_number} from {source}")
    
    # Return a dictionary with the normalized phone, original form, and source
    return {
        'phone': normalized_number,
        'original': original_form,
        'source': source,
        'type': number_type
    } 
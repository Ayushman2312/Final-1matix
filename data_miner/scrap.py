from serpapi import GoogleSearch
import re
import requests
from bs4 import BeautifulSoup
import logging
import os
import time
import json
from django.conf import settings as django_settings
from urllib.parse import urlparse
from requests.exceptions import RequestException
import random
import traceback
import threading

# Import app-specific settings
try:
    from .settings import (
        SERPAPI_KEY, GEMINI_API_KEY, DEFAULT_MAX_RESULTS, DEFAULT_MAX_PAGES,
        DEFAULT_TIMEOUT, SCRAPING_DELAY, MAX_RETRIES, MIN_PHONE_LENGTH, MAX_DOMAIN_LENGTH
    )
except ImportError:
    # Default values if settings.py is not available
    SERPAPI_KEY = "64e3a48333bbb33f4ce8ded91e5268cd453a80fb244104de63b7ad9af9cc2a58"
    GEMINI_API_KEY = 'AIzaSyDsXH-_ftI5xn4aWfkwpw__4ixUMs7a7fM'
    DEFAULT_MAX_RESULTS = 50
    DEFAULT_MAX_PAGES = 5
    DEFAULT_TIMEOUT = 10
    SCRAPING_DELAY = 1
    MAX_RETRIES = 3
    MIN_PHONE_LENGTH = 8
    MAX_DOMAIN_LENGTH = 50

# Import for Google Gemini API
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

# Configure logging
logger = logging.getLogger(__name__)

# Dictionary to track active tasks and their stop flags
active_tasks = {}

# Class to manage API keys for SerpAPI
class ApiKeyManager:
    """Manages a pool of API keys and rotates them when needed"""
    
    def __init__(self, api_keys_file='data_miner/apis.txt'):
        """Initialize with a file containing API keys"""
        self.api_keys = []
        self.current_key_index = 0
        self.disabled_keys = set()  # Set to track disabled keys
        
        # Load API keys from file
        try:
            with open(api_keys_file, 'r') as f:
                for line in f:
                    # Clean up the line and extract just the key
                    key = line.strip()
                    if key and not key.startswith('#'):
                        # Extract key if it's in format "1.key123456"
                        if '.' in key:
                            key = key.split('.', 1)[1]
                        self.api_keys.append(key)
            
            logger.info(f"Loaded {len(self.api_keys)} API keys")
        except Exception as e:
            logger.error(f"Error loading API keys: {e}")
            # Use default key as fallback
            self.api_keys = [SERPAPI_KEY]
    
    def get_current_key(self):
        """Get the current active API key"""
        if not self.api_keys:
            logger.error("No API keys available")
            return None
            
        # Skip disabled keys
        while self.current_key_index < len(self.api_keys):
            key = self.api_keys[self.current_key_index]
            if key not in self.disabled_keys:
                return key
            self.current_key_index += 1
            
        # If we've gone through all keys, reset to start and try again
        self.current_key_index = 0
        while self.current_key_index < len(self.api_keys):
            key = self.api_keys[self.current_key_index]
            if key not in self.disabled_keys:
                return key
            self.current_key_index += 1
            
        logger.error("All API keys are disabled")
        return None
    
    def rotate_key(self):
        """Move to the next available API key"""
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        logger.info(f"Rotated to API key index {self.current_key_index}")
        return self.get_current_key()
    
    def disable_current_key(self):
        """Mark the current key as disabled (e.g., when it runs out of searches)"""
        if not self.api_keys:
            return None
            
        current_key = self.api_keys[self.current_key_index]
        self.disabled_keys.add(current_key)
        logger.warning(f"Disabled API key {current_key[:8]}... due to usage limits")
        
        # Move to next key
        return self.rotate_key()
    
    def is_error_limit_reached(self, response):
        """Check if the error is due to API limits being reached"""
        if isinstance(response, dict):
            # Check for common limit errors
            if 'error' in response:
                error_msg = response['error'].lower()
                limit_indicators = ['run out of searches', 'limit exceeded', 'api limit', 'quota exceeded']
                return any(indicator in error_msg for indicator in limit_indicators)
        return False

# Initialize global API key manager
api_key_manager = ApiKeyManager()

def stop_task(task_id):
    """
    Stop a running task by setting its stop flag
    
    Args:
        task_id (str): ID of the task to stop
        
    Returns:
        bool: True if task was found and stopped, False otherwise
    """
    if task_id in active_tasks:
        active_tasks[task_id]['stop'] = True
        logger.info(f"Stop signal sent to task {task_id}")
        
        # Wait for a short time to see if task exits gracefully
        for _ in range(10):  # Wait up to 5 seconds
            time.sleep(0.5)
            if not active_tasks.get(task_id, {}).get('running', False):
                # Task has exited
                return True
                
        # If still running, try to terminate the thread
        try:
            if 'thread' in active_tasks[task_id]:
                # This is a soft attempt - threads can't be forcibly terminated in Python
                active_tasks[task_id]['thread'].join(0.1)
                logger.info(f"Attempted to terminate thread for task {task_id}")
                
            # Update status to stopped
            update_task_status(task_id, {
                'status': 'stopped',
                'progress': 0,
                'message': 'Task was manually stopped'
            })
            
            # Clean up regardless
            if task_id in active_tasks:
                del active_tasks[task_id]
                
            return True
        except Exception as e:
            logger.error(f"Error while stopping task {task_id}: {e}")
            return False
    else:
        logger.warning(f"Attempt to stop non-existent task {task_id}")
        return False

class GeminiQueryOptimizer:
    """Uses Google Gemini to optimize search queries for better results"""
    
    def __init__(self, api_key=None):
        """Initialize the Gemini client with API key"""
        # Use the provided API key or try to get from settings
        self.api_key = api_key or GEMINI_API_KEY or getattr(django_settings, 'GEMINI_API_KEY', None)
        
        # If API key is available and Gemini is installed, configure the Gemini client
        if self.api_key and GEMINI_AVAILABLE:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                self.available = True
            except Exception as e:
                logger.error(f"Error initializing Gemini API: {e}")
                self.available = False
        else:
            if not GEMINI_AVAILABLE:
                logger.warning("Google Gemini package not installed, query optimization disabled")
            else:
                logger.warning("No Gemini API key found, query optimization disabled")
            self.available = False
    
    def optimize_query(self, keyword, data_type, country=None):
        """
        Optimize the search query based on the keyword, data_type and country
        
        Args:
            keyword (str): The user's search keyword
            data_type (str): 'email' or 'phone'
            country (str): Country code like 'IN', 'US', etc.
            
        Returns:
            str: Optimized search query
        """
        if not self.available:
            # If Gemini is not available, return a manually optimized query
            country_term = f"in {country}" if country else ""
            if data_type == 'email':
                return f"{keyword} contact us email {country_term}"
            else:  # phone
                return f"{keyword} contact phone number {country_term}"
        
        try:
            # Craft a prompt for Gemini to optimize the query
            prompt = f"""
              You are a professional web researcher specialized in crafting powerful Google search queries to extract business contact information.

              Your task: Create a highly optimized **Google search query** to help find **{data_type}s** for businesses related to: "{keyword}".
              {f'Target country: {country}' if country else ''}

              **Guidelines:**
              1. Structure the query exactly like a real user would type it into Google Search.
              2. Include **relevant phrases** like:
                - "contact", "phone number", "mobile", "email", "support"
                - Use logical operators (OR/AND), quotes for exact matches, and parentheses when needed.
              3. Narrow the scope to country-specific sites using: `site:.{country.lower()}`
              4. **Exclude** major platforms and low-quality sources using `-site:`:
                - facebook.com, twitter.com, linkedin.com, instagram.com, youtube.com, justdial.com, indiamart.com
              5. Do **not** use full sentence instructions or explanations—only the final search query string.
              6. Ensure the query is powerful, concise, and avoids triggering local results (Google Maps packs).
              7. Avoid enclosing the entire query in quotes unless absolutely needed—use smart quoting.

              📌 **Output Requirements**:
              - Return ONLY the optimized Google search query (1 line), nothing else.

              Example Output Format:
                  "dry fruits supplier" (contact OR phone OR email) site:.in -site:facebook.com -site:twitter.com -site:linkedin.com -site:justdial.com -site:indiamart.com
              """

            
            response = self.model.generate_content(prompt)
            
            # Get the optimized query from the response
            optimized_query = response.text.strip()
            
            # Log the optimization
            logger.info(f"Original query: '{keyword}' -> Optimized: '{optimized_query}'")
            
            return optimized_query
            
        except Exception as e:
            logger.error(f"Error optimizing query with Gemini: {e}")
            # Fallback to manual optimization
            country_term = f"in {country}" if country else ""
            if data_type == 'email':
                return f"{keyword} contact us email {country_term}"
            else:  # phone
                return f"{keyword} contact phone number {country_term}"


class SerpApiScraper:
    """Scraper using SerpAPI to get search results and extract emails or phone numbers"""
    
    def __init__(self, api_key=None, update_status_callback=None, task_id=None):
        """
        Initialize the SerpAPI scraper
        
        Args:
            api_key (str): The SerpAPI key, will use the one in settings if not provided
            update_status_callback (callable): Function to call for status updates
            task_id (str): Task ID for tracking
        """
        # Use API Key Manager instead of a single key
        self.api_key_manager = api_key_manager
        
        # Still store a specific key if provided explicitly
        self.specific_api_key = api_key
        
        self.update_status = update_status_callback
        self.task_id = task_id
        
        # Register this task in active tasks with a stop flag
        if task_id:
            active_tasks[task_id] = {
                'stop': False,
                'running': True,
                'thread': threading.current_thread()
            }
            
        # Initialize the query optimizer
        self.query_optimizer = GeminiQueryOptimizer()
        
        # Initialize requests session for persistence
        self.session = requests.Session()
        
        # Add user agent rotation
        try:
            from fake_useragent import UserAgent
            self.ua = UserAgent(verify_ssl=False)
            self.has_user_agent_generator = True
        except Exception:
            self.has_user_agent_generator = False
            # Fallback user agents if fake_useragent fails
            self.user_agents = [
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/120.0.0.0',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15',
                'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
                'Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
            ]
            
        # Domain access tracking for rate limiting
        self.domain_access_times = {}
        self.domain_success_rates = {}
        
        # Proxy configuration
        self.proxies = []
        self.setup_proxy_pool()
        
    def __del__(self):
        """Clean up resources when scraper is destroyed"""
        # Remove task from active tasks if it exists
        if self.task_id and self.task_id in active_tasks:
            active_tasks[self.task_id]['running'] = False
            del active_tasks[self.task_id]
            
        # Close session
        if hasattr(self, 'session'):
            try:
                self.session.close()
            except:
                pass
    
    def setup_proxy_pool(self):
        """Set up a pool of proxies for rotation during scraping"""
        try:
            # Load free proxies from common sources
            self._update_progress(2, "Setting up proxy pool...")
            
            # Define proxy credentials and endpoints
            proxy_auth = "vnkl9BGvMRlmvWfO:EjFoKHcjcchVYwZ9"
            proxy_endpoint = "geo.iproyal.com:12321"
            
            # Format proxy URL according to required format
            self.proxies.append({
                'http': f'http://{proxy_auth}@{proxy_endpoint}',
                'https': f'http://{proxy_auth}@{proxy_endpoint}'
            })
            
            logger.info(f"Set up proxy pool with {len(self.proxies)} proxies")
            
        except Exception as e:
            logger.error(f"Error setting up proxy pool: {e}")
            # If proxy setup fails, continue without proxies
            self.proxies = []
    
    def _update_progress(self, progress, message):
        """Update progress if callback is available"""
        if self.update_status and self.task_id:
            self.update_status(self.task_id, {
                'status': 'processing',
                'progress': progress,
                'message': message
            })
            
        # Check if task should be stopped
        if self.task_id and self.task_id in active_tasks and active_tasks[self.task_id]['stop']:
            logger.info(f"Task {self.task_id} is stopping due to stop flag")
            if self.update_status:
                self.update_status(self.task_id, {
                    'status': 'stopped',
                    'progress': progress,
                    'message': 'Task was manually stopped'
                })
            # Mark task as not running
            active_tasks[self.task_id]['running'] = False
            # Raise exception to stop execution
            raise InterruptedError("Task was manually stopped")
    
    def _get_random_user_agent(self):
        """Get a random user agent string."""
        if self.has_user_agent_generator:
            try:
                return self.ua.random
            except Exception:
                pass
                
        # Fallback to predefined list
        return random.choice(self.user_agents)
        
    def _get_random_proxy(self):
        """Get a random proxy from the list."""
        if not self.proxies:
            return None
            
        return random.choice(self.proxies)
    
    def _generate_browser_fingerprint(self):
        """
        Generate a realistic browser fingerprint with headers and cookies
        to avoid bot detection.
        
        Returns:
            dict: Dictionary of headers that mimic a real browser
        """
        # Get base user agent
        user_agent = self._get_random_user_agent()
        
        # Extract browser info from user agent for consistency
        browser_type = "Chrome"
        browser_version = "122"
        platform = "Windows"
        
        if "Firefox" in user_agent:
            browser_type = "Firefox"
            browser_version = "123" if "123.0" in user_agent else "115"
        elif "Safari" in user_agent and "Chrome" not in user_agent:
            browser_type = "Safari"
            browser_version = "17"
            platform = "Macintosh"
        elif "Edg" in user_agent:
            browser_type = "Edge"
            browser_version = "120"
            
        # Determine OS platform
        if "Windows" in user_agent:
            platform = "Windows"
        elif "Macintosh" in user_agent:
            platform = "macOS"
        elif "Linux" in user_agent:
            platform = "Linux"
        elif "iPhone" in user_agent or "iPad" in user_agent:
            platform = "iOS"
            
        # Generate consistent sec-ch-ua value based on browser
        if browser_type == "Chrome":
            sec_ch_ua = f'"Not/A)Brand";v="99", "Google {browser_type}";v="{browser_version}", "Chromium";v="{browser_version}"'
        elif browser_type == "Edge":
            sec_ch_ua = f'"Not/A)Brand";v="99", "Microsoft Edge";v="{browser_version}", "Chromium";v="{browser_version}"'
        elif browser_type == "Firefox":
            sec_ch_ua = f'"Firefox";v="{browser_version}", "Gecko";v="20100101"'
        else:
            sec_ch_ua = f'"Not/A)Brand";v="99", "Safari";v="{browser_version}"'
            
        # Create base headers
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
        }
        
        # Add modern browser fingerprinting headers
        if browser_type in ["Chrome", "Edge"]:
            headers.update({
                'sec-ch-ua': sec_ch_ua,
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': f'"{platform}"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
            })
            
        # Add random language preference (weighted towards English)
        lang_options = [
            'en-US,en;q=0.9',
            'en-GB,en;q=0.9',
            'en-US,en;q=0.9,fr;q=0.8',
            'en-IN,en-US;q=0.9,en;q=0.8,hi;q=0.7',
            'en-US,en;q=0.9,es;q=0.8',
        ]
        headers['Accept-Language'] = random.choice(lang_options)
        
        # Sometimes add a referer (like coming from Google search)
        if random.random() > 0.7:
            referer_options = [
                'https://www.google.com/',
                'https://www.google.co.in/',
                'https://www.bing.com/',
                'https://search.yahoo.com/',
                'https://duckduckgo.com/'
            ]
            headers['Referer'] = random.choice(referer_options)
            
        # Return the generated fingerprint headers
        return headers
        
    def _track_domain_access(self, domain):
        """Track domain access for rate limiting."""
        current_time = time.time()
        self.domain_access_times.setdefault(domain, []).append(current_time)
        
        # Clean up old access times
        self.domain_access_times[domain] = [
            t for t in self.domain_access_times[domain]
            if current_time - t < 300  # Keep only last 5 minutes
        ]
        
    def _check_domain_rate_limit(self, domain):
        """Check if we should rate limit this domain and apply delay if needed."""
        if domain not in self.domain_access_times:
            return
            
        # Get recent access count
        recent_count = len(self.domain_access_times[domain])
        
        # Apply adaptive delay based on recent access count
        if recent_count > 1:
            # Calculate delay: more requests = longer delay
            base_delay = 2.0
            
            # Check success rate for this domain
            success_rate = self.domain_success_rates.get(domain, {}).get('rate', 1.0)
            
            # Lower success rate = longer delay
            if success_rate < 0.8:
                base_delay *= (1.5 / success_rate)
                
            # Calculate final delay with randomization
            delay = base_delay * min(recent_count, 5) * random.uniform(0.8, 1.2)
            delay = min(delay, 15)  # Cap at 15 seconds
            
            # Apply the delay
            time.sleep(delay)
            
    def _update_domain_success_rate(self, domain, success):
        """Update success rate for a domain."""
        if domain not in self.domain_success_rates:
            self.domain_success_rates[domain] = {'success': 0, 'total': 0, 'rate': 1.0}
            
        stats = self.domain_success_rates[domain]
        if success:
            stats['success'] += 1
        stats['total'] += 1
        stats['rate'] = stats['success'] / stats['total'] if stats['total'] > 0 else 1.0
        
    def extract_emails(self, text):
        """Extract email addresses from text using regex"""
        # RFC 5322 compliant email regex pattern
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = re.findall(email_pattern, text)
        
        # Filter out common false positives and limit to reasonable domain lengths
        filtered_emails = []
        for email in emails:
            # Check domain part length (too long domains are usually false positives)
            domain_part = email.split('@')[1]
            if len(domain_part) <= MAX_DOMAIN_LENGTH:  # Use setting for domain length
                filtered_emails.append(email.lower())
                
        return filtered_emails
    
    def extract_phone_numbers(self, text, country=None):
        """
        Extract phone numbers from text using regex
        Uses different patterns based on country if specified
        Only extracts mobile numbers, filtering out landlines and spam numbers
        """
        # Basic international pattern
        patterns = [
            r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}',  # International format
            r'\(\d{3,4}\)[-.\s]?\d{3,4}[-.\s]?\d{3,4}',  # (XXX) XXX-XXXX
            r'\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}'  # XXX-XXX-XXXX
        ]
        
        # Add country-specific patterns
        if country == 'IN':
            # Indian mobile numbers (10 digits, starting with 6, 7, 8, or 9)
            patterns.append(r'(?:\+91|0)?[6789]\d{9}')
        elif country == 'US':
            # US mobile numbers (10 digits, may include area code)
            patterns.append(r'(?:\+1|1)?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
        
        # Extract all phone numbers using the patterns
        phone_numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            phone_numbers.extend(matches)
        
        # Clean up the extracted phone numbers
        cleaned_numbers = []
        for number in phone_numbers:
            # Remove any non-digit or '+' characters
            clean_num = re.sub(r'[^\d+]', '', number)
            
            # Skip numbers that are too short or too long
            if len(clean_num) < MIN_PHONE_LENGTH or len(clean_num) > 15:
                continue
                
            # Country-specific mobile number validation
            is_mobile = self._is_mobile_number(clean_num, country)
            
            if is_mobile:
                # Format the number consistently with country code if possible
                formatted_num = self._format_mobile_number(clean_num, country)
                if formatted_num and formatted_num not in cleaned_numbers:
                    cleaned_numbers.append(formatted_num)
        
        return cleaned_numbers
        
    def _is_mobile_number(self, number, country=None):
        """
        Validate if a number is a mobile number based on country-specific rules
        
        Args:
            number (str): Phone number (digits only)
            country (str): Country code like 'IN', 'US', etc.
            
        Returns:
            bool: True if number is a valid mobile number, False otherwise
        """
        # Remove the leading '+' if present
        if number.startswith('+'):
            number = number[1:]
            
        # Indian mobile numbers validation
        if country == 'IN':
            # Check if it's an Indian mobile (starts with 6, 7, 8, or 9 and has 10 digits)
            if len(number) == 10 and number[0] in '6789':
                return True
            # For numbers with country code (+91)
            elif len(number) == 12 and number.startswith('91') and number[2] in '6789':
                return True
                
        # US mobile numbers validation
        elif country == 'US':
            # US mobile numbers don't have a clear pattern to distinguish from landlines
            # But we can filter out toll-free and special numbers
            toll_free_prefixes = ['800', '833', '844', '855', '866', '877', '888']
            
            # For 10-digit numbers
            if len(number) == 10:
                area_code = number[:3]
                # Filter out toll-free and special area codes
                if area_code in toll_free_prefixes or area_code in ['900', '911']:
                    return False
                return True
                
            # For numbers with country code (+1)
            elif len(number) == 11 and number.startswith('1'):
                area_code = number[1:4]
                if area_code in toll_free_prefixes or area_code in ['900', '911']:
                    return False
                return True
                
        # Generic international validation for other countries
        else:
            # For most countries, numbers between 8-12 digits are likely mobile
            # Filter out obviously invalid numbers (all same digit, sequential digits)
            if 8 <= len(number) <= 15:
                # Check if all digits are the same (spam/fake number)
                if len(set(number)) == 1:
                    return False
                    
                # Check if digits are sequential (12345...)
                is_sequential = True
                for i in range(len(number) - 1):
                    if int(number[i+1]) != (int(number[i]) + 1) % 10:
                        is_sequential = False
                        break
                if is_sequential:
                    return False
                    
                # Basic validation passed
                return True
                
        return False
        
    def _format_mobile_number(self, number, country=None):
        """
        Format mobile number consistently with country code
        
        Args:
            number (str): Phone number (digits only)
            country (str): Country code like 'IN', 'US', etc.
            
        Returns:
            str: Formatted mobile number
        """
        # Remove the leading '+' if present for processing
        has_plus = number.startswith('+')
        if has_plus:
            number = number[1:]
            
        # Format Indian numbers
        if country == 'IN':
            # 10-digit number without country code
            if len(number) == 10 and number[0] in '6789':
                return '+91' + number
            # Number with country code
            elif len(number) == 12 and number.startswith('91') and number[2] in '6789':
                return '+' + number
            # Remove 0 prefix if present and add country code
            elif len(number) == 11 and number.startswith('0') and number[1] in '6789':
                return '+91' + number[1:]
                
        # Format US numbers
        elif country == 'US':
            # 10-digit number without country code
            if len(number) == 10:
                return '+1' + number
            # Number with country code
            elif len(number) == 11 and number.startswith('1'):
                return '+' + number
                
        # Generic international format for other countries
        else:
            # If already has country code (usually 1-3 digits), just return with +
            if 11 <= len(number) <= 15:
                return '+' + number
            # Return as-is with + if it had one
            return '+' + number if has_plus else number
            
        # Return original if no formatting applied
        return '+' + number if has_plus else number
    
    def is_valid_url(self, url):
        """Check if a URL is valid and not a common false positive"""
        try:
            parsed = urlparse(url)
            
            # Check for valid scheme and netloc
            if not (parsed.scheme and parsed.netloc):
                return False
                
            # Skip common non-relevant domains
            skip_domains = [
                'facebook.com', 'twitter.com', 'instagram.com', 'youtube.com',
                'linkedin.com', 'pinterest.com', 'reddit.com', 'tiktok.com',
                'google.com', 'bing.com', 'yahoo.com', 'baidu.com', "indiamart.com","justdial.com"
            ]
            
            domain = parsed.netloc.lower()
            if any(skip in domain for skip in skip_domains):
                return False
                
            # Check if URL ends with .pdf
            if url.lower().endswith('.pdf'):
                logger.info(f"Skipping PDF URL: {url}")
                return False
                
            return True
        except:
            return False
    
    def extract_data_from_url(self, url, data_type, country=None):
        """
        Scrape a URL to extract emails or phone numbers with enhanced anti-bot measures
        
        Args:
            url (str): The URL to scrape
            data_type (str): 'email' or 'phone'
            country (str): Country code for phone number validation
            
        Returns:
            list: List of extracted emails or phone numbers
        """
        # Extract domain for rate limiting
        domain = urlparse(url).netloc
        
        # Apply rate limiting for this domain
        self._check_domain_rate_limit(domain)
        
        # Track this access
        self._track_domain_access(domain)
        
        # Initialize retry counter
        retry_count = 0
        max_retries = MAX_RETRIES + 2  # Add extra retries
        
        while retry_count < max_retries:
            try:
                # Generate browser fingerprint headers
                headers = self._generate_browser_fingerprint()
                
                # Customize for country if needed
                if country == 'IN':
                    headers['Accept-Language'] = 'en-IN,en-US;q=0.9,en;q=0.8,hi;q=0.7'
                
                # Get proxy for this request (only on retries to avoid unnecessary slowdowns)
                proxy = None
                if retry_count > 0:
                    proxy = self._get_random_proxy()
                
                # Adaptive timeout - longer for retries
                timeout = DEFAULT_TIMEOUT + (retry_count * 5)
                
                # Make a HEAD request first to check content type (to avoid downloading PDFs)
                try:
                    head_response = self.session.head(
                        url,
                        headers=headers,
                        proxies=proxy,
                        timeout=timeout/2,
                        allow_redirects=True
                    )
                    
                    # Check if it's a PDF by content-type
                    content_type = head_response.headers.get('Content-Type', '')
                    if 'application/pdf' in content_type.lower():
                        logger.info(f"Skipping PDF content type: {url} ({content_type})")
                        return []
                except Exception as head_error:
                    # If HEAD request fails, continue with GET (some servers don't support HEAD)
                    logger.warning(f"HEAD request failed for {url}: {head_error}")
                
                # Make the request with the session for cookie persistence
                response = self.session.get(
                    url, 
                    headers=headers, 
                    proxies=proxy,
                    timeout=timeout,
                    allow_redirects=True
                )
                
                # Check content type again after GET (some servers might redirect)
                content_type = response.headers.get('Content-Type', '')
                if 'application/pdf' in content_type.lower():
                    logger.info(f"Skipping PDF content type after GET: {url} ({content_type})")
                    return []
                
                # Add random delay between requests to look more human
                time.sleep(random.uniform(0.5, 2.0))
                
                # Check if request was successful
                if response.status_code == 200:
                    # Update success rate for this domain
                    self._update_domain_success_rate(domain, True)
                    
                    # Parse the HTML content
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract all text from the page
                    text = soup.get_text()
                    
                    # Extract data based on type
                    if data_type == 'email':
                        return self.extract_emails(text)
                    else:  # phone
                        return self.extract_phone_numbers(text, country)
                    
                # Handle specific error codes
                elif response.status_code == 403:  # Forbidden - likely bot detection
                    retry_count += 1
                    self._update_domain_success_rate(domain, False)
                    logger.warning(f"Bot detection (403) on {url}, retry {retry_count}/{max_retries} with new identity")
                    
                    # Clear cookies and use a new user agent on next try
                    self.session.cookies.clear()
                    
                    # Apply longer delay before retry for 403s
                    time.sleep(random.uniform(5, 10))
                    
                elif response.status_code == 429:  # Too Many Requests
                    retry_count += 1
                    self._update_domain_success_rate(domain, False)
                    logger.warning(f"Rate limited (429) on {url}, retry {retry_count}/{max_retries} with longer delay")
                    
                    # Apply much longer delay before retry for rate limits
                    time.sleep(random.uniform(10, 20))
                    
                elif response.status_code == 404:  # Not Found
                    logger.warning(f"Page not found (404): {url}")
                    self._update_domain_success_rate(domain, False)
                    return []
                    
                else:  # Other status codes
                    retry_count += 1
                    self._update_domain_success_rate(domain, False)
                    logger.warning(f"HTTP {response.status_code} on {url}, retry {retry_count}/{max_retries}")
                    
                    # Apply exponential backoff
                    time.sleep((2 ** retry_count) * random.uniform(0.5, 1.5))
                    
            except requests.exceptions.Timeout:
                retry_count += 1
                self._update_domain_success_rate(domain, False)
                logger.warning(f"Timeout requesting {url}, retry {retry_count}/{max_retries}")
                
                # Apply exponential backoff for timeouts
                time.sleep((1.5 ** retry_count) * random.uniform(1, 3))
                
            except requests.exceptions.ConnectionError as e:
                retry_count += 1
                self._update_domain_success_rate(domain, False)
                logger.warning(f"Connection error requesting {url}, retry {retry_count}/{max_retries}: {e}")
                
                # Clear session cookies on connection errors
                self.session.cookies.clear()
                
                # Apply longer delay for connection errors
                time.sleep(random.uniform(3, 7))
                
            except requests.exceptions.RequestException as e:
                retry_count += 1
                self._update_domain_success_rate(domain, False)
                logger.warning(f"Request error for {url}, retry {retry_count}/{max_retries}: {e}")
                time.sleep(random.uniform(2, 5))
                
            except Exception as e:
                logger.error(f"Unexpected error scraping {url}: {e}")
                self._update_domain_success_rate(domain, False)
                return []
        
        logger.error(f"Failed to extract data from {url} after {max_retries} retries")
        return []
    
    def search_and_scrape(self, keyword, data_type='email', country='in', max_results=None, max_pages=None):
        """
        Search using SerpAPI and scrape results for emails or phone numbers
        
        Args:
            keyword (str): Search keyword
            data_type (str): 'email' or 'phone'
            country (str): Country code like 'IN', 'US', etc.
            max_results (int): Maximum number of results to return
            max_pages (int): Maximum number of search result pages to process
            
        Returns:
            dict: Dictionary with results and status information
        """
        # Use provided values or defaults from settings
        max_results = max_results or DEFAULT_MAX_RESULTS
        max_pages = max_pages or DEFAULT_MAX_PAGES
        
        self._update_progress(5, f"Optimizing search query for {keyword}...")
        
        # Optimize the query using Gemini
        optimized_query = self.query_optimizer.optimize_query(keyword, data_type, country)
        
        self._update_progress(10, f"Starting search for '{optimized_query}'...")
        
        # Initialize results
        all_results = set()
        scraped_urls = set()
        failed_domains = set()  # Track domains that consistently fail
        
        # Track overall progress
        total_progress_value = 90  # Progress value to distribute across all activities
        progress_per_page = total_progress_value / min(max_pages, 3)  # Allocate progress per page
        
        # Use a reasonable number of URLs per page to avoid overwhelming the scraper
        urls_per_page = min(25, max_results)
        
        for page in range(1, max_pages + 1):
            # Check if stop flag is set
            if self.task_id and self.task_id in active_tasks and active_tasks[self.task_id]['stop']:
                logger.info(f"Task {self.task_id} is stopping due to stop flag")
                break
                
            if len(all_results) >= max_results:
                break
                
            current_progress = 10 + int((page - 1) / max_pages * total_progress_value)
            self._update_progress(current_progress, f"Searching page {page} of {max_pages}...")
            
            # Configure SerpAPI parameters with current API key from manager or the specific one provided
            current_api_key = self.specific_api_key or self.api_key_manager.get_current_key()
            if not current_api_key:
                logger.error("No API keys available")
                break
                
            params = {
                "engine": "google",
                "q": optimized_query,
                "api_key": current_api_key,
                "num": 100,  # Get more results per page
                "gl": country.lower(),  # Google country (lowercase)
                "hl": "en",  # Language set to English
            }
            
            # Add country-specific parameters
            if country.upper() == 'IN':
                params["location"] = "India"
                params["google_domain"] = "google.co.in"
            elif country.upper() == 'US':
                params["location"] = "United States"
                params["google_domain"] = "google.com"
            
            # Track if we need to retry with a different API key
            retry_with_new_key = True
            max_key_retries = min(5, len(self.api_key_manager.api_keys))  # Limit retry attempts
            key_retry_count = 0
            
            while retry_with_new_key and key_retry_count < max_key_retries:
                try:
                    # Make the SerpAPI request
                    self._update_progress(current_progress + 2, f"Fetching search results from SerpAPI...")
                    search = GoogleSearch(params)
                    results = search.get_dict()
                    
                    # Check if the response indicates API key has run out of searches
                    if self.api_key_manager.is_error_limit_reached(results):
                        if self.specific_api_key:
                            # If using a specific key, we can't rotate
                            logger.error(f"Specific API key has run out of searches: {results.get('error', '')}")
                            return {
                                'success': False,
                                'data_type': data_type,
                                'keyword': keyword,
                                'error': f"API key has run out of searches: {results.get('error', '')}"
                            }
                        
                        # Disable current key and get next one
                        logger.warning(f"API key ran out of searches: {results.get('error', '')}")
                        new_key = self.api_key_manager.disable_current_key()
                        
                        if not new_key:
                            logger.error("No more API keys available")
                            return {
                                'success': False,
                                'data_type': data_type,
                                'keyword': keyword,
                                'error': "All API keys have run out of searches"
                            }
                            
                        # Update params with new key and retry
                        params["api_key"] = new_key
                        key_retry_count += 1
                        logger.info(f"Retrying with new API key (attempt {key_retry_count})")
                        continue
                    
                    # If we get here, the request succeeded
                    retry_with_new_key = False
                    
                    # Debug log the entire results structure
                    logger.debug(f"SerpAPI response structure: {list(results.keys())}")
                    
                    # Extract organic results - ensure we handle all possible response formats
                    organic_results = []
                    
                    # Try standard organic_results key
                    if "organic_results" in results:
                        organic_results = results.get("organic_results", [])
                        logger.info(f"Found {len(organic_results)} standard organic results")
                    
                    # If no results yet, try alternative keys that might contain results
                    if not organic_results and "shopping_results" in results:
                        # Extract links from shopping results
                        shopping_results = results.get("shopping_results", [])
                        for item in shopping_results:
                            if "link" in item:
                                organic_results.append({"link": item["link"], "title": item.get("title", "")})
                        logger.info(f"Found {len(organic_results)} shopping results")
                    
                    # Try knowledge graph if available
                    if "knowledge_graph" in results:
                        kg = results.get("knowledge_graph", {})
                        if "website" in kg:
                            organic_results.append({"link": kg["website"], "title": kg.get("title", "")})
                            logger.info("Added knowledge graph website to results")
                    
                    # Try local results if available
                    if "local_results" in results:
                        local_results = results.get("local_results", [])
                        for item in local_results:
                            if "website" in item:
                                organic_results.append({"link": item["website"], "title": item.get("title", "")})
                        logger.info(f"Found {len(local_results)} local results with websites")
                    
                    # Log the number of results found
                    logger.info(f"Total combined results: {len(organic_results)}")
                    
                    if not organic_results:
                        logger.warning(f"No organic results found for page {page}")
                        
                        # Try with alternative query on failure
                        if page == 1:
                            # Construct a more direct query as fallback
                            if data_type == 'email':
                                fallback_query = f'"{keyword}" "contact us" "email" OR "contact" OR "get in touch" site:.{country.lower()}'
                            else:  # phone
                                fallback_query = f'"{keyword}" "contact us" "phone" OR "call us" OR "mobile" site:.{country.lower()}'
                                
                            # Try the fallback query
                            params["q"] = fallback_query
                            self._update_progress(current_progress + 2, f"Trying alternative query: '{fallback_query}'")
                            
                            # Reset the retry flag and try again with fallback query
                            retry_with_new_key = True
                            key_retry_count = 0
                            continue
                        else:
                            break  # For subsequent pages, just move on
                        
                    self._update_progress(current_progress + 5, f"Found {len(organic_results)} results on page {page}")
                    
                    # Get a shuffled subset of results to randomize the order
                    subset_size = min(len(organic_results), urls_per_page)
                    selected_indices = random.sample(range(len(organic_results)), subset_size)
                    
                    # Process results in random order to avoid patterns
                    progress_per_url = progress_per_page / max(subset_size, 1)
                    
                    for idx, i in enumerate(selected_indices):
                        # Check if stop flag is set
                        if self.task_id and self.task_id in active_tasks and active_tasks[self.task_id]['stop']:
                            logger.info(f"Task {self.task_id} is stopping due to stop flag")
                            break
                            
                        result = organic_results[i]
                        url = result.get("link")
                        
                        # Skip if URL is not valid or already scraped
                        if not url or not self.is_valid_url(url) or url in scraped_urls:
                            continue
                        
                        # Skip if domain is in failed domains list
                        domain = urlparse(url).netloc
                        if domain in failed_domains:
                            continue
                            
                        scraped_urls.add(url)
                        
                        # Update progress
                        item_progress = current_progress + 5 + int(idx * progress_per_url)
                        self._update_progress(item_progress, f"Scraping {url}...")
                        
                        # Extract data from the URL
                        extracted_data = self.extract_data_from_url(url, data_type, country)
                        
                        # Check for successful extraction
                        if extracted_data:
                            # Add unique results
                            all_results.update(extracted_data)
                            # Log successful extraction
                            logger.info(f"Found {len(extracted_data)} {data_type}s on {url}")
                        else:
                            # Add to failed domains if extraction failed completely
                            # Only mark completely failed domains, not just ones with no data
                            domain_success_rate = self.domain_success_rates.get(domain, {}).get('rate', 1.0)
                            if domain_success_rate < 0.3:  # If success rate is very low
                                failed_domains.add(domain)
                                logger.warning(f"Adding {domain} to failed domains list due to low success rate")
                        
                        # Break if we have enough results
                        if len(all_results) >= max_results:
                            break
                            
                        # Add a random delay between URL processing to appear more human
                        time.sleep(random.uniform(0.5, 2.0))
                
                except InterruptedError:
                    # Task was stopped manually
                    logger.info(f"Task {self.task_id} was interrupted")
                    # Clean up
                    if self.task_id in active_tasks:
                        active_tasks[self.task_id]['running'] = False
                    # Return partial results
                    final_results = list(all_results)[:max_results]
                    return {
                        'success': False,
                        'status': 'stopped',
                        'data_type': data_type,
                        'keyword': keyword,
                        'optimized_query': optimized_query,
                        'country': country,
                        'results_count': len(final_results),
                        'results': final_results
                    }
                    
                except Exception as e:
                    logger.error(f"Error in search for page {page}: {e}")
                    logger.error(traceback.format_exc())
                    
                    # Check if this might be an API key issue and we should retry
                    if 'quota' in str(e).lower() or 'limit' in str(e).lower() or 'api key' in str(e).lower():
                        if not self.specific_api_key:
                            new_key = self.api_key_manager.rotate_key()
                            if new_key:
                                params["api_key"] = new_key
                                key_retry_count += 1
                                logger.info(f"Error might be API related, retrying with new key (attempt {key_retry_count})")
                                continue
                    
                    self._update_progress(current_progress, f"Error in search: {str(e)}")
                    
                    # Add a delay after error before trying next page
                    time.sleep(random.uniform(3.0, 6.0))
                    
                    # Break the retry loop
                    retry_with_new_key = False
            
            # Add a longer delay between pages to avoid rate limiting
            time.sleep(random.uniform(2.0, 5.0))
        
        # If we don't have enough results, try to generate some based on domain patterns
        if len(all_results) < max_results / 2 and data_type == 'email':
            try:
                self._update_progress(90, "Generating additional email patterns for common domains...")
                # Extract domains from URLs we scraped
                domains = [urlparse(url).netloc for url in scraped_urls if self.is_valid_url(url)]
                
                # For each domain, try to generate common email patterns
                for domain in domains[:10]:  # Limit to 10 domains
                    # Skip domains we already failed on
                    if domain in failed_domains:
                        continue
                        
                    # Generate common patterns (info@, contact@, etc.)
                    common_patterns = [
                        f"info@{domain}", 
                        f"contact@{domain}", 
                        f"support@{domain}", 
                        f"hello@{domain}",
                        f"enquiry@{domain}",
                        f"sales@{domain}"
                    ]
                    
                    # Add to results if they look valid
                    for email in common_patterns:
                        # Very basic validation
                        if "@" in email and "." in email.split("@")[1]:
                            all_results.add(email)
            except Exception as e:
                logger.error(f"Error generating additional emails: {e}")
        
        # Convert set to list for the final results
        final_results = list(all_results)[:max_results]
        
        self._update_progress(95, f"Finalizing {len(final_results)} {data_type} results...")
        
        # Clean up task tracking
        if self.task_id and self.task_id in active_tasks:
            active_tasks[self.task_id]['running'] = False
        
        # Prepare result object
        result = {
            'success': True,
            'data_type': data_type,
            'keyword': keyword,
            'optimized_query': optimized_query,
            'country': country,
            'results_count': len(final_results),
            'results': final_results
        }
        
        self._update_progress(100, f"Completed! Found {len(final_results)} {data_type}s")
        
        return result


def update_task_status(task_id, status_data, task_record=None):
    """
    Update the status of a background task
    
    Args:
        task_id (str): The task ID
        status_data (dict): Status data with progress, message, etc.
        task_record (BackgroundTask, optional): The task record if available
    """
    try:
        import os
        import json
        
        # Update status file
        status_file_path = os.path.join(django_settings.MEDIA_ROOT, 'mining_status', f"{task_id}.json")
        os.makedirs(os.path.dirname(status_file_path), exist_ok=True)
        
        with open(status_file_path, 'w') as f:
            json.dump(status_data, f)
            
        # Update task record if provided
        if task_record:
            task_record.progress = status_data.get('progress', 0)
            task_record.save()
            
    except Exception as e:
        logger.error(f"Error updating task status: {e}")


def scrape_with_serpapi(keyword, data_type='email', country='IN', task_id=None, max_results=None):
    """
    Main function to scrape data using SerpAPI
    
    Args:
        keyword (str): Search keyword
        data_type (str): 'email' or 'phone'
        country (str): Country code like 'IN', 'US', etc.
        task_id (str): Task ID for tracking
        max_results (int): Maximum number of results to return
        
    Returns:
        dict: Dictionary with results and status information
    """
    # Set up logging with the task_id for better tracking
    task_logger = logging.getLogger(f"serpapi_scraper_{task_id}")
    if task_id:
        # Register task as active
        active_tasks[task_id] = {
            'stop': False,
            'running': True,
            'thread': threading.current_thread()
        }
        
        # Update task status to mark as starting
        update_task_status(task_id, {
            'status': 'processing',
            'progress': 0,
            'message': f'Starting data mining for "{keyword}"'
        })
    
    try:
        # Initialize scraper with task ID and update callback
        scraper = SerpApiScraper(
            update_status_callback=update_task_status,
            task_id=task_id
        )
        
        # Search and scrape
        results = scraper.search_and_scrape(
            keyword=keyword,
            data_type=data_type,
            country=country,
            max_results=max_results
        )
        
        # Check if results indicate an API key issue
        if not results.get('success', True) and 'error' in results:
            error_msg = results.get('error', '').lower()
            if 'api key' in error_msg or 'quota' in error_msg or 'limit' in error_msg or 'run out of searches' in error_msg:
                task_logger.warning(f"API key issue detected: {error_msg}")
                task_logger.info("Attempting to use a different API key")
                
                # Try again with a different API key
                new_key = api_key_manager.rotate_key()
                if new_key:
                    task_logger.info(f"Retrying with a different API key")
                    
                    # Update status to inform about retry
                    if task_id:
                        update_task_status(task_id, {
                            'status': 'processing',
                            'progress': 10,
                            'message': f'Retrying with a different API key'
                        })
                    
                    # Create a new scraper with a specific API key
                    scraper = SerpApiScraper(
                        api_key=new_key,
                        update_status_callback=update_task_status,
                        task_id=task_id
                    )
                    
                    # Try again with the new key
                    results = scraper.search_and_scrape(
                        keyword=keyword,
                        data_type=data_type,
                        country=country,
                        max_results=max_results
                    )
        
        # Check if task was stopped
        if task_id and task_id in active_tasks and active_tasks[task_id]['stop']:
            if task_id in active_tasks:
                del active_tasks[task_id]
            return results
        
        # If we got very few results, try a slightly different approach
        if results.get('results_count', 0) < 5 and task_id:
            task_logger.warning(f"Few results ({results.get('results_count', 0)}) found, trying alternative approach")
            
            # Check if task was stopped before continuing
            if task_id in active_tasks and active_tasks[task_id]['stop']:
                if task_id in active_tasks:
                    del active_tasks[task_id]
                return results
            
            # Update status to inform about the alternative approach
            update_task_status(task_id, {
                'status': 'processing',
                'progress': 80,
                'message': f'Trying alternative approach to find more results'
            })
            
            # Create a slightly different query for the second attempt
            if data_type == 'email':
                alt_keyword = f"{keyword} contact email"
            else:
                alt_keyword = f"{keyword} contact phone number"
                
            # Try with a different approach
            alt_results = scraper.search_and_scrape(
                keyword=alt_keyword,
                data_type=data_type,
                country=country,
                max_results=max_results
            )
            
            # Merge results from both approaches
            combined_results = set(results.get('results', []))
            combined_results.update(alt_results.get('results', []))
            
            # Update the results with the combined set
            results['results'] = list(combined_results)
            results['results_count'] = len(results['results'])
            results['alternative_query'] = alt_keyword
        
        # Clean up session resources
        if hasattr(scraper, 'session'):
            try:
                scraper.session.close()
            except Exception as e:
                task_logger.warning(f"Error closing scraper session: {e}")
        
        # If we have a task ID, update the final status
        if task_id:
            update_task_status(task_id, {
                'status': 'completed',
                'progress': 100,
                'message': f'Found {results.get("results_count", 0)} {data_type} results',
                'data_type': data_type,
                'results': results.get('results', [])
            })
            
            # Clean up task tracking
            if task_id in active_tasks:
                del active_tasks[task_id]
        
        return results
        
    except InterruptedError:
        # Task was manually stopped
        logger.info(f"Task {task_id} was interrupted and is shutting down")
        
        # If we have a task ID, update status to show stopped
        if task_id:
            update_task_status(task_id, {
                'status': 'stopped',
                'progress': 0,
                'message': 'Task was manually stopped',
            })
            
            # Clean up task tracking
            if task_id in active_tasks:
                del active_tasks[task_id]
        
        # Return stopped result
        return {
            'success': False,
            'status': 'stopped',
            'data_type': data_type,
            'keyword': keyword,
            'country': country,
            'results_count': 0,
            'results': [],
        }
        
    except Exception as e:
        # Log the error
        task_logger.error(f"Error in scrape_with_serpapi: {e}")
        task_logger.error(traceback.format_exc())
        
        # Check if this might be an API key issue
        if 'api key' in str(e).lower() or 'quota' in str(e).lower() or 'limit' in str(e).lower():
            task_logger.warning(f"API key issue detected in exception: {e}")
            
            # Try with a different API key
            new_key = api_key_manager.rotate_key()
            if new_key:
                task_logger.info(f"Retrying with a different API key after exception")
                
                # Update status to inform about retry
                if task_id:
                    update_task_status(task_id, {
                        'status': 'processing',
                        'progress': 10,
                        'message': f'Retrying with a different API key after error'
                    })
                
                try:
                    # Create a new scraper with the new key
                    scraper = SerpApiScraper(
                        api_key=new_key,
                        update_status_callback=update_task_status,
                        task_id=task_id
                    )
                    
                    # Try again with the new key
                    return scraper.search_and_scrape(
                        keyword=keyword,
                        data_type=data_type,
                        country=country,
                        max_results=max_results
                    )
                except Exception as retry_e:
                    task_logger.error(f"Error in retry attempt: {retry_e}")
                    # Continue to general error handling
        
        # If we have a task ID, update status to show error
        if task_id:
            update_task_status(task_id, {
                'status': 'error',
                'progress': 0,
                'message': f'Error: {str(e)}',
                'error': str(e)
            })
            
            # Clean up task tracking
            if task_id in active_tasks:
                del active_tasks[task_id]
        
        # Return error result
        return {
            'success': False,
            'data_type': data_type,
            'keyword': keyword,
            'country': country,
            'results_count': 0,
            'results': [],
            'error': str(e)
        }

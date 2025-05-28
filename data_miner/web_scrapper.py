import argparse
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup, Comment
import re
import random
import time
import csv
from urllib.parse import quote, urlparse, urljoin, unquote
import os
import socket
import threading
from typing import List, Dict, Tuple, Optional, Set, Union
import logging
from fake_useragent import UserAgent
import json
from playwright.async_api import Browser, Page, Playwright, TimeoutError as PlaywrightTimeoutError, async_playwright
import tldextract
import warnings
import asyncio
import sys
import platform
import traceback
from collections import defaultdict, deque

# Add Gemini API for query optimization
import google.generativeai as genai
from google.api_core.exceptions import InvalidArgument

# Import specialized Google browser search module
try:
    # Try absolute import first (when used as a package)
    from data_miner.google_browser_search import search_google as browser_search_google
except ImportError:
    # Fall back to relative import (when run as a script)
    from google_browser_search import search_google as browser_search_google

# Helper function to run async code in synchronous methods
def run_async(coroutine):
    """Run an async function in a synchronous context."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # If no running loop exists, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    try:
        return loop.run_until_complete(coroutine)
    finally:
        # Don't close the loop here to avoid issues with reusing it
        pass

# Import our improved validation functions
try:
    # Try relative import first (when used as a package)
    from .improved_validators import validate_email, validate_indian_phone
except ImportError:
    # Fall back to absolute import (when run as a script)
    from improved_validators import validate_email, validate_indian_phone

# Fix for Windows asyncio pipe ResourceWarning issues
if platform.system() == 'Windows':
    # Silence the resource warnings that occur in Windows with asyncio
    import warnings
    warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*")
    
    # Replace the default event loop for Windows
    if sys.version_info >= (3, 8):
        # For Python 3.8+, use WindowsProactorEventLoopPolicy
        # This provides better compatibility with Playwright and subprocess operations
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        # Create a new proactor event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    else:
        # For older Python versions
        asyncio.set_event_loop(asyncio.ProactorEventLoop())

# Global event loop management to prevent event loop conflicts
_GLOBAL_EVENT_LOOP = None

# Advanced rate limiting and request throttling
class RateLimiter:
    """
    Advanced rate limiter to prevent getting blocked by domains
    Implements dynamic delay, exponential backoff, and success rate monitoring
    """
    
    def __init__(self):
        # Track request times per domain
        self.request_times = defaultdict(deque)
        self.success_rates = defaultdict(lambda: {'success': 0, 'total': 0})
        self.error_counts = defaultdict(int)
        self.last_request_time = defaultdict(float)
        
        # Configuration
        self.min_delay = 1.0  # Minimum delay between requests
        self.max_delay = 30.0  # Maximum delay between requests
        self.window_size = 60  # Time window in seconds
        self.max_requests_per_window = 10  # Maximum requests per time window
        self.error_threshold = 3  # Number of errors before increasing delay
        self.success_rate_threshold = 0.7  # Minimum success rate to maintain current delay
        
        # Adaptive delay factors
        self.base_delay = 2.0
        self.delay_multiplier = 1.5
        self.max_delay_multiplier = 5.0
        
    def should_delay_request(self, domain):
        """Check if a request should be delayed based on rate limiting rules."""
        current_time = time.time()
        base_domain = self._extract_base_domain(domain)
        
        # Get the request history for this domain
        request_history = self.request_times[base_domain]
        
        # Remove old requests outside the window
        while request_history and current_time - request_history[0] > self.window_size:
            request_history.popleft()
        
        # Check if we've exceeded the request limit
        if len(request_history) >= self.max_requests_per_window:
            return True
            
        # Check if we need to enforce minimum delay
        last_request = self.last_request_time[base_domain]
        if current_time - last_request < self.min_delay:
            return True
            
        return False
        
    def calculate_required_delay(self, domain):
        """Calculate the required delay before making the next request."""
        current_time = time.time()
        base_domain = self._extract_base_domain(domain)
        
        # Get the request history for this domain
        request_history = self.request_times[base_domain]
        
        # Calculate base delay
        delay = self.base_delay
        
        # Adjust delay based on error rate
        error_count = self.error_counts[base_domain]
        if error_count > self.error_threshold:
            delay *= min(self.delay_multiplier ** (error_count - self.error_threshold),
                        self.max_delay_multiplier)
        
        # Adjust delay based on success rate
        success_rate = self.get_success_rate(base_domain)
        if success_rate < self.success_rate_threshold:
            delay *= (1 + (self.success_rate_threshold - success_rate))
        
        # Ensure delay is within bounds
        delay = max(self.min_delay, min(delay, self.max_delay))
        
        # Add randomization to avoid patterns
        delay *= random.uniform(0.8, 1.2)
        
        return delay
        
    def _extract_base_domain(self, domain):
        """Extract the base domain from a full domain name."""
        try:
            extracted = tldextract.extract(domain)
            return f"{extracted.domain}.{extracted.suffix}"
        except Exception:
            return domain
            
    def record_request(self, domain):
        """Record a request for rate limiting purposes."""
        current_time = time.time()
        base_domain = self._extract_base_domain(domain)
        
        # Add current time to request history
        self.request_times[base_domain].append(current_time)
        self.last_request_time[base_domain] = current_time
        
        # Clean up old requests
        while self.request_times[base_domain] and current_time - self.request_times[base_domain][0] > self.window_size:
            self.request_times[base_domain].popleft()
            
    def record_success(self, domain):
        """Record a successful request."""
        base_domain = self._extract_base_domain(domain)
        self.success_rates[base_domain]['success'] += 1
        self.success_rates[base_domain]['total'] += 1
        self.error_counts[base_domain] = max(0, self.error_counts[base_domain] - 1)
        
    def record_error(self, domain, status_code=None):
        """Record a failed request."""
        base_domain = self._extract_base_domain(domain)
        self.success_rates[base_domain]['total'] += 1
        self.error_counts[base_domain] += 1
        
        # Adjust error count based on status code
        if status_code == 429:  # Too Many Requests
            self.error_counts[base_domain] += 2
        elif status_code == 403:  # Forbidden
            self.error_counts[base_domain] += 1
            
    def get_success_rate(self, domain=None):
        """Get the success rate for a domain or overall."""
        if domain:
            base_domain = self._extract_base_domain(domain)
            stats = self.success_rates[base_domain]
            return stats['success'] / max(1, stats['total'])
        else:
            total_success = sum(stats['success'] for stats in self.success_rates.values())
            total_requests = sum(stats['total'] for stats in self.success_rates.values())
            return total_success / max(1, total_requests)
            
    def adaptive_delay(self, domain, importance=1.0):
        """Calculate an adaptive delay based on domain history and importance."""
        base_delay = self.calculate_required_delay(domain)
        
        # Adjust delay based on importance (lower importance = longer delay)
        adjusted_delay = base_delay * (2 - importance)
        
        # Add randomization
        final_delay = adjusted_delay * random.uniform(0.9, 1.1)
        
        return max(self.min_delay, min(final_delay, self.max_delay))
    
    def _extract_base_domain(self, domain):
        """Extract the base domain from a full domain name"""
        if not domain:
            return "unknown"
        
        # Handle common search engines specially to ensure proper rate limiting
        if 'google' in domain:
            return 'google.com'
        if 'bing' in domain:
            return 'bing.com'
        if 'duckduckgo' in domain:
            return 'duckduckgo.com'
        
        # Extract base domain using tldextract
        try:
            extracted = tldextract.extract(domain)
            return f"{extracted.domain}.{extracted.suffix}"
        except:
            # Fallback for parsing errors
            parts = domain.split('.')
            if len(parts) >= 2:
                return '.'.join(parts[-2:])
            return domain

    def record_request(self, domain):
        """Record that a request is being made to a domain"""
        with self.lock:
            base_domain = self._extract_base_domain(domain)
            
            # Record request time
            if base_domain not in self.request_times:
                self.request_times[base_domain] = []
            
            # Keep only recent request times (last 24 hours)
            cutoff = datetime.now() - timedelta(hours=24)
            self.request_times[base_domain] = [
                t for t in self.request_times[base_domain] if t > cutoff
            ]
            
            # Add current request time
            self.request_times[base_domain].append(datetime.now())
            
            # Increment active requests counter
            self.active_requests[base_domain] = self.active_requests.get(base_domain, 0) + 1

    def record_success(self, domain):
        """Record a successful request to a domain"""
        with self.lock:
            base_domain = self._extract_base_domain(domain)
            
            # Update success record
            if base_domain not in self.success_record:
                self.success_record[base_domain] = {'success': 0, 'failure': 0}
            
            self.success_record[base_domain]['success'] += 1
            
            # Reduce error count when successful
            if base_domain in self.error_count and self.error_count[base_domain] > 0:
                self.error_count[base_domain] = max(0, self.error_count[base_domain] - 0.5)
            
            # Remove rate limit marking if present
            if base_domain in self.rate_limited:
                del self.rate_limited[base_domain]
            
            # Decrement active requests counter
            if base_domain in self.active_requests:
                self.active_requests[base_domain] = max(0, self.active_requests[base_domain] - 1)

    def record_error(self, domain, status_code=None):
        """
        Record a failed request to a domain
        
        Args:
            domain (str): The domain that returned an error
            status_code (int, optional): HTTP status code if available
        """
        with self.lock:
            base_domain = self._extract_base_domain(domain)
            
            # Update failure record
            if base_domain not in self.success_record:
                self.success_record[base_domain] = {'success': 0, 'failure': 0}
            
            self.success_record[base_domain]['failure'] += 1
            
            # Increment error count for backoff calculation
            if base_domain not in self.error_count:
                self.error_count[base_domain] = 0
            
            # More severe increment for rate limiting
            if status_code == 429:  # Too Many Requests
                self.error_count[base_domain] += 2
                
                # Record rate limiting
                backoff_time = min(60 * (2 ** self.error_count[base_domain]), self.max_backoff)
                self.rate_limited[base_domain] = (datetime.now(), backoff_time)
                
                logging.warning(f"⚠️ Rate limited by {base_domain} (429 Too Many Requests). Backing off for {backoff_time:.1f} seconds")
            elif status_code and status_code >= 400:
                # Less severe for other error codes
                self.error_count[base_domain] += 1
            else:
                # Generic error (no status code)
                self.error_count[base_domain] += 0.5
            
            # Decrement active requests counter
            if base_domain in self.active_requests:
                self.active_requests[base_domain] = max(0, self.active_requests[base_domain] - 1)

    def get_success_rate(self, domain=None):
        """
        Get the success rate for a domain or overall
        
        Args:
            domain (str, optional): Domain to get success rate for
            
        Returns:
            float: Success rate between 0 and 1
        """
        with self.lock:
            if domain:
                base_domain = self._extract_base_domain(domain)
                record = self.success_record.get(base_domain, {'success': 0, 'failure': 0})
                total = record['success'] + record['failure']
                return record['success'] / total if total > 0 else 1.0
            else:
                # Calculate overall success rate
                total_success = sum(r['success'] for r in self.success_record.values())
                total_failure = sum(r['failure'] for r in self.success_record.values())
                total = total_success + total_failure
                return total_success / total if total > 0 else 1.0

    def adaptive_delay(self, domain, importance=1.0):
        """
        Apply an adaptive delay for the domain based on history
        
        Args:
            domain (str): Domain to delay for
            importance (float): Importance factor (lower means longer delay is acceptable)
        """
        should_delay, delay_time = self.should_delay_request(domain)
        
        if should_delay:
            # Adjust delay based on importance (lower importance can wait longer)
            adjusted_delay = delay_time / max(0.1, importance)
            
            # Add some randomness
            adjusted_delay *= random.uniform(0.8, 1.2)
            
            # Apply the delay
            time.sleep(adjusted_delay)
        
        # Record this request
        self.record_request(domain)

def get_or_create_event_loop():
    """Get the current event loop or create a new one if needed.
    
    This function ensures we reuse the same event loop where possible
    to avoid issues with asyncio.
    
    Returns:
        asyncio.AbstractEventLoop: The event loop to use
    """
    global _GLOBAL_EVENT_LOOP
    
    # If we already have a global event loop that's still usable, return it
    if _GLOBAL_EVENT_LOOP is not None and not _GLOBAL_EVENT_LOOP.is_closed():
        return _GLOBAL_EVENT_LOOP
    
    # If we're on Windows, always set the ProactorEventLoop policy
    if platform.system() == 'Windows':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    try:
        # Try to get the current event loop
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("Event loop is closed")
        _GLOBAL_EVENT_LOOP = loop
        return loop
    except RuntimeError:
        # Create a new event loop if needed
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _GLOBAL_EVENT_LOOP = loop
        return loop

def extract_json_ld(html_content: str) -> List[Dict]:
    """
    Extract structured data from JSON-LD script tags in the HTML content.
    
    Args:
        html_content: HTML content to parse
        
    Returns:
        List of dictionaries containing the JSON-LD data
    """
    results = []
    if not html_content:
        return results
        
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_ld_scripts:
            try:
                # Get the script content
                json_text = script.string
                if not json_text:
                    continue
                    
                # Clean the JSON text to handle common issues
                # Remove CDATA sections
                if '<![CDATA[' in json_text and ']]>' in json_text:
                    json_text = json_text.split('<![CDATA[')[1].split(']]>')[0]
                    
                # Fix common JSON syntax errors
                json_text = json_text.strip()
                # Fix trailing commas before closing brackets
                json_text = re.sub(r',\s*}', '}', json_text)
                json_text = re.sub(r',\s*]', ']', json_text)
                    
                # Parse the JSON
                data = json.loads(json_text)
                
                # Handle case where the JSON-LD is a list
                if isinstance(data, list):
                    results.extend(data)
                # Handle case where the JSON-LD is a single object
                else:
                    results.append(data)
            except json.JSONDecodeError as e:
                logging.debug(f"JSON decode error in JSON-LD: {e}")
                # Try to extract partial data using regex for common patterns
                try:
                    # Extract email pattern
                    email_matches = re.findall(r'"email"\s*:\s*"([^"]+@[^"]+)"', json_text)
                    for email in email_matches:
                        results.append({"email": email})
                        
                    # Extract phone pattern
                    phone_matches = re.findall(r'"telephone"\s*:\s*"([^"]+)"', json_text)
                    for phone in phone_matches:
                        results.append({"telephone": phone})
                except Exception:
                    pass
            except Exception as e:
                logging.debug(f"Error processing JSON-LD: {e}")
    except Exception as e:
        logging.debug(f"Error extracting JSON-LD: {e}")
        
    return results


class ContactScraper:
    def __init__(self, use_browser=True, debug_mode=False, task_id=None):
        # Set up logging
        self.logger = logging.getLogger('ContactScraper')
        self.logger.setLevel(logging.DEBUG if debug_mode else logging.INFO)
        
        # Clear existing handlers to avoid duplicates
        if self.logger.handlers:
            for handler in self.logger.handlers:
                self.logger.removeHandler(handler)
                
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Add console handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        ch.setLevel(logging.WARNING)  # Only warnings and above to console
        self.logger.addHandler(ch)
        
        # Add file handler
        try:
            # Create logs directory if it doesn't exist
            os.makedirs('scraper_logs', exist_ok=True)
            
            # Create a timestamped log file, include task_id if available
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if task_id:
                log_filename = f"scraper_{timestamp}_task_{task_id}.log"
            else:
                log_filename = f"scraper_{timestamp}_manual.log"
                
            log_file_path = os.path.join('scraper_logs', log_filename)
            fh = logging.FileHandler(log_file_path)
            fh.setFormatter(formatter)
            fh.setLevel(logging.INFO)  # Log info and above to file
            self.logger.addHandler(fh)
            
            self.log_file_path = log_file_path
            self.logger.info(f"Logging to file: {self.log_file_path}")
        except Exception as e:
            print(f"Warning: Could not set up file logging: {e}")
            self.log_file_path = None
        
        self.debug_mode = debug_mode
        self.use_browser = use_browser
        self.task_id = task_id  # Store task_id for future reference
        
        # Initialize rate limiter for advanced request throttling
        self.rate_limiter = RateLimiter()
        
        # Initialize counters
        self.captcha_detected_domains = set()
        self.blocked_domains = set()
        self.successful_domains = set()
        
        # Initialize browser components
        self.browser = None
        self.context = None
        self.page = None
        self.browser_initialized = False
        
        # Initialize default proxy configuration
        self.proxy_list = [None]  # Start with direct connection
        self.current_proxy_index = 0
        
        # Initialize Gemini API for query optimization
        # Try to get Gemini API key from .env file
        try:
            from dotenv import load_dotenv
            load_dotenv()  # Load environment variables from .env file
            self.gemini_api_key = os.environ.get('GEMINI_API_KEY')
        except ImportError:
            self.logger.warning("python-dotenv package not installed. Run 'pip install python-dotenv'")
            self.gemini_api_key = os.environ.get('GEMINI_API_KEY')  # Fallback to direct environment variable
        self.gemini_model = None
        
        if self.gemini_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.gemini_api_key)
                self.gemini_model = genai.GenerativeModel('gemini-pro')
                self.logger.info("Successfully configured Gemini API")
            except ImportError:
                self.logger.warning("Google GenerativeAI package not installed. Run 'pip install google-generativeai'")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Gemini API: {e}")
        else:
            self.logger.warning("No Gemini API key found in environment variables. Set GEMINI_API_KEY for enhanced query optimization.")
            
        # Add excluded websites for search optimization
        self.search_excluded_sites = [
            'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
            'youtube.com', 'pinterest.com', 'indiamart.com', 'amazon.com',
            'flipkart.com', 'quora.com', 'reddit.com', 'wikipedia.org',
            'justdial.com', 'sulekha.com', 'yelp.com', 'glassdoor.com',
            'indeed.com', 'naukri.com', 'monster.com', 'timesjobs.com',
            'whatsapp.com', 'telegram.org', 'reddit.com', 'tumblr.com'
        ]
        
        # Expanded list of domains that should not be scraped (for ethical considerations)
        self.excluded_domains = [
            # Marketplaces and B2B platforms
            'indiamart.com', 'm.indiamart.com', 'dir.indiamart.com',
            'tradeindia.com', 'www.tradeindia.com',
            'exportersindia.com', 'www.exportersindia.com',
            'justdial.com', 'digitalinternationalintermesh.com',
            'wholesalebox.in', 'alibaba.com', 'thomasnet.com',
            'yellowpages.com', 'sulekha.com', 'shopify.com',
            'ebay.com', 'ebay.in', 'amazon.com', 'amazon.in', 'flipkart.com',
            'myntra.com', 'snapdeal.com', 'paytmmall.com', 
            
            # Social networks and sharing sites
            'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com',
            'youtube.com', 'pinterest.com', 'tumblr.com', 'reddit.com',
            'quora.com', 'medium.com', 'blogger.com', 'blogspot.com',
            'wordpress.com', 'tiktok.com', 'whatsapp.com', 't.me',
            'telegram.org', 'telegram.me', 'flickr.com', 'imgur.com',
            'slideshare.net', 
            
            # Search engines and news sites
            'google.com', 'google.co.in', 'bing.com', 'yahoo.com',
            'duckduckgo.com', 'baidu.com', 'yandex.com', 'ask.com',
            'timesofindia.indiatimes.com', 'ndtv.com', 'news18.com',
            'hindustantimes.com', 'thehindu.com', 'indianexpress.com',
            
            # Job sites
            'naukri.com', 'monster.com', 'indeed.com', 'glassdoor.com',
            'shine.com', 'timesjobs.com', 'linkedin.com/jobs',
            
            # Web services, cloud platforms, and analytics
            'googleapis.com', 'gstatic.com', 'googleusercontent.com',
            'ggpht.com', 'doubleclick.net', 'googleadservices.com',
            'google-analytics.com', 'googlesyndication.com', 'cloudflare.com',
            'cloudfront.net', 'amazonaws.com', 'akamaihd.net', 'analytics.google.com',
            'mailchimp.com', 'freshdesk.com', 'zendesk.com', 'azure.com',
            'salesforce.com', 'hubspot.com', 'github.com', 'gitlab.com',
            'cdn.com', 'jsdelivr.net', 'jquery.com', 'w3.org',
            
            # Government and educational domains
            'gov.in', 'edu', 'nic.in', 'ac.in', 'res.in', '.edu',
            'wikipedia.org', 'wikimedia.org', 'wikibooks.org',
            
            # File sharing and document sites
            'drive.google.com', 'docs.google.com', 'sheets.google.com',
            'forms.google.com', 'calendar.google.com', 'dropbox.com',
            'onedrive.live.com', 'box.com', 'mediafire.com', 'slideshare.net',
            'scribd.com', 'docstoc.com', 'issuu.com', 'academia.edu',
            'researchgate.net',
            
            # Payment gateways and banking
            'paytm.com', 'paypal.com', 'razorpay.com', 'instamojo.com', 
            'billdesk.com', 'phonepe.com', 'gpay.app', 'sbi.co.in',
            'icicibank.com', 'hdfcbank.com', 'axisbank.com', 'pnbindia.in',
            
            # Tracking and ad networks
            'taboola.com', 'outbrain.com', 'adnxs.com', 'moatads.com',
            'criteo.com', 'scorecardresearch.com', 'adjust.com', 'appsflyer.com',
            'branch.io', 'amplitude.com', 'segment.com', 'ga.js',
            'gtag.js', 'gtm.js', 'fbpixel', 'facebook.net', 'flurry.com',
            'omniture.com', 'adroll.com', 'adform.net', 'rubiconproject.com',
            'pubmatic.com', 'casalemedia.com'
        ]
        self.logger.info(f"Configured {len(self.excluded_domains)} excluded domains for ethical scraping")
        
        # Additional checks for URL filtering
        self.tracking_param_patterns = [
            'utm_', 'gclid', 'fbclid', 'msclkid', 'dclid', 'zanpid', 
            'ref', 'referrer', 'source', 'ref_src', 'ref_url', 'cmpid',
            'pf_rd_', '_hsenc', '_hsmi', 'vero_id', 'mc_eid', 'hsa_', 
            'oly_enc_id', 'oly_anon_id', '_openstat', 'wickedid', 
            'mkt_tok', 'trk', 'igshid'
        ]
        
        # File extension patterns that should be excluded
        self.excluded_file_extensions = [
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico',
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            '.zip', '.rar', '.tar', '.gz', '.7z', '.exe', '.dll', '.apk',
            '.mp3', '.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv',
            '.css', '.js', '.xml', '.json', '.rss', '.atom'
        ]
        
        # Try to use fake_useragent for more realistic user agents
        try:
            self.ua = UserAgent()
            self.logger.info("Using fake-useragent for more realistic user agents")
        except Exception as e:
            self.logger.warning(f"Could not initialize fake-useragent: {e}. Using fallback user agents.")
            self.ua = None
        
        # Fallback user agents with Indian locale hints
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:97.0) Gecko/20100101 Firefox/97.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36 Edg/98.0.1108.56'
        ]
        
        # Cookie and session management
        self.session = requests.Session()
        self.cookies = {}
        
        # Playwright configuration
        self.use_browser = use_browser
        self.browser = None
        self.browser_context = None
        self.page = None
        self.browser_initialized = False
        self.playwright = None
        
        # Royal Residential Proxies configuration
        self.proxy_host = 'geo.iproyal.com'
        self.proxy_port = 11200
        self.proxy_username = 'vnkl9BGvMRlmvWfO'
        self.proxy_password = 'EjFoKHcjcchVYwZ9'
        
        # Configure proxies with a larger pool, focusing on Indian IPs
        self.proxy_list = []
        
        # Add primary proxy with Indian country targeting
        self.proxy_list.append({
            'http': f'http://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}',
            'https': f'http://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}'
        })
        
        # Add residential proxies with different country codes but prioritize India
        countries = ['in', 'in', 'in', 'us', 'uk', 'sg']  # Multiple 'in' entries to increase probability
        for country_code in countries:
            self.proxy_list.append({
                'http': f'http://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}',
                'https': f'http://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}'
            })
        
        # Add proxy with rotating IPs (no country specified)
        self.proxy_list.append({
            'http': f'http://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}',
            'https': f'http://{self.proxy_username}:{self.proxy_password}@{self.proxy_host}:{self.proxy_port}'
        })
        
        # Add fallback to direct connection (no proxy)
        self.proxy_list.append(None)
        
        # Track proxy performance
        self.proxy_success_count = {}  # Count successful requests per proxy
        self.proxy_failure_count = {}  # Count failed requests per proxy
        self.consecutive_failures = 0  # Track consecutive failures for current proxy
        
        # Proxy rotation settings
        self.max_consecutive_failures = 3  # After this many failures, rotate proxy
        self.rotation_counter = 0  # Count how many times we've rotated
        
        # Regex patterns specifically for Indian phone numbers and emails
        # UPDATED: More comprehensive phone patterns to match various formats
        # Including number with country code, without country code, and with separators
        # This covers formats like:
        # +91 9876543210, +91-9876543210, 09876543210, 9876543210, 98765-43210, etc.
        self.phone_pattern = re.compile(r'''
            (?:
                # Format: +91 followed by 10 digits with optional separators
                (?:\+91[\s\-.]?)?(?:[6789]\d{9})
                |
                # Format: 10 digits with optional separators in between
                (?:[6789]\d{2,4}[\s\-.]?\d{2,4}[\s\-.]?\d{2,4})
                |
                # Format: Leading 0 followed by 10 digits with optional separators
                (?:0[6789]\d{1,2}[\s\-.]?\d{3,4}[\s\-.]?\d{3,4})
                |
                # Short format: 5 digits - 5 digits for some business numbers
                (?:[6789]\d{4}[\s\-.]?\d{5})
                |
                # STD Code followed by landline (e.g., 022-12345678)
                (?:0\d{2,4}[\s\-.]?\d{6,8})
                |
                # International format with country code and STD code
                (?:\+?91[\s\-.]?\d{2,4}[\s\-.]?\d{6,8})
                |
                # 8-digit landline without STD code
                (?:[2345]\d{7})
                |
                # Toll-free numbers
                (?:1(?:800|900|860)[\s\-.]?\d{3}[\s\-.]?\d{4})
                |
                # 5-digit special numbers (short codes)
                (?:\b\d{5}\b)
            )
        ''', re.VERBOSE)
        
        # Add a secondary pattern for more phone formats
        self.phone_pattern_alt = re.compile(r'''
            (?:
                # Common patterns with brackets
                (?:\(?\+91\)?[\s\-.]?)?(?:\(?\d{2,5}\)?[\s\-.]?\d{5,8})
                |
                # General 10-digit format (with or without country code)
                (?:(?:\+\d{1,2}[\s\-.]?)?\d{10})
                |
                # Parentheses format with STD code (e.g., (022) 12345678)
                (?:\(\d{2,4}\)[\s\-.]?\d{6,8})
                |
                # Formats with periods as separators
                (?:\+?91\.[\s\-]?\d{2,4}\.[\s\-]?\d{6,8})
                |
                # Formats with parentheses for country code
                (?:\(\+?91\)[\s\-.]?\d{2,4}[\s\-.]?\d{6,8})
                |
                # International format with + but without 91 (e.g., +22 12345678) - for businesses
                (?:\+\d{2}[\s\-.]?\d{8,10})
                |
                # Format with ISD+STD code commonly used by businesses 
                (?:00[\s\-.]?91[\s\-.]?\d{2,4}[\s\-.]?\d{6,8})
            )
        ''', re.VERBOSE)
        
        # UPDATED: More comprehensive email pattern
        # Matches common email formats while avoiding common false positives
        self.email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')
        
        # Additional pattern for email extraction from obfuscated text
        self.obfuscated_email_pattern = re.compile(r'([a-zA-Z0-9._%+-]+)\s*(?:[\[\(]?\s*at\s*[\]\)]?|\[@\]|&#64;|@)\s*([a-zA-Z0-9.-]+)(?:[\[\(]?\s*(?:dot|\.)\s*[\]\)]?|\.|\s*\.)([a-zA-Z]{2,})')
        
        # Additional patterns for Indian domains and specific formats
        self.indian_domain_pattern = re.compile(r'\.in$|\.co\.in$|\.org\.in$|\.net\.in$')
        
        # Random request delay ranges
        self.min_delay = 2.0  # Minimum delay between requests in seconds
        self.max_delay = 10.0  # Maximum delay between requests in seconds
        
        # Anti-blocking measures
        self.recent_domains = set()  # Track recently accessed domains for rate limiting
        self.domain_access_times = {}  # Track access times per domain
        self.domain_min_interval = 20  # Minimum seconds between accessing same domain
        self.max_requests_per_domain = 3  # Max requests per domain in a session
        self.domain_request_count = {}  # Counter for requests per domain
        
        # If a domain blocks us, remember it
        self.blocked_domains = set()
        self.captcha_detected_domains = set()
        
        # Create directory for results if not exists
        os.makedirs('scraped_data', exist_ok=True)
        
        # Playwright lock to ensure only one browser operation at a time
        self.browser_lock = asyncio.Lock()
        
        # Debug mode flag
        self.debug_mode = debug_mode
        
        # Install required packages if missing
        self._ensure_dependencies()
        
        # Results tracking
        self.target_results = 0
        self.found_emails = set()
        self.found_phones = set()
        
        # Add excluded websites for search optimization
        self.search_excluded_sites = [
            'facebook.com', 'twitter.com', 'instagram.com', 'linkedin.com',
            'youtube.com', 'pinterest.com', 'indiamart.com', 'amazon.com',
            'flipkart.com', 'quora.com', 'reddit.com', 'wikipedia.org',
            'justdial.com', 'sulekha.com', 'yelp.com', 'glassdoor.com',
            'indeed.com', 'naukri.com', 'monster.com', 'timesjobs.com',
            'whatsapp.com', 'telegram.org', 'reddit.com', 'tumblr.com'
        ]
            
    def _ensure_dependencies(self):
        """Ensure all required dependencies are installed."""
        try:
            print("Checking dependencies...")
            
            # Check for requests package
            try:
                import requests
                print("✅ Requests library found")
            except ImportError:
                print("❌ Requests library not found, attempting to install...")
                import subprocess
                import sys
                subprocess.run([sys.executable, "-m", "pip", "install", "requests"], check=True)
                print("✅ Requests library installed")
            
            # Check for BeautifulSoup
            try:
                from bs4 import BeautifulSoup
                print("✅ BeautifulSoup library found")
            except ImportError:
                print("❌ BeautifulSoup library not found, attempting to install...")
                import subprocess
                import sys
                subprocess.run([sys.executable, "-m", "pip", "install", "beautifulsoup4"], check=True)
                print("✅ BeautifulSoup library installed")
            
            # Check for Playwright
            try:
                # First check if module is importable
                import playwright
                try:
                    version = playwright.__version__
                    print(f"✅ Playwright package found (version {version})")
                except AttributeError:
                    print("✅ Playwright package found (version not available)")
                
                # Try importing the Playwright browser launch module
                try:
                    from playwright.async_api import async_playwright
                    print("✅ Playwright async API available")
                except ImportError:
                    print("❌ Playwright async API not available, reinstalling...")
                    import subprocess
                    import sys
                    subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
                    print("✅ Playwright reinstalled")
                
                # Check if browser is installed
                import subprocess
                import sys
                
                print("Checking Playwright browser installation...")
                # Run the command to see if browsers are installed
                result = subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "--help"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    print("❌ Playwright browser installation check failed")
                    print("Installing Playwright browsers...")
                    subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
                    subprocess.run([sys.executable, "-m", "playwright", "install"], check=True)
                    print("✅ Playwright browsers installed")
                else:
                    print("✅ Playwright browser installation available")
                    
                # Install the browser if not already
                print("Installing Playwright browsers...")
                try:
                    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
                    print("✅ Chromium browser installed")
                except subprocess.CalledProcessError:
                    print("⚠️ Chromium browser installation failed, may already be installed")
                
                # Install dependencies
                print("Installing browser dependencies...")
                try:
                    subprocess.run([sys.executable, "-m", "playwright", "install-deps", "chromium"], check=True)
                    print("✅ Browser dependencies installed")
                except subprocess.CalledProcessError:
                    print("⚠️ Browser dependencies installation failed")
                
                return True
                
            except ImportError:
                print("❌ Playwright not found, attempting to install...")
                import subprocess
                import sys
                subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
                print("✅ Playwright installed")
                # Also install the browser
                try:
                    subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
                    print("✅ Chromium browser installed")
                except subprocess.CalledProcessError:
                    print("⚠️ Failed to install Chromium browser")
                    return False
                    
                # Install dependencies
                try:
                    subprocess.run([sys.executable, "-m", "playwright", "install-deps", "chromium"], check=True)
                    print("✅ Browser dependencies installed")
                except subprocess.CalledProcessError:
                    print("⚠️ Failed to install browser dependencies")
                    
                return True
            
            return True
            
        except Exception as e:
            print(f"❌ Error ensuring dependencies: {e}")
            return False
    
    def _setup_proton_vpn_connection(self):
        """Setup ProtonVPN connection for more reliable access (if available)."""
        try:
            # Check if protonvpn-cli is installed
            import subprocess
            result = subprocess.run(['which', 'protonvpn-cli'], 
                                   stdout=subprocess.PIPE, 
                                   stderr=subprocess.PIPE)
            
            if result.returncode == 0:
                print("ProtonVPN CLI found, attempting to connect...")
                # Try to connect to ProtonVPN
                try:
                    # Connect to fastest server
                    connect_result = subprocess.run(['protonvpn-cli', 'connect', '-f'], 
                                                  stdout=subprocess.PIPE, 
                                                  stderr=subprocess.PIPE,
                                                  timeout=30)
                    
                    if connect_result.returncode == 0:
                        print("✅ Connected to ProtonVPN")
                        return True
                    else:
                        print("❌ Failed to connect to ProtonVPN")
                except Exception as e:
                    print(f"Error connecting to ProtonVPN: {e}")
        except Exception:
            # ProtonVPN not available, continue without it
            pass
        
        return False
            
    async def initialize_browser(self):
        """Initialize the Playwright browser with proper configuration for all operating systems."""
        if self.browser_initialized and self.browser and self.page:
            self.logger.info("Browser already initialized")
            return True
            
        # Print detailed initialization status
        self.logger.info("Initializing browser for web scraping...")
        
        # Track initialization time
        start_time = time.time()
        
        try:
            # Initialize Playwright
            self.playwright = await async_playwright().start()
            self.logger.info("Playwright initialized successfully")
            
            # Use a country-specific proxy for better results (especially for Indian searches)
            proxy_config = None
            try:
                proxy = self.get_random_proxy()
                if proxy and 'http' in proxy:
                    # Format proxy URL properly for Playwright
                    proxy_str = proxy['http']
                    if proxy_str.startswith('http://'):
                        proxy_str = proxy_str[7:]
                    
                    # Extract username/password if present
                    username = None
                    password = None
                    if '@' in proxy_str:
                        auth, proxy_str = proxy_str.split('@', 1)
                        if ':' in auth:
                            username, password = auth.split(':', 1)
                    
                    # Configure proxy
                    proxy_config = {
                        "server": f"http://{proxy_str}",
                    }
                    
                    # Add credentials if available
                    if username and password:
                        proxy_config["username"] = username
                        proxy_config["password"] = password
                    
                    self.logger.info(f"Using proxy: {proxy_str}")
            except Exception as e:
                self.logger.warning(f"Proxy setup failed, continuing without proxy: {e}")
                proxy_config = None
            
            # Set browser parameters with minimal settings for stability and better mimicking
            browser_args = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-web-security',
                '--disable-features=BlockCredentialedSubresources'
            ]
            
            # Launch browser with improved configuration for realistic browsing
            try:
                self.logger.info("Launching browser...")
                launch_options = {
                    "headless": True,
                    "args": browser_args,
                    "timeout": 60000,  # 60 second timeout
                    "ignore_default_args": ["--enable-automation"],
                    "chromium_sandbox": False,
                    "handle_sigint": False,
                    "handle_sigterm": False,
                    "handle_sighup": False
                }
                
                # Add proxy if available
                if proxy_config:
                    launch_options["proxy"] = proxy_config
                
                # First try to launch Chromium (preferred browser)
                try:
                    self.browser = await self.playwright.chromium.launch(**launch_options)
                    self.logger.info("Chromium browser launched successfully")
                except Exception as e:
                    self.logger.warning(f"Chromium launch failed: {e}, trying Firefox")
                    # Try Firefox if Chromium fails
                    try:
                        self.browser = await self.playwright.firefox.launch(**launch_options)
                        self.logger.info("Firefox browser launched successfully")
                    except Exception as e2:
                        self.logger.warning(f"Firefox launch failed: {e2}, trying minimal configuration")
                        # Try with absolutely minimal configuration as last resort
                        self.browser = await self.playwright.chromium.launch(headless=True)
                        self.logger.info("Browser launched with minimal configuration")
            except Exception as e:
                self.logger.error(f"All browser launch attempts failed: {str(e)}")
                await self._cleanup_browser_resources()
                self.use_browser = False
                return False
            
            # Create a browser context with improved human-like settings
            try:
                self.logger.info("Creating browser context...")
                viewport_sizes = [
                    {"width": 1920, "height": 1080},
                    {"width": 1366, "height": 768},
                    {"width": 1536, "height": 864},
                    {"width": 1440, "height": 900}
                ]
                context_options = {
                    "viewport": random.choice(viewport_sizes),
                    "user_agent": self.get_random_user_agent(),
                    "locale": "en-IN",  # Use Indian locale
                    "timezone_id": "Asia/Kolkata",  # Indian timezone
                    "geolocation": {"longitude": 77.2090, "latitude": 28.6139, "accuracy": 100},  # New Delhi coordinates
                    "permissions": ["geolocation"],
                    "is_mobile": random.random() < 0.2,  # 20% chance of mobile device
                    "color_scheme": "no-preference",
                    "reduced_motion": "no-preference"
                }
                
                self.browser_context = await self.browser.new_context(**context_options)
                
                # Additional context setup to mimic a real user
                await self.browser_context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', { get: () => false });
                    Object.defineProperty(navigator, 'languages', { get: () => ['en-IN', 'en', 'hi'] });
                """)
                self.logger.info("Browser context created successfully")
            except Exception as e:
                self.logger.error(f"Failed to create browser context: {str(e)}")
                await self._cleanup_browser_resources()
                self.use_browser = False
                return False
            
            # Create a new page
            try:
                self.logger.info("Creating browser page...")
                self.page = await self.browser_context.new_page()
                
                # Set extra HTTP headers for the page that real browsers typically send
                await self.page.set_extra_http_headers({
                    "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
                    "sec-ch-ua-platform": "\"Windows\"",
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua": "\"Google Chrome\";v=\"113\", \"Chromium\";v=\"113\", \"Not-A.Brand\";v=\"24\""
                })
                
                self.logger.info("Browser page created successfully")
            except Exception as e:
                self.logger.error(f"Failed to create browser page: {str(e)}")
                await self._cleanup_browser_resources()
                self.use_browser = False
                return False
            
            # Test the browser with a simple navigation to make sure it works
            try:
                self.logger.info("Testing browser with navigation...")
                await self.page.goto("https://example.com", timeout=30000)
                await asyncio.sleep(1)  # Short pause to let the page settle
                self.logger.info("Browser test completed successfully")
            except Exception as e:
                self.logger.error(f"Browser test failed: {str(e)}")
                await self._cleanup_browser_resources()
                self.use_browser = False
                return False
            
            # Apply stealth settings to make the browser harder to detect
            await self._apply_stealth_settings()
            
            # Success - mark as initialized
            self.browser_initialized = True
            elapsed_time = time.time() - start_time
            self.logger.info(f"Browser initialized successfully in {elapsed_time:.1f} seconds")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize browser: {str(e)}")
            self.logger.error(traceback.format_exc())
            
            # Try to clean up any resources that were created
            try:
                await self._cleanup_browser_resources()
            except Exception as cleanup_error:
                self.logger.error(f"Error cleaning up browser resources: {cleanup_error}")
            
            # If we get here, browser initialization failed
            self.browser_initialized = False
            self.use_browser = False
            return False
    
    async def _cleanup_browser_resources(self):
        """Clean up browser resources safely with better error handling."""
        # Close the page
        if self.page:
            self.logger.info("Closing browser page...")
            try:
                await self.page.close()
                print("✅ Browser page closed successfully")
            except Exception as e:
                self.logger.warning(f"Error closing page: {e}")
                print(f"⚠️ Error closing browser page: {e}")
            self.page = None
        
        # Close the browser context
        if self.browser_context:
            self.logger.info("Closing browser context...")
            try:
                await self.browser_context.close()
                print("✅ Browser context closed successfully")
            except Exception as e:
                self.logger.warning(f"Error closing browser context: {e}")
                print(f"⚠️ Error closing browser context: {e}")
            self.browser_context = None
        
        # Close the browser
        if self.browser:
            self.logger.info("Closing browser...")
            try:
                await self.browser.close()
                print("✅ Browser closed successfully")
            except Exception as e:
                self.logger.warning(f"Error closing browser: {e}")
                print(f"⚠️ Error closing browser: {e}")
            self.browser = None
        
        # Stop playwright
        if self.playwright:
            self.logger.info("Stopping playwright...")
            try:
                await self.playwright.stop()
                print("✅ Playwright stopped successfully")
            except Exception as e:
                self.logger.warning(f"Error stopping playwright: {e}")
                print(f"⚠️ Error stopping playwright: {e}")
            self.playwright = None
        
        # Set initialization flag to false
        self.browser_initialized = False
        self.logger.info("Browser resources cleanup completed")
    
    async def _apply_stealth_settings(self, page=None):
        """Apply advanced stealth settings to avoid detection and prevent captchas."""
        if page is None:
            page = self.page
            
        try:
            # Set viewport to a common resolution with randomization
            common_resolutions = [
                {"width": 1920, "height": 1080},
                {"width": 1366, "height": 768},
                {"width": 1536, "height": 864},
                {"width": 1440, "height": 900},
                {"width": 1280, "height": 720}
            ]
            await page.set_viewport_size(random.choice(common_resolutions))
            
            # Override navigator properties with more sophisticated approach
            await page.add_init_script("""
                // Advanced fingerprint protection
                (() => {
                    // Override webdriver property
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    });
                    
                    // Create fake plugins array with realistic entries
                    const makePluginsArray = () => {
                        const plugins = [
                            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: 'Portable Document Format' },
                            { name: 'Native Client', filename: 'internal-nacl-plugin', description: 'Native Client Executable' },
                            { name: 'Widevine Content Decryption Module', filename: 'widevinecdmadapter.dll', description: 'Enables Widevine licenses for playback of HTML audio/video content.' }
                        ];
                        
                        // Create a plugins-like object
                        const pluginsArray = Object.create(Object.getPrototypeOf(navigator.plugins));
                        plugins.forEach((plugin, i) => {
                            const pluginObj = {
                                name: plugin.name,
                                description: plugin.description,
                                filename: plugin.filename,
                                length: 1
                            };
                            Object.setPrototypeOf(pluginObj, Plugin.prototype);
                            pluginsArray[i] = pluginObj;
                            pluginsArray[plugin.name] = pluginObj;
                        });
                        
                        pluginsArray.length = plugins.length;
                        return pluginsArray;
                    };
                    
                    // Replace navigator plugins and mimeTypes
                    const pluginsArray = makePluginsArray();
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => pluginsArray
                    });
                    
                    // Randomize hardware concurrency to a realistic value
                    const originalHardwareConcurrency = navigator.hardwareConcurrency || 4;
                    Object.defineProperty(navigator, 'hardwareConcurrency', {
                        get: () => Math.min(originalHardwareConcurrency, 8)
                    });
                    
                    // Fix inconsistencies in WebGL reporting
                    const getParameter = WebGLRenderingContext.prototype.getParameter;
                    WebGLRenderingContext.prototype.getParameter = function(parameter) {
                        // UNMASKED_VENDOR_WEBGL and UNMASKED_RENDERER_WEBGL
                        if (parameter === 37445) {
                            return 'Intel Inc.';
                        }
                        if (parameter === 37446) {
                            return 'Intel Iris OpenGL Engine';
                        }
                        return getParameter.apply(this, arguments);
                    };
                    
                    // Override platform with consistent value
                    Object.defineProperty(navigator, 'platform', {
                        get: () => 'Win32'
                    });
                    
                    // Add touch support conditionally (for mobile emulation)
                    if (Math.random() > 0.7) { // 30% chance of having touch support
                        Object.defineProperty(navigator, 'maxTouchPoints', {
                            get: () => 5
                        });
                    }
                    
                    // Override product and productSub
                    Object.defineProperty(navigator, 'product', {
                        get: () => 'Gecko'
                    });
                    Object.defineProperty(navigator, 'productSub', {
                        get: () => '20030107'
                    });
                    
                    // Override permission behavior
                    const originalQuery = navigator.permissions.query;
                    navigator.permissions.query = function(parameters) {
                        if (parameters.name === 'notifications' || 
                            parameters.name === 'push' || 
                            parameters.name === 'midi' ||
                            parameters.name === 'camera' || 
                            parameters.name === 'microphone' || 
                            parameters.name === 'geolocation' ||
                            parameters.name === 'clipboard-read' ||
                            parameters.name === 'clipboard-write') {
                            return Promise.resolve({state: 'prompt', onchange: null});
                        }
                        return originalQuery.apply(this, arguments);
                    };
                    
                    // Spoof consistent deviceMemory
                    Object.defineProperty(navigator, 'deviceMemory', {
                        get: () => 8
                    });
                    
                    // Override language settings to match headers
                    Object.defineProperty(navigator, 'language', {
                        get: () => 'en-US'
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en']
                    });

                    // Block intensive fingerprinting scripts
                    // Chrome evaluates scripts even in string assignments
                    window.chrome = {
                        app: {
                            isInstalled: false,
                            InstallState: {
                                DISABLED: 'disabled',
                                INSTALLED: 'installed',
                                NOT_INSTALLED: 'not_installed'
                            },
                            RunningState: {
                                CANNOT_RUN: 'cannot_run',
                                READY_TO_RUN: 'ready_to_run',
                                RUNNING: 'running'
                            }
                        },
                        runtime: {
                            OnInstalledReason: {
                                INSTALL: 'install',
                                UPDATE: 'update',
                                CHROME_UPDATE: 'chrome_update',
                                SHARED_MODULE_UPDATE: 'shared_module_update'
                            },
                            OnRestartRequiredReason: {
                                APP_UPDATE: 'app_update',
                                OS_UPDATE: 'os_update',
                                PERIODIC: 'periodic'
                            },
                            PlatformArch: {
                                ARM: 'arm',
                                X86_32: 'x86-32',
                                X86_64: 'x86-64'
                            },
                            PlatformNaclArch: {
                                ARM: 'arm',
                                X86_32: 'x86-32',
                                X86_64: 'x86-64'
                            },
                            PlatformOs: {
                                MAC: 'mac',
                                WIN: 'win',
                                ANDROID: 'android',
                                CROS: 'cros',
                                LINUX: 'linux',
                                OPENBSD: 'openbsd'
                            },
                            RequestUpdateCheckStatus: {
                                THROTTLED: 'throttled',
                                NO_UPDATE: 'no_update',
                                UPDATE_AVAILABLE: 'update_available'
                            }
                        }
                    };

                    // Add browser-specific details
                    // Spoof connection information
                    if ('connection' in navigator) {
                        Object.defineProperties(navigator.connection, {
                            rtt: {
                                get: () => 50 + Math.floor(Math.random() * 40)
                            },
                            downlink: {
                                get: () => 5 + Math.floor(Math.random() * 10)
                            },
                            effectiveType: {
                                get: () => ['4g', '3g'][Math.floor(Math.random() * 2)]
                            },
                            saveData: {
                                get: () => false
                            }
                        });
                    }

                    // Modify performance timing to appear realistic
                    if ('performance' in window && 'timing' in window.performance) {
                        // Ensure timing is realistic - add variability
                        const timingVariability = 5 + Math.floor(Math.random() * 30);
                        const originalGetEntriesByType = window.performance.getEntriesByType;
                        window.performance.getEntriesByType = function(type) {
                            const entries = originalGetEntriesByType.apply(this, arguments);
                            if (type === 'navigation' && entries.length) {
                                entries.forEach(entry => {
                                    // Add random variations to timing measurements
                                    entry.connectEnd += timingVariability;
                                    entry.connectStart += timingVariability;
                                    entry.domComplete += timingVariability;
                                    entry.domContentLoadedEventEnd += timingVariability;
                                    entry.domContentLoadedEventStart += timingVariability;
                                    entry.domInteractive += timingVariability;
                                    entry.loadEventEnd += timingVariability;
                                    entry.loadEventStart += timingVariability;
                                    entry.requestStart += timingVariability;
                                    entry.responseEnd += timingVariability;
                                    entry.responseStart += timingVariability;
                                });
                            }
                            return entries;
                        };
                    }
                })();
            """)
            
            # Handle common anti-bot protections by Google
            await page.add_init_script("""
                // Disable common bot detection libraries that Google uses
                (() => {
                    // Hide that we're using automation
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise;
                    delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
                    
                    // Mask common bot detection checks
                    const originalQuerySelector = document.querySelector;
                    document.querySelector = function(...args) {
                        // Block queries for known bot detection elements
                        if (args[0] && typeof args[0] === 'string' && 
                            (args[0].includes('recaptcha') || 
                            args[0].includes('g-recaptcha') || 
                            args[0].includes('iframe[src*=recaptcha]'))) {
                            // Return null for first few calls to avoid suspicion
                            // but allow real recaptcha to load if needed
                            if (Math.random() < 0.7) {
                                return null;
                            }
                        }
                        return originalQuerySelector.apply(document, args);
                    };
                    
                    // Override some navigator properties for Google specifically
                    if (window.location.hostname.includes('google')) {
                        // Use realistic values for Google
                        Object.defineProperty(navigator, 'userAgent', {
                            get: () => 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36'
                        });
                        
                        // Override specific Google checks
                        window.navigator.mediaDevices = {
                            enumerateDevices: () => Promise.resolve([
                                {
                                    deviceId: 'default',
                                    kind: 'audioinput',
                                    label: '',
                                    groupId: ''
                                },
                                {
                                    deviceId: 'default',
                                    kind: 'audiooutput',
                                    label: '',
                                    groupId: ''
                                }
                            ])
                        };
                    }
                })();
            """)
            
            # Set user agent with improved consistency
            user_agent = self.get_random_user_agent()
            
            # Add random minor variations to user agent to avoid fingerprinting
            parts = user_agent.split(' ')
            if len(parts) > 3:
                # Small chance to modify minor version numbers only
                if random.random() < 0.3:
                    for i in range(len(parts)):
                        if '/' in parts[i] and '.' in parts[i]:
                            base, versions = parts[i].split('/')
                            if '.' in versions:
                                major, minor = versions.split('.')
                                # Only modify minor version
                                parts[i] = f"{base}/{major}.{int(minor) + random.randint(-2, 2)}"
                
                user_agent = ' '.join(parts)
            
            # Set headers that better mimic real browsers
            await page.set_extra_http_headers({
                'User-Agent': user_agent,
                'Accept-Language': 'en-US,en;q=0.9,hi;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'DNT': '1',
                'Sec-CH-UA': '"Google Chrome";v="113", "Chromium";v="113", "Not-A.Brand";v="24"',
                'Sec-CH-UA-Mobile': '?0',
                'Sec-CH-UA-Platform': '"Windows"',
                # Add random cache-control header to make it more realistic
                'Cache-Control': random.choice(['max-age=0', 'no-cache', 'max-age=0, private']),
                # Add a random referer sometimes
                'Referer': random.choice([
                    'https://www.google.com/',
                    'https://www.bing.com/', 
                    'https://search.yahoo.com/',
                    ''
                ]) if random.random() < 0.7 else ''
            })
            
            # Set extra delays between actions to mimic human behavior
            await page.keyboard.set_action_delay(50 + random.randint(10, 100))
            await page.mouse.set_action_delay(50 + random.randint(10, 100))
            
            # Improved human-like behavior simulation
            await self._simulate_human_browsing(page)
            
            # Set cookies to appear like a returning visitor
            await self._set_natural_cookies(page)
            
            # Disable automation-specific features
            await page.context.clear_permissions()
            
            # Configure geolocation for India (random cities)
            indian_locations = [
                {"longitude": 77.2090, "latitude": 28.6139},  # Delhi
                {"longitude": 72.8777, "latitude": 19.0760},  # Mumbai
                {"longitude": 77.5946, "latitude": 12.9716},  # Bangalore
                {"longitude": 80.2707, "latitude": 13.0827},  # Chennai
                {"longitude": 78.4867, "latitude": 17.3850},  # Hyderabad
            ]
            
            location = random.choice(indian_locations)
            await page.context.grant_permissions(['geolocation'])
            await page.context.set_geolocation(location)
            
            return True
        except Exception as e:
            self.logger.error(f"Error applying stealth settings: {e}")
            return False
            
    async def _set_natural_cookies(self, page):
        """Set cookies that make the browser appear as a returning visitor."""
        try:
            # Only set cookies for certain domains to avoid suspicion
            current_url = page.url
            domain = urlparse(current_url).netloc
            
            if not domain or domain == 'about:blank':
                return
                
            # Set common cookies that regular users would have
            common_cookies = [
                {
                    "name": "preference_cookie",
                    "value": "accepted",
                    "domain": domain,
                    "path": "/"
                },
                {
                    "name": "returning_visitor",
                    "value": "true",
                    "domain": domain,
                    "path": "/"
                },
                {
                    "name": "session_depth",
                    "value": str(random.randint(2, 10)),
                    "domain": domain,
                    "path": "/"
                }
            ]
            
            # For Google specifically, set cookies that prevent bot detection
            if 'google' in domain:
                google_cookies = [
                    {
                        "name": "NID",
                        "value": ''.join(random.choices('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_', k=160)),
                        "domain": ".google.com",
                        "path": "/"
                    },
                    {
                        "name": "1P_JAR",
                        "value": datetime.now().strftime("%Y-%m-%d"),
                        "domain": ".google.com",
                        "path": "/"
                    },
                    {
                        "name": "CONSENT",
                        "value": f"YES+IN.{random.randint(100000000, 999999999)}",
                        "domain": ".google.com",
                        "path": "/"
                    },
                    {
                        "name": "SEARCH_SAMESITE",
                        "value": "CgQI_ZcB",
                        "domain": ".google.com",
                        "path": "/"
                    }
                ]
                common_cookies.extend(google_cookies)
                
            # Set the cookies
            for cookie in common_cookies:
                try:
                    await page.context.add_cookies([cookie])
                except Exception:
                    # Skip if cookie couldn't be set
                    pass
                    
        except Exception as e:
            self.logger.debug(f"Error setting natural cookies: {e}")
            # Non-critical error, continue execution
            
    async def _simulate_human_browsing(self, page=None):
        """Simulate realistic human browsing behavior with improved randomization."""
        if page is None:
            page = self.page
            
        if not page:
            return
            
        try:
            # Get viewport dimensions
            viewport = await page.evaluate("""
                () => ({
                    width: window.innerWidth,
                    height: window.innerHeight
                })
            """)
            
            width = viewport.get('width', 1366)
            height = viewport.get('height', 768)
            
            # More realistic mouse movements: curved paths instead of straight lines
            points = []
            num_points = random.randint(3, 7)  # Fewer points for faster execution
            
            # Generate random bezier curve points
            start_x, start_y = random.randint(0, width), random.randint(0, height)
            points.append((start_x, start_y))
            
            for _ in range(num_points):
                # Create more natural curve by limiting movement distance
                max_distance = 300  # Maximum pixels to move at once
                delta_x = random.randint(-max_distance, max_distance)
                delta_y = random.randint(-max_distance, max_distance)
                
                # Ensure we stay within viewport
                next_x = max(0, min(width, points[-1][0] + delta_x))
                next_y = max(0, min(height, points[-1][1] + delta_y))
                points.append((next_x, next_y))
            
            # Move mouse along the curved path with variable speed
            await page.mouse.move(points[0][0], points[0][1])
            for x, y in points[1:]:
                # Randomize speed for more human-like movement
                steps = random.randint(2, 5)  # Fewer steps for faster execution
                await page.mouse.move(x, y, steps=steps)
                await asyncio.sleep(random.uniform(0.02, 0.1))  # Shorter delays
                
            # Random scrolling behavior that's faster but still human-like
            scroll_count = random.randint(2, 4)
            for i in range(scroll_count):
                # Random scroll amount
                scroll_amount = random.randint(300, 800) if i < scroll_count-1 else random.randint(800, 1500)
                
                # Apply scroll with natural acceleration
                steps = random.randint(3, 5)
                for step in range(1, steps + 1):
                    # Accelerating scroll
                    scroll_progress = step / steps
                    # Ease-out function: cubic y = 1-(1-x)^3
                    eased_progress = 1 - (1 - scroll_progress) ** 3
                    step_amount = int(scroll_amount * eased_progress)
                    await page.evaluate(f"window.scrollTo(0, {step_amount})")
                    await asyncio.sleep(random.uniform(0.03, 0.08))
                
                # Random pause between scrolls (shorter for efficiency)
                await asyncio.sleep(random.uniform(0.3, 0.7))
                
                # Maybe move the mouse a bit while scrolling (more realistic)
                if random.random() < 0.3:  # 30% chance
                    mouse_x = random.randint(0, width)
                    mouse_y = random.randint(100, height-100)
                    await page.mouse.move(mouse_x, mouse_y, steps=2)
            
            # Simulate reading behavior - find text and hover over it
            if random.random() < 0.5:  # 50% chance
                await self._simulate_reading(page)
                
            # Find important content and possibly interact with it
            if random.random() < 0.2:  # 20% chance - keep low to avoid accidental clicks
                await self._maybe_interact_with_content(page)
                
        except Exception as e:
            self.logger.error(f"Error simulating human browsing: {e}", exc_info=True)
            
    async def _simulate_reading(self, page):
        """Simulate a user reading content on the page."""
        try:
            # Find paragraphs or text blocks
            text_elements = await page.evaluate("""
                () => {
                    const paragraphs = Array.from(document.querySelectorAll('p, h1, h2, h3, .content, article'));
                    return paragraphs
                        .filter(el => {
                            // Only consider visible elements with actual text
                            const rect = el.getBoundingClientRect();
                            return rect.top >= 0 && rect.top < window.innerHeight &&
                                   rect.width > 50 && rect.height > 10 &&
                                   el.textContent.trim().length > 20;
                        })
                        .map(el => {
                            const rect = el.getBoundingClientRect();
                            return {
                                x: rect.left + rect.width / 2,
                                y: rect.top + rect.height / 2,
                                height: rect.height,
                                width: rect.width,
                                text: el.textContent.trim().substring(0, 30)
                            };
                        })
                        .slice(0, 3); // Limit to 3 paragraphs
                }
            """)
            
            if not text_elements or len(text_elements) == 0:
                return
                
            for element in text_elements:
                # Move to the text element
                await page.mouse.move(
                    element['x'] + random.randint(-10, 10), 
                    element['y'] + random.randint(-5, 5),
                    steps=3
                )
                
                # Pause as if reading
                reading_time = random.uniform(0.5, 1.5)  # 0.5 to 1.5 seconds per text block
                await asyncio.sleep(reading_time)
                
                # Occasionally scroll a bit more
                if random.random() < 0.3:
                    await page.mouse.wheel(0, random.randint(50, 150))
                    await asyncio.sleep(0.3)
                    
        except Exception as e:
            self.logger.debug(f"Error simulating reading: {e}")
            # Non-critical, continue execution

    async def _detect_captcha_in_browser(self, page=None):
        """Enhanced CAPTCHA detection in browser context."""
        if page is None:
            page = self.page
            
        try:
            # Common CAPTCHA indicators
            captcha_indicators = [
                "captcha",
                "recaptcha",
                "challenge",
                "verify you are human",
                "robot check",
                "security check",
                "prove you're not a robot",
                "automated access",
                "unusual traffic"
            ]
            
            # Check page content
            content = await page.content()
            content_lower = content.lower()
            
            # Check for CAPTCHA elements
            captcha_elements = await page.query_selector_all(
                "iframe[src*='recaptcha'], div[class*='captcha'], div[id*='captcha'], " +
                "form[action*='captcha'], input[name*='captcha'], img[src*='captcha']"
            )
            
            if captcha_elements:
                self.logger.warning("CAPTCHA elements detected on page")
                return True
                
            # Check for CAPTCHA text
            for indicator in captcha_indicators:
                if indicator in content_lower:
                    self.logger.warning(f"CAPTCHA indicator found: {indicator}")
                    return True
                    
            # Check for common CAPTCHA images
            captcha_images = await page.query_selector_all(
                "img[src*='captcha'], img[alt*='captcha'], img[title*='captcha']"
            )
            
            if captcha_images:
                self.logger.warning("CAPTCHA images detected")
                return True
                
            # Check for common CAPTCHA forms
            captcha_forms = await page.query_selector_all(
                "form[action*='captcha'], form[id*='captcha'], form[class*='captcha']"
            )
            
            if captcha_forms:
                self.logger.warning("CAPTCHA forms detected")
                return True
                
            return False
            
        except Exception as e:
            self.logger.error(f"Error detecting CAPTCHA: {e}")
            return False
            
    async def _ensure_lazy_content_loaded(self):
        """Ensure lazy-loaded content appears by scrolling and waiting more thoroughly."""
        if not self.page:
            return
            
        try:
            # Get page height with more reliable method
            page_height = await self.page.evaluate("""
                () => Math.max(
                    document.body ? document.body.scrollHeight : 0,
                    document.documentElement ? document.documentElement.scrollHeight : 0,
                    document.body ? document.body.offsetHeight : 0,
                    document.documentElement ? document.documentElement.offsetHeight : 0
                )
            """)
            
            # Return early if page is very short
            if page_height < 1000:
                return
                
            # Scroll down in steps to trigger lazy loading
            viewport_height = await self.page.evaluate("window.innerHeight")
            scroll_steps = min(5, max(3, page_height // viewport_height))
            
            for i in range(1, scroll_steps + 1):
                # Scroll to position with easing
                position = (page_height * i) // (scroll_steps + 1)
                
                # Use smoother scrolling with multiple small steps
                current_position = await self.page.evaluate("window.scrollY")
                steps = 10
                for step in range(1, steps + 1):
                    target = current_position + (position - current_position) * (step / steps)
                    await self.page.evaluate(f"window.scrollTo(0, {target})")
                    await asyncio.sleep(0.05)
                
                # Wait longer for content to load
                await asyncio.sleep(0.8)
                
                # Check for AJAX spinners or loading indicators
                has_loading_indicator = await self.page.evaluate("""
                    () => {
                        const loaders = document.querySelectorAll(
                            '.loading, .spinner, .loader, [class*="loading"], [class*="spinner"], 
                            [class*="loader"], [aria-busy="true"], [class*="progress"], 
                            img[src*="loading"], img[src*="spinner"], iframe[loading="lazy"]'
                        );
                        return loaders.length > 0;
                    }
                """)
                
                if has_loading_indicator:
                    # Wait longer for AJAX content to load
                    self.logger.info("Loading indicators detected, waiting for content...")
                    await asyncio.sleep(2)
                    
                # Look for tabbed content and click each tab to ensure all content is loaded
                await self._activate_tabbed_content()
                
                # Look for "show more" or "expand" buttons and click them
                await self._click_expansion_elements()
            
            # Scroll back to top slowly
            await self.page.evaluate("""
                (duration) => {
                    const start = window.scrollY;
                    const startTime = Date.now();
                    function scroll() {
                        const now = Date.now();
                        const time = Math.min(1, (now - startTime) / duration);
                        // Ease-out function: cubic y = 1-(1-x)^3
                        const ease = 1 - Math.pow(1 - time, 3);
                        window.scrollTo(0, start * (1 - ease));
                        if (time < 1) requestAnimationFrame(scroll);
                    }
                    scroll();
                }
            """, 500)  # 500ms duration
            
            await asyncio.sleep(0.5)
            
        except Exception as e:
            self.logger.warning(f"Error ensuring lazy content loaded: {e}")
            
    async def _activate_tabbed_content(self):
        """Click on tabs to ensure all tabbed content is loaded."""
        try:
            # Find common tab elements
            tab_elements = await self.page.evaluate("""
                () => {
                    // Common tab selectors
                    const tabSelectors = [
                        '.tab', '.tabs li', '.nav-tab', '.nav-tabs li', '.nav-item', '.tab-title',
                        '[role="tab"]', '[data-tab]', '.tablink', '.tab-trigger', 
                        '.accordion-header', '.accordion-button', '.collapse-header'
                    ];
                    
                    // Find all tab elements
                    let tabs = [];
                    for (const selector of tabSelectors) {
                        const elements = document.querySelectorAll(selector);
                        for (const el of elements) {
                            // Skip if not visible or already selected/active
                            if (el.offsetParent === null) continue;
                            if (el.classList.contains('active') || 
                                el.classList.contains('selected') ||
                                el.getAttribute('aria-selected') === 'true') continue;
                                
                            // Get position for clicking
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 10 && rect.height > 10 && 
                                rect.top >= 0 && rect.left >= 0 && 
                                rect.bottom <= window.innerHeight && 
                                rect.right <= window.innerWidth) {
                                tabs.push({
                                    x: rect.left + rect.width / 2,
                                    y: rect.top + rect.height / 2,
                                    text: el.textContent.trim().substring(0, 30)
                                });
                            }
                        }
                    }
                    return tabs.slice(0, 5); // Limit to 5 tabs max
                }
            """)
            
            # Click on each tab with delay between
            for tab in tab_elements:
                self.logger.debug(f"Clicking tab: {tab.get('text', 'unnamed')}")
                await self.page.mouse.move(tab['x'], tab['y'], steps=2)
                await asyncio.sleep(0.2)
                await self.page.mouse.click(tab['x'], tab['y'])
                await asyncio.sleep(1)  # Wait for tab content to load
                
        except Exception as e:
            self.logger.debug(f"Error activating tabbed content: {e}")
            
    async def _click_expansion_elements(self):
        """Find and click 'show more', 'expand', etc. buttons."""
        try:
            expansion_elements = await self.page.evaluate("""
                () => {
                    // Texts that suggest expandable content
                    const expandTexts = [
                        'show more', 'read more', 'view more', 'load more', 'expand',
                        'see more', 'show all', 'view all', 'see all', '+', 'more'
                    ];
                    
                    // Find elements containing these texts that are likely buttons
                    const elements = [];
                    const allElements = document.querySelectorAll(
                        'button, a, div[role="button"], span[role="button"], [class*="more"], ' + 
                        '[class*="expand"], [class*="collapse"], [aria-expanded="false"]'
                    );
                    
                    for (const el of allElements) {
                        // Skip if not visible
                        if (el.offsetParent === null) continue;
                        
                        // Get text content
                        const text = el.textContent.trim().toLowerCase();
                        
                        // Check if it contains any expand texts
                        if (expandTexts.some(t => text.includes(t))) {
                            const rect = el.getBoundingClientRect();
                            // Ensure element is visible and has reasonable size
                            if (rect.width > 10 && rect.height > 10 && 
                                rect.top >= 0 && rect.left >= 0 && 
                                rect.bottom <= window.innerHeight && 
                                rect.right <= window.innerWidth) {
                                elements.push({
                                    x: rect.left + rect.width / 2,
                                    y: rect.top + rect.height / 2,
                                    text: text.substring(0, 30)
                                });
                            }
                        }
                    }
                    return elements.slice(0, 3); // Limit to 3 max
                }
            """)
            
            # Click on each expansion element
            for element in expansion_elements:
                self.logger.debug(f"Clicking expansion element: {element.get('text', 'unnamed')}")
                await self.page.mouse.move(element['x'], element['y'], steps=2)
                await asyncio.sleep(0.2)
                await self.page.mouse.click(element['x'], element['y'])
                await asyncio.sleep(1.5)  # Wait for expanded content to load
                
        except Exception as e:
            self.logger.debug(f"Error clicking expansion elements: {e}")
            
    async def browser_get_page(self, url, max_retries=2):
        """Use Playwright browser automation to get a page with improved reliability."""
        # Ensure browser is initialized
        browser_ready = await self.initialize_browser()
        if not browser_ready:
            self.logger.warning("Browser not available. Falling back to requests.")
            return None
            
        domain = urlparse(url).netloc
        
        # Check for rate limiting on domain
        self._check_domain_rate_limit(domain)
        
        # Track this request
        self._track_domain_access(domain)
        
        retries = 0
        while retries < max_retries:
            try:
                self.logger.info(f"Browser requesting URL: {url}")
                
                async with self.browser_lock:
                    # Enhanced navigation with progressive wait strategy
                    try:
                        # First attempt with shorter timeout and minimal wait
                        response = await self.page.goto(
                            url, 
                            wait_until="domcontentloaded", 
                            timeout=15000
                        )
                        
                        if not response:
                            self.logger.warning(f"No response object from navigation to {url}")
                            # Wait a moment for page to settle
                            await asyncio.sleep(1)
                        elif response.status >= 400:
                            self.logger.warning(f"HTTP error {response.status} when loading {url}")
                            if response.status == 404:
                                # No need to retry for 404
                                return None
                        
                        # Wait for network to become idle - catches AJAX content
                        try:
                            await self.page.wait_for_load_state('networkidle', timeout=5000)
                            self.logger.info("Network became idle")
                        except PlaywrightTimeoutError:
                            # Continue even if networkidle times out - page might still be usable
                            self.logger.info("Network idle timeout, but continuing")
                            
                        # Wait for essential elements to appear if needed
                        essential_selectors = ['body', 'header', 'footer', 'main', '.content', '#content', '[role="main"]']
                        for selector in essential_selectors:
                            try:
                                # Try to find at least one important page element with short timeout
                                await self.page.wait_for_selector(selector, timeout=1000)
                                self.logger.debug(f"Found essential element: {selector}")
                                break  # Found one essential element, no need to check more
                            except PlaywrightTimeoutError:
                                continue  # Try next selector
                        
                        # Check if page loaded properly
                        page_content = await self.page.content()
                        content_length = len(page_content)
                        
                        self.logger.info(f"Initial page content length: {content_length}")
                        
                        if content_length < 100:  # Very short content might indicate a problem
                            self.logger.warning(f"Very short content ({content_length} bytes) received from {url}")
                            # Print the content for debugging
                            self.logger.debug(f"Full content: {page_content}")
                            retries += 1
                            if retries < max_retries:
                                # Wait a bit and try again
                                await asyncio.sleep(random.uniform(2, 4))
                                continue
                        
                        # Check for CAPTCHA presence with enhanced detection
                        if await self._detect_captcha_in_browser():
                            self.logger.warning(f"CAPTCHA detected on {domain}. Adding to blocked domains.")
                            self.captcha_detected_domains.add(domain)
                            retries += 1
                            
                            # Try CAPTCHA mitigation strategies
                            if retries < max_retries:
                                self.logger.info("Trying to bypass with CAPTCHA mitigation strategy...")
                                # Simulate scrolling to appear more human-like
                                await self._simulate_human_browsing()
                                # Wait longer to see if CAPTCHA clears or page loads alternate content
                                await asyncio.sleep(random.uniform(5, 10))
                                await self.page.reload(wait_until="domcontentloaded", timeout=30000)
                                # Try waiting for network idle after reload
                                try:
                                    await self.page.wait_for_load_state('networkidle', timeout=5000)
                                except PlaywrightTimeoutError:
                                    pass
                                continue
                        
                        # Check if content loaded properly (more efficient check)
                        page_content = await self.page.content()
                        if len(page_content) > 300:  # Smaller min size for valid page
                            # Extract cookies from the browser and save them to our session
                            browser_cookies = await self.browser_context.cookies()
                            for cookie in browser_cookies:
                                self.cookies[cookie['name']] = cookie['value']
                            
                            # Ensure all dynamic content is loaded
                            await self._ensure_lazy_content_loaded()
                            
                            # Get the final page content after all processing
                            final_content = await self.page.content()
                            
                            self.logger.info(f"Successfully retrieved content for {url}, length: {len(final_content)}")
                            
                            # Record successful access for this domain
                            proxy_id = '0'  # Default proxy ID
                            self.proxy_success_count[proxy_id] = self.proxy_success_count.get(proxy_id, 0) + 1
                            self.consecutive_failures = 0  # Reset failure counter
                            
                            return final_content
                        else:
                            self.logger.warning(f"Page content too short ({len(page_content)} bytes) for {url}")
                            retries += 1
                    except PlaywrightTimeoutError:
                        self.logger.warning(f"Timeout loading {url}. Retrying...")
                        retries += 1
                        continue
            
            except PlaywrightTimeoutError:
                self.logger.warning(f"Timeout loading {url}. Retrying...")
                retries += 1
                await asyncio.sleep(random.uniform(1, 3))
                
            except Exception as e:
                self.logger.error(f"Browser error for {url}: {e}")
                retries += 1
                
                # If it's a fatal error, try reinitializing the browser
                if "context already closed" in str(e) or "browser closed" in str(e):
                    self.browser_initialized = False
                    browser_ready = await self.initialize_browser()
                    if not browser_ready:
                        break
                await asyncio.sleep(random.uniform(1, 3))
        
        # All retries failed - record the failure
        proxy_id = '0'  # Default proxy ID
        self.proxy_failure_count[proxy_id] = self.proxy_failure_count.get(proxy_id, 0) + 1
        self.consecutive_failures += 1
        
        # Report detailed failure
        self.logger.warning(f"Failed to get content from {url} after {max_retries} attempts")
        return None
    
    def _clean_search_query(self, query: str) -> str:
        """Clean and format a search query for better results"""
        # Ensure proper quote matching
        quote_count = query.count('"')
        if quote_count % 2 != 0:
            # Unmatched quotes - fix by removing trailing quote or adding one
            if query.endswith('"'):
                query = query[:-1]
            else:
                query += '"'
                
        # Remove any stray operators at the beginning or end
        query = re.sub(r'^[\s\(\)\[\]]+', '', query)
        query = re.sub(r'[\s\(\)\[\]]+$', '', query)
        
        # Clean up spaces around operators
        query = re.sub(r'\s+OR\s+', ' OR ', query)
        query = re.sub(r'\s+AND\s+', ' AND ', query)
        query = re.sub(r'\s*\|\s*', ' | ', query)
        
        # Ensure proper spacing around site: operators
        query = re.sub(r'site:\s*', 'site:', query)
        query = re.sub(r'-site:\s*', '-site:', query)
        
        return query
    
    def _fallback_optimize_query(self, keyword: str) -> str:
        """
        Manual fallback method to optimize search queries when Gemini API is unavailable.
        This version creates simpler queries less likely to trigger security checks.
        
        Args:
            keyword (str): The original search keyword
            
        Returns:
            str: Manually optimized search query
        """
        # Limit exclusions to just the top 5 most important sites to avoid complex queries
        top_exclusions = self.search_excluded_sites[:5]
        exclusion_string = ' '.join([f'-site:{site}' for site in top_exclusions])
        
        # Check if keyword appears to be a company or business name
        if ' ' in keyword or keyword[0].isupper() or len(keyword.split()) > 1:
            # Create a simpler query with fewer operators
            optimized_query = f'"{keyword}" contact email phone'
            
            # Add site:.in for Indian-specific searches to get more relevant results
            if self.is_indian_domain(keyword) or 'india' in keyword.lower() or 'delhi' in keyword.lower() or 'mumbai' in keyword.lower():
                optimized_query += ' site:.in'
        else:
            # More generic keyword - use broader matching but keep it simple
            optimized_query = f'"{keyword}" business contact'
            
        # Add a few exclusions, but not too many
        optimized_query += f" {exclusion_string}"
        
        # Avoid using too many operators like filetype: which can trigger security checks
        # Only add if the keyword is very generic to help filter
        if len(keyword.split()) <= 2 and random.random() < 0.2:  # Reduced chance (20%)
            optimized_query += ' filetype:html'
            
        self.logger.info(f"Fallback optimized query (security-check-friendly): {optimized_query}")
        return optimized_query
        
    def search_with_multiple_strategies(self, keyword: str, num_results: int = 10) -> List[str]:
        """
        Perform search with multiple optimization strategies for more comprehensive results.
        
        Args:
            keyword (str): The original search keyword
            num_results (int): Number of results to return per strategy
            
        Returns:
            List[str]: Combined list of unique URLs from all strategies
        """
        all_urls = set()
        strategies = ["contact_info", "email_focus", "phone_focus"]
        
        for strategy in strategies:
            # Optimize query for this specific strategy
            optimized_query = self.optimize_search_query_with_gemini(keyword, strategy)
            
            # Log the strategy and query
            self.logger.info(f"Searching with strategy '{strategy}': {optimized_query}")
            print(f"🔍 Searching with {strategy} strategy: {optimized_query}")
            
            # Perform the search
            urls = self.search_google(optimized_query, num_results=num_results)
            
            if urls:
                # Log success and add to our set
                strategy_urls = set(urls)
                self.logger.info(f"Strategy '{strategy}' found {len(strategy_urls)} URLs")
                all_urls.update(strategy_urls)
            
            # Respect rate limits between searches
            time.sleep(random.uniform(5, 10))
        
        # Return the combined unique URLs
        return list(all_urls)

    def scrape(self, keyword: str, num_results: int = 50, max_runtime_minutes: int = 15, task_id=None, task_record=None):
        """
        Main method to scrape contact information based on a keyword.
        
        Args:
            keyword: Search keyword
            num_results: Maximum number of results to return
            max_runtime_minutes: Maximum runtime in minutes
            task_id: Optional task ID for tracking progress
            task_record: Optional database record for progress tracking
            
        Returns:
            Dict containing emails, phones, and task information
        """
        start_time = time.time()
        max_runtime_seconds = max_runtime_minutes * 60
        
        # Create a task ID if not provided
        if not task_id and task_record:
            if hasattr(task_record, 'id'):
                task_id = task_record.id
            elif hasattr(task_record, 'task_id'):
                task_id = task_record.task_id
        
        emails = set()
        phones = set()
        scraped_urls = set()  # Track already scraped URLs
        search_page = 1  # Track which search result page we're on
        max_search_pages = 10  # Maximum search pages to try
        
        # Tracking proxy performance
        successful_proxy_requests = 0
        failed_proxy_requests = 0
        proxy_rotation_threshold = 3  # Rotate proxy after this many consecutive failures
        consecutive_failures = 0
        
        # For better time management
        time_per_url = 10  # Initial estimate of seconds needed per URL
        urls_processed = 0
        
        # Set of known spam domains to filter out early
        spam_domains = {
            'pinterest.com', 'youtube.com', 'facebook.com', 'instagram.com', 'twitter.com',
            'linkedin.com', 'tiktok.com', 'reddit.com', 'quora.com', 'indeed.com', 'glassdoor.com',
            'alibaba.com', 'indiamart.com', 'tradeindia.com', 'amazon.com', 'flipkart.com',
            'justdial.com', 'sulekha.com', 'craigslist.org', 'naukri.com', 'monster.com',
            'yelp.com', 'zomato.com', 'swiggy.com', 'imdb.com', 'wikipedia.org', 'wikihow.com'
        }
        
        # URLs where we've found results
        successful_urls = []
        results_by_url = []
        
        # For tracking timeouts
        timeout_count = 0
        max_timeouts = 5  # Maximum consecutive timeouts before changing approach
        
        # Initialize target counts
        self.target_results = num_results
        self.found_emails = set()
        self.found_phones = set()
        
        self.logger.info(f"Starting scrape for keyword: '{keyword}'")
        print(f"🔍 Starting search for '{keyword}', targeting {num_results} contacts within {max_runtime_minutes} minutes")
        
        # Initialize task status if tracking is enabled
        if task_id:
            status_data = {
                "status": "processing",
                "progress": 5,
                "message": f"Starting search for '{keyword}'",
                "keyword": keyword,
                "task_id": task_id,
                "results_count": 0,
                "elapsed_time": 0
            }
            self.update_task_status(task_id, status_data, task_record)
        
        try:
            # Optimize the search query using Gemini API
            try:
                optimized_query = self.optimize_search_query_with_gemini(keyword)
                self.logger.info(f"Original keyword: '{keyword}' | Optimized query: '{optimized_query}'")
                print(f"🧠 Optimized search query: {optimized_query}")
            except Exception as query_error:
                self.logger.error(f"Error optimizing query: {query_error}")
                optimized_query = keyword
                print(f"⚠️ Using original query due to optimization error: {keyword}")
                
                # Update task status with the error
                if task_id:
                    status_data = {
                        "status": "processing",
                        "progress": 5,
                        "message": f"Error optimizing query: {str(query_error)[:100]}. Continuing with original query.",
                        "keyword": keyword,
                        "task_id": task_id,
                        "results_count": 0,
                        "elapsed_time": 0
                    }
                    self.update_task_status(task_id, status_data, task_record)

            while len(phones) < num_results and search_page <= max_search_pages:
                # Check if we've exceeded our runtime
                elapsed_time = time.time() - start_time
                if elapsed_time > max_runtime_seconds:
                    self.logger.info(f"Reached maximum runtime of {max_runtime_minutes} minutes")
                    print(f"⏱️ Time limit reached after {elapsed_time/60:.1f} minutes")
                    break
                
                # Calculate remaining time and adjust strategy
                remaining_seconds = max_runtime_seconds - elapsed_time
                print(f"⏱️ {remaining_seconds/60:.1f} minutes remaining of {max_runtime_minutes} minutes")
                
                # Update task progress if tracking is enabled
                if task_id:
                    # Calculate progress based on time or results
                    time_progress = min(int((elapsed_time / max_runtime_seconds) * 90), 90)
                    results_progress = min(int((len(phones) / num_results) * 90), 90)
                    progress = max(time_progress, results_progress)
                    
                    status_data = {
                        "status": "processing",
                        "progress": progress,
                        "message": f"Searching page {search_page}, found {len(emails)} emails and {len(phones)} phones",
                        "keyword": keyword,
                        "task_id": task_id,
                        "results_count": len(emails) + len(phones),
                        "elapsed_time": elapsed_time / 60.0
                    }
                    if 'update_task_status' in globals():
                        globals()['update_task_status'](task_id, status_data, task_record)
                
                # Update time per URL estimate if we have data
                if urls_processed > 0:
                    time_per_url = elapsed_time / urls_processed
                
                # SEARCH FOR URLS
                print(f"🔍 Searching for {keyword} (page {search_page})...")
                
                # First optimize the search query if we haven't done so yet
                if not 'optimized_query' in locals():
                    optimized_query = self.optimize_search_query_with_gemini(keyword)
                    self.logger.info(f"Original keyword: '{keyword}' | Optimized query: '{optimized_query}'")
                    print(f"🧠 Optimized search query: {optimized_query}")
                
                # Use multiple search strategies if we're having trouble finding results
                search_results = []
                
                # Try Google first
                if search_page <= 2:
                    print(f"🔍 Trying Google search...")
                    search_results = self.search_google(optimized_query, num_results=10, page=search_page-1)
                
                # If Google didn't work or we're on later pages, try DuckDuckGo
                if not search_results:
                    # Increment page counter even if no results
                    search_page += 1
                    
                    # If we've had security issues with Google, try a simpler query
                    if search_page > 1:
                        print("⚠️ Security checks detected. Trying simpler query...")
                        # Create a very simple query without special operators
                        simple_query = f'"{keyword}" contact'
                        if 'delhi' in keyword.lower() or 'india' in keyword.lower():
                            simple_query += ' site:.in'
                        print(f"🔍 Using simplified query: {simple_query}")
                        
                        # Try with Google again with a simpler query
                        print(f"🔍 Trying Google search with simplified query...")
                        search_results = self.search_google(simple_query, num_results=10, page=0)
                        
                        # If that failed too, try direct search as last resort
                        if not search_results and hasattr(self, 'direct_search'):
                            print(f"🔍 Trying direct search as last resort...")
                            try:
                                search_results = self.direct_search(simple_query, num_results=10)
                            except Exception as e:
                                self.logger.error(f"Direct search failed: {e}")
                else:
                    # Increment page counter if we got results
                    search_page += 1
                
                if not search_results:
                    print("❌ No search results found. Trying a different query...")
                    # If we've tried multiple pages without results, try a completely different approach
                    if search_page > 3:
                        # Create a much simpler query with minimal operators
                        print("🔄 Trying drastically simplified query as last attempt...")
                        last_resort_query = keyword.replace('"', '').strip()
                        # Try with quotes only around the main term
                        simple_query = f'"{last_resort_query}" contact'
                        print(f"🔍 Last resort query: {simple_query}")
                        
                        # Try Google one more time with very basic query
                        search_results = self.search_google(simple_query, num_results=15, page=0)
                        
                        if not search_results:
                            print("⚠️ Multiple search attempts failed. Trying direct search as last resort.")
                            # Try our direct search method as a final fallback
                            print("🔎 Using direct search for specific URLs...")
                            search_results = self.direct_search(keyword, num_results=15)
                            
                            if not search_results:
                                print("⚠️ All search methods failed. Stopping search.")
                                break
                    else:
                        continue
                
                if search_results:
                    print(f"✅ Found {len(search_results)} URLs to check")
                    
                    # Process each URL from the search results
                    for url in search_results:
                        # Skip already scraped URLs
                        if url in scraped_urls:
                            continue
                            
                        # Check if we've exceeded our runtime
                        elapsed_time = time.time() - start_time
                        if elapsed_time > max_runtime_seconds:
                            print(f"⏱️ Time limit reached during URL processing")
                            break
                            
                        # Skip known spam domains
                        domain = urlparse(url).netloc
                        if any(spam in domain for spam in spam_domains):
                            print(f"⏭️ Skipping known spam domain: {domain}")
                            continue
                            
                        print(f"🌐 Checking {url}...")
                        
                        # Extract contacts from this URL
                        try:
                            emails_found, phones_found = self.extract_contacts_from_url(url)
                            urls_processed += 1
                            
                            # Log results for this URL
                            if emails_found or phones_found:
                                print(f"✅ Found on {domain}:")
                                
                                # Display emails with clear formatting
                                if emails_found:
                                    print("  📧 EMAILS:")
                                    for email in emails_found:
                                        print(f"    • {email}")
                                        emails.add(email)
                                
                                # Display phones with clear formatting
                                if phones_found:
                                    print("  📱 PHONES:")
                                    for phone in phones_found:
                                        if isinstance(phone, dict):
                                            phone_display = phone.get('phone', str(phone))
                                            print(f"    • {phone_display}")
                                        else:
                                            print(f"    • {phone}")
                                        phones.add(phone)
                                
                                # Track successful URLs
                                successful_urls.append(url)
                                
                                # Update progress if tracking is enabled
                                if task_id:
                                    # Update progress and message with latest count
                                    progress = min(int((len(phones) / num_results) * 90), 90)
                                    status_data = {
                                        "status": "processing",
                                        "progress": progress,
                                        "message": f"Found {len(emails)} emails and {len(phones)} phones",
                                        "keyword": keyword,
                                        "task_id": task_id,
                                        "results_count": len(emails) + len(phones),
                                        "elapsed_time": (time.time() - start_time) / 60.0
                                    }
                                    if 'update_task_status' in globals():
                                        globals()['update_task_status'](task_id, status_data, task_record)
                            else:
                                print(f"ℹ️ No contacts found on {domain}")
                            
                            # Add result to structured results
                            results_by_url.append({
                                'url': url,
                                'domain': domain,
                                'emails': list(emails_found),
                                'phones': list(phones_found)
                            })
                            
                            # Mark URL as scraped to avoid duplicates
                            scraped_urls.add(url)
                            
                            # Check if we've reached our target
                            if len(phones) >= num_results:
                                print(f"🎯 Target number of contacts reached!")
                                break
                                
                        except Exception as e:
                            self.logger.error(f"Error extracting contacts from {url}: {e}")
                            print(f"❌ Error checking {url}: {str(e)}")
                            
                            # Record failure but continue with next URL
                            results_by_url.append({
                                'url': url,
                                'domain': domain,
                                'emails': [],
                                'phones': [],
                                'error': str(e)
                            })
                            scraped_urls.add(url)
                else:
                    print("❌ No URLs found from search. Moving to next page...")
                    # If we've tried multiple pages without results, break the loop
                    if search_page > 3:
                        print("⚠️ Multiple search pages without results. Stopping search.")
                        break
            
            # Return more comprehensive results for Celery tasks
            result = {
                "emails": emails,
                "phones": phones,
                "task_info": {
                    "task_id": task_id,
                    "keyword": keyword,
                    "optimized_query": optimized_query,
                    "completion_time": datetime.now().isoformat(),
                    "elapsed_time_minutes": (time.time() - start_time) / 60.0,
                    "urls_processed": urls_processed,
                    "successful_urls": successful_urls,
                    "status": "completed",
                    "results_count": len(emails) + len(phones)
                }
            }
            
            # Save results to CSV
            if emails or phones:
                csv_filename = self.save_results_to_csv(keyword, emails, phones) 
                result["task_info"]["csv_filename"] = csv_filename
                
                # Save detailed results if we have them
                if results_by_url:
                    detailed_csv = self.save_detailed_results_to_csv(keyword, results_by_url)
                    result["task_info"]["detailed_csv"] = detailed_csv
            
            # Update task status to completed
            if task_id:
                status_data = {
                    "status": "completed",
                    "progress": 100,
                    "message": f"Completed. Found {len(emails)} emails and {len(phones)} phones",
                    "keyword": keyword,
                    "task_id": task_id,
                    "results_count": len(emails) + len(phones),
                    "elapsed_time": (time.time() - start_time) / 60.0
                }
                self.update_task_status(task_id, status_data, task_record)
            
            self.logger.info(f"Scraping completed: found {len(emails)} emails and {len(phones)} phones")
            return result
            
        except Exception as e:
            self.logger.error(f"Error during scraping: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            
            # Ensure we update the task status to show the error to the frontend
            status_data = {
                "status": "error",
                "progress": 0,
                "message": f"Error: {str(e)}",
                "keyword": keyword,
                "task_id": task_id,
                "results_count": len(emails) + len(phones),
                "elapsed_time": (time.time() - start_time) / 60.0
            }
            
            if task_id:
                self.update_task_status(task_id, status_data, task_record)
                
            return {
                "emails": emails,
                "phones": phones,
                "task_info": {
                    "task_id": task_id,
                    "keyword": keyword,
                    "optimized_query": optimized_query if 'optimized_query' in locals() else None,
                    "status": "error",
                    "error_message": str(e),
                    "elapsed_time_minutes": (time.time() - start_time) / 60.0,
                    "results_count": len(emails) + len(phones)
                }
            }

    # Update the status with better database handling
    def update_task_status(self, task_id, status, task_record=None):
        """Update the task status in the database and/or via callback"""
        # Log the status update for tracking
        logging.info(f"Updating task {task_id}: {status.get('status', 'unknown')}, progress: {status.get('progress', 0)}%")
        
        # Try to use the global function first (if we're in a Django/Flask app)
        if 'update_task_status' in globals():
            try:
                globals()['update_task_status'](task_id, status, task_record)
                return
            except Exception as e:
                logging.error(f"Failed to use global update_task_status: {e}")
        
        # Fall back to updating the task_record directly
        if task_record:
            try:
                # First log task status to files for better tracking
                task_log_dir = os.path.join('scraper_logs', 'tasks')
                os.makedirs(task_log_dir, exist_ok=True)
                
                # Current timestamp for logs
                timestamp = datetime.now().isoformat()
                
                # Write task status to a JSON log file
                json_log_path = os.path.join(task_log_dir, f'task_{task_id}_json.log')
                with open(json_log_path, 'a') as f:
                    # Add timestamp to the status
                    status_with_time = status.copy()
                    status_with_time['timestamp'] = timestamp
                    f.write(json.dumps(status_with_time) + '\n')
                
                # Also write to a human-readable text log file
                text_log_path = os.path.join(task_log_dir, f'task_{task_id}.log')
                with open(text_log_path, 'a') as f:
                    # Format the status update as a human-readable log entry
                    progress = status.get("progress", 0)
                    status_type = status.get("status", "processing")
                    message = status.get("message", "No message")
                    results_count = status.get("results_count", 0)
                    
                    log_entry = f"[{timestamp}] Status: {status_type.upper()} | Progress: {progress}% | Results: {results_count} | Message: {message}\n"
                    f.write(log_entry)
                
                # Update Django model if available
                task_record.progress = status.get("progress", 0)
                task_record.status = status.get("status", "processing")
                task_record.message = status.get("message", "")
                
                # Set completed timestamp if task is finished
                if status.get("status") == "completed" or status.get("status") == "error" or status.get("status") == "failed":
                    # Try to use Django's timezone if available
                    try:
                        from django.utils import timezone
                        task_record.completed_at = timezone.now()
                    except ImportError:
                        task_record.completed_at = datetime.now()
                    
                    # Add error message if there's an error
                    if status.get("status") == "error" or status.get("status") == "failed":
                        if hasattr(task_record, 'error_message'):
                            task_record.error_message = status.get("message", "Unknown error")
                
                # Try to save the record
                if hasattr(task_record, 'save') and callable(task_record.save):
                    task_record.save()
                    logging.info(f"✅ Successfully updated task record in database: {task_record.status}")
                else:
                    logging.warning("⚠️ Task record has no save method")
            except Exception as e:
                print(f"Error updating task record: {e}")
                import traceback
                print(traceback.format_exc())
        else:
            # Log that we don't have a task record
            logging.warning(f"No task record provided for task_id {task_id}")
            
            # Still write the status to log files even without a task record
            try:
                task_log_dir = os.path.join('scraper_logs', 'tasks')
                os.makedirs(task_log_dir, exist_ok=True)
                
                # Current timestamp for logs
                timestamp = datetime.now().isoformat()
                
                # Write to text log file
                text_log_path = os.path.join(task_log_dir, f'task_{task_id}.log')
                with open(text_log_path, 'a') as f:
                    progress = status.get("progress", 0)
                    status_type = status.get("status", "processing")
                    message = status.get("message", "No message")
                    
                    log_entry = f"[{timestamp}] Status: {status_type.upper()} | Progress: {progress}% | Message: {message}\n"
                    f.write(log_entry)
            except Exception as log_error:
                logging.error(f"Failed to write status to log file: {log_error}")

    # Define the function but don't call it at module level
    def parse_arguments():
        parser = argparse.ArgumentParser(description='Web scraper for contact information')
        parser.add_argument('--keyword', type=str, help='Search keyword for finding contacts', required=True)
        parser.add_argument('--results', type=int, default=50, help='Number of contacts to find')
        parser.add_argument('--time', type=int, default=15, help='Maximum runtime in minutes')
        parser.add_argument('--no-browser', action='store_true', help='Disable browser automation')
        parser.add_argument('--api-mode', action='store_true', help='Run in API mode (reduced output)')
        return parser.parse_args()

    def get_request_session(self):
        """Return a properly configured requests session for making HTTP requests.
        This session includes appropriate cookies and headers for better stealth.
        """
        # Use the existing session object
        if not hasattr(self, 'session') or self.session is None:
            self.session = requests.Session()
            
        # Add cookies if available
        if hasattr(self, 'cookies') and self.cookies:
            self.session.cookies.update(self.cookies)
            
        # Configure session for better reliability
        adapter = requests.adapters.HTTPAdapter(
            max_retries=3,
            pool_connections=10,
            pool_maxsize=10
        )
        
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
        # Set a reasonable timeout
        self.session.timeout = 30
        
        return self.session

    async def _search_duckduckgo_with_browser(self, keyword: str, num_results: int = 10) -> List[str]:
        """
        DISABLED: DuckDuckGo search has been disabled.
        
        Args:
            keyword (str): Search keyword
            num_results (int): Maximum number of results to return
            
        Returns:
            List[str]: Empty list (method disabled)
        """
        self.logger.info("DuckDuckGo browser search method has been disabled")
        print("⚠️ DuckDuckGo browser search method has been disabled by administrator")
        return []

    
    def extract_contacts_from_url(self, url):
        """
        Extract contact information from a given URL with enhanced scraping techniques.
        
        Args:
            url: URL to scrape
            
        Returns:
            tuple: (set of emails, set of phones)
        """
        # Extract domain for logging
        domain = urlparse(url).netloc
        self.logger.info(f"Extracting contacts from: {url}")
        
        # Initialize result sets
        emails = set()
        phones = set()
        
        # Check if domain is in excluded list
        if domain in self.excluded_domains:
            self.logger.info(f"Skipping excluded domain: {domain}")
            return emails, phones
            
        # Track extraction success
        browser_success = False
        request_success = False
        
        # Try with browser first if available (more reliable for modern sites)
        if self.use_browser and self.browser_initialized:
            try:
                self.logger.info(f"Attempting browser-based extraction for {url}")
                # Use the event loop
                loop = get_or_create_event_loop()
                browser_content = loop.run_until_complete(self.browser_get_page(url))
                
                if browser_content:
                    # Process the content from browser
                    browser_emails, browser_phones = self._extract_all_contacts(browser_content, url, domain)
                    emails.update(browser_emails)
                    phones.update(browser_phones)
                    self.logger.info(f"Browser extraction found {len(browser_emails)} emails and {len(browser_phones)} phones")
                    browser_success = len(browser_emails) > 0 or len(browser_phones) > 0
                else:
                    self.logger.warning(f"Browser extraction failed for {url}, falling back to direct request")
            except Exception as e:
                self.logger.error(f"Error in browser extraction: {e}")
                # Continue to regular request method as fallback
        
        # Try direct request method if browser didn't succeed or we don't have enough contacts
        if not browser_success or (len(emails) < 2 and len(phones) < 2):
            try:
                headers = {
                    'User-Agent': self.get_random_user_agent(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': 'https://www.google.com/',
                    'DNT': '1',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'max-age=0',
                    'TE': 'Trailers',
                    # Add more headers to look more like a browser
                    'sec-ch-ua': '"Google Chrome";v="113", "Chromium";v="113"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1'
                }
                
                # Apply random delay between requests
                time.sleep(random.uniform(1, 3))
                
                # Add cookies from previous requests if available
                cookies = self.session.cookies if hasattr(self, 'session') else None
                
                # Use our optimized request method
                response = requests.get(url, headers=headers, timeout=30, cookies=cookies)
                
                if response.status_code == 200:
                    # Process the content from direct request
                    request_emails, request_phones = self._extract_all_contacts(response.text, url, domain)
                    emails.update(request_emails)
                    phones.update(request_phones)
                    self.logger.info(f"Direct request found {len(request_emails)} emails and {len(request_phones)} phones")
                    request_success = len(request_emails) > 0 or len(request_phones) > 0
                else:
                    self.logger.warning(f"Failed to fetch {url}: Status {response.status_code}")
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout requesting {url}")
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Connection error requesting {url}")
            except Exception as e:
                self.logger.error(f"Error extracting contacts from {url}: {e}")
        
        # Check contact pages if we still don't have enough contacts
        if not browser_success and not request_success or (len(emails) < 2 and len(phones) < 2):
            self.logger.info(f"Searching for contact pages on {domain}")
            contact_urls = self._find_contact_urls(url, domain)
            
            for contact_url in contact_urls[:3]:  # Check up to 3 contact pages
                try:
                    self.logger.info(f"Checking contact page: {contact_url}")
                    
                    # Apply random delay between requests
                    time.sleep(random.uniform(1, 3))
                    
                    headers = {
                        'User-Agent': self.get_random_user_agent(),
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                        'Accept-Language': 'en-US,en;q=0.5',
                        'Referer': url,  # Use original URL as referer
                        'DNT': '1',
                        'Connection': 'keep-alive'
                    }
                    
                    # First try browser for contact page if available
                    contact_content = None
                    if self.use_browser and self.browser_initialized:
                        try:
                            loop = get_or_create_event_loop()
                            contact_content = loop.run_until_complete(self.browser_get_page(contact_url))
                        except Exception as e:
                            self.logger.warning(f"Browser failed for contact page {contact_url}: {e}")
                    
                    # Fall back to direct request if browser failed
                    if not contact_content:
                        contact_response = requests.get(contact_url, headers=headers, timeout=30)
                        
                        if contact_response.status_code == 200:
                            contact_content = contact_response.text
                    
                    # Process the content if we got it
                    if contact_content:
                        contact_emails, contact_phones = self._extract_all_contacts(contact_content, contact_url, domain)
                        emails.update(contact_emails)
                        phones.update(contact_phones)
                        self.logger.info(f"Contact page {contact_url} found {len(contact_emails)} emails and {len(contact_phones)} phones")
                        
                        # If we found good contacts, no need to check more pages
                        if len(contact_emails) > 0 or len(contact_phones) > 0:
                            break
                except Exception as e:
                    self.logger.warning(f"Error fetching contact page {contact_url}: {e}")
        
        # For Indian businesses, try some common email patterns if we still don't have enough
        if len(emails) == 0 and 'in' in domain.split('.')[-1]:
            self.logger.info(f"Trying to generate likely emails for Indian domain: {domain}")
            generated_emails = self._generate_likely_emails(domain)
            if generated_emails:
                self.logger.info(f"Generated {len(generated_emails)} potential emails")
                emails.update(generated_emails)
        
        # Log and return results
        self.logger.info(f"Found {len(emails)} emails and {len(phones)} phones on {domain}")
        return emails, phones
    
    def _extract_all_contacts(self, html_content, url, domain):
        """
        Comprehensive contact extraction from HTML content using all available methods.
        
        Args:
            html_content: HTML content to parse
            url: Source URL
            domain: Domain name
            
        Returns:
            tuple: (set of emails, set of phones)
        """
        emails = set()
        phones = set()
        
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 1. Extract from page text with enhanced approach
            text = soup.get_text(separator=' ', strip=True)
            text_emails = self._extract_emails_from_text(text)
            text_phones = self._extract_phones_from_text(text, f"{domain}_text")
            emails.update(text_emails)
            phones.update(text_phones)
            
            # 2. Extract from HTML attributes with expanded attribute search
            attr_emails, attr_phones = self._extract_from_attributes(soup, domain)
            emails.update(attr_emails)
            phones.update(attr_phones)
            
            # 3. Extract from structured data
            struct_emails, struct_phones = self._extract_from_structured_data(html_content, domain)
            emails.update(struct_emails)
            phones.update(struct_phones)
            
            # 4. Extract from JavaScript with improved pattern matching
            js_emails, js_phones = self._extract_from_javascript(html_content)
            emails.update(js_emails)
            phones.update(js_phones)
            
            # 5. Extract obfuscated emails
            obfs_emails = self._extract_obfuscated_emails(html_content)
            emails.update(obfs_emails)
            
            # 6. Extract from comment blocks (often hide contact info)
            comments_emails, comments_phones = self._extract_from_comments(soup, domain)
            emails.update(comments_emails)
            phones.update(comments_phones)
            
            # 7. Extract from data attributes
            data_emails, data_phones = self._extract_from_data_attributes(soup, domain)
            emails.update(data_emails)
            phones.update(data_phones)
            
            # 8. Look for contact info in image alt text and title attributes
            image_emails, image_phones = self._extract_from_image_attributes(soup, domain)
            emails.update(image_emails)
            phones.update(image_phones)
            
            # Apply validation to all found emails
            validated_emails = set()
            for email in emails:
                if self._validate_email(email):
                    validated_emails.add(email.lower())
            
            # Apply validation to all found phones
            validated_phones = set()
            for phone in phones:
                if isinstance(phone, str):
                    validated = self.validate_indian_phone(phone, f"{domain}_validation")
                    if validated:
                        # Handle different return formats from validate_indian_phone
                        if isinstance(validated, dict) and 'formatted' in validated:
                            validated_phones.add(validated['formatted'])
                        elif isinstance(validated, str):
                            validated_phones.add(validated)
                        else:
                            # Fallback to the original phone number if validation returns a dict without 'formatted'
                            if isinstance(validated, dict) and 'phone' in validated:
                                validated_phones.add(validated['phone'])
                            else:
                                validated_phones.add(phone)
                else:
                    # If it's already a dict, try to get the formatted version or use as is
                    if isinstance(phone, dict) and 'formatted' in phone:
                        validated_phones.add(phone['formatted'])
                    elif isinstance(phone, dict) and 'phone' in phone:
                        validated_phones.add(phone['phone'])
                    else:
                        validated_phones.add(str(phone))
                    
            return validated_emails, validated_phones
            
        except Exception as e:
            self.logger.error(f"Error in comprehensive contact extraction: {e}")
            return emails, phones
    
    def _extract_from_comments(self, soup, domain):
        """Extract contact information from HTML comment blocks."""
        emails = set()
        phones = set()
        
        try:
            # Find all HTML comments
            comments = soup.find_all(string=lambda text: isinstance(text, Comment))
            
            for comment in comments:
                # Extract emails from comments
                comment_emails = self._extract_emails_from_text(comment)
                emails.update(comment_emails)
                
                # Extract phones from comments
                comment_phones = self._extract_phones_from_text(comment, f"{domain}_comment")
                phones.update(comment_phones)
                
            return emails, phones
            
        except Exception as e:
            self.logger.error(f"Error extracting from comments: {e}")
            return set(), set()
    
    def _extract_from_data_attributes(self, soup, domain):
        """Extract contact information from data-* attributes."""
        emails = set()
        phones = set()
        
        try:
            # Find elements with data-* attributes
            elements = soup.find_all(lambda tag: any(attr.startswith('data-') for attr in tag.attrs))
            
            for element in elements:
                # Check each data-* attribute
                for attr_name, attr_value in element.attrs.items():
                    if attr_name.startswith('data-') and isinstance(attr_value, str):
                        # Extract emails from attribute value
                        attr_emails = self._extract_emails_from_text(attr_value)
                        emails.update(attr_emails)
                        
                        # Extract phones from attribute value
                        attr_phones = self._extract_phones_from_text(attr_value, f"{domain}_data_attr")
                        phones.update(attr_phones)
                        
                        # Look for contact-specific attributes
                        contact_attributes = ['data-email', 'data-contact', 'data-phone', 'data-mobile', 
                                            'data-tel', 'data-fax', 'data-info', 'data-whatsapp']
                        
                        if attr_name.lower() in contact_attributes and attr_value:
                            # Check if it's an email attribute
                            if 'email' in attr_name.lower() and '@' in attr_value:
                                if self._validate_email(attr_value):
                                    emails.add(attr_value.lower())
                            
                            # Check if it's a phone attribute
                            if any(phone_term in attr_name.lower() for phone_term in ['phone', 'mobile', 'tel', 'fax', 'whatsapp']):
                                validated_phones = self._extract_phones_from_text(attr_value, f"{domain}_data_attr_specific")
                                phones.update(validated_phones)
                
            return emails, phones
            
        except Exception as e:
            self.logger.error(f"Error extracting from data attributes: {e}")
            return set(), set()
    
    def _extract_from_image_attributes(self, soup, domain):
        """Extract contact information from image alt text and title attributes."""
        emails = set()
        phones = set()
        
        try:
            # Find all images
            images = soup.find_all('img')
            
            for img in images:
                # Check alt text
                alt_text = img.get('alt', '')
                if alt_text:
                    # Extract emails from alt text
                    alt_emails = self._extract_emails_from_text(alt_text)
                    emails.update(alt_emails)
                    
                    # Extract phones from alt text
                    alt_phones = self._extract_phones_from_text(alt_text, f"{domain}_img_alt")
                    phones.update(alt_phones)
                
                # Check title attribute
                title_text = img.get('title', '')
                if title_text:
                    # Extract emails from title text
                    title_emails = self._extract_emails_from_text(title_text)
                    emails.update(title_emails)
                    
                    # Extract phones from title text
                    title_phones = self._extract_phones_from_text(title_text, f"{domain}_img_title")
                    phones.update(title_phones)
                    
                # Check if the image itself is a contact icon by its name or class
                contact_indicators = ['email', 'mail', 'contact', 'phone', 'tel', 'call', 'whatsapp']
                
                if (img.get('src', '') and any(indicator in img.get('src', '').lower() for indicator in contact_indicators) or
                    img.get('class', '') and any(indicator in ' '.join(img.get('class', [])).lower() for indicator in contact_indicators)):
                    
                    # Check parent or nearby elements for contact info
                    parent = img.parent
                    if parent:
                        parent_text = parent.get_text()
                        parent_emails = self._extract_emails_from_text(parent_text)
                        emails.update(parent_emails)
                        
                        parent_phones = self._extract_phones_from_text(parent_text, f"{domain}_img_parent")
                        phones.update(parent_phones)
                
            return emails, phones
            
        except Exception as e:
            self.logger.error(f"Error extracting from image attributes: {e}")
            return set(), set()
    
    def _generate_likely_emails(self, domain):
        """Generate likely email addresses for a domain based on common patterns."""
        likely_emails = set()
        
        try:
            # Strip any subdomains
            base_domain = domain
            if domain.count('.') > 1:
                base_domain_parts = domain.split('.')
                if len(base_domain_parts) > 2:
                    base_domain = '.'.join(base_domain_parts[-2:])
            
            # Common prefixes used by Indian businesses
            common_prefixes = [
                'info', 'contact', 'support', 'sales', 'hello',
                'admin', 'enquiry', 'enquiries', 'help', 'office',
                'marketing', 'customercare', 'feedback', 'business',
                'order', 'hr', 'careers', 'webmaster'
            ]
            
            # Generate potential emails
            for prefix in common_prefixes:
                email = f"{prefix}@{base_domain}"
                if self._validate_email(email):
                    likely_emails.add(email.lower())
            
            return likely_emails
            
        except Exception as e:
            self.logger.error(f"Error generating likely emails: {e}")
            return set()

    def _find_contact_urls(self, base_url, domain):
        """
        Find contact page URLs for a given website.
        
        Args:
            base_url: Base URL of the website
            domain: Domain name
            
        Returns:
            list: List of contact page URLs
        """
        contact_urls = []
        try:
            # First try to construct common contact page URLs
            parsed_url = urlparse(base_url)
            base_scheme = parsed_url.scheme
            
            # Common contact page paths
            common_paths = [
                '/contact', '/contact-us', '/contactus', '/contact_us',
                '/about', '/about-us', '/aboutus', '/about_us',
                '/reach-us', '/get-in-touch', '/support'
            ]
            
            # Add URLs with common paths
            for path in common_paths:
                contact_url = f"{base_scheme}://{domain}{path}"
                contact_urls.append(contact_url)
                
            # If we have the page content, also look for contact links
            headers = {
                'User-Agent': self.get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }
            
            try:
                response = requests.get(base_url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for contact page links
                    contact_keywords = ['contact', 'about', 'contact-us', 'about-us', 'reach', 'touch', 'support']
                    for link in soup.find_all('a', href=True):
                        href = link.get('href', '')
                        link_text = link.get_text().lower()
                        
                        # Check both link URL and text for contact keywords
                        if any(keyword in href.lower() for keyword in contact_keywords) or \
                           any(keyword in link_text for keyword in contact_keywords):
                            
                            # Handle relative URLs
                            if not href.startswith(('http://', 'https://')):
                                if href.startswith('/'):
                                    href = f"{base_scheme}://{domain}{href}"
                                else:
                                    href = f"{base_scheme}://{domain}/{href}"
                            
                            # Only follow links on the same domain
                            if domain in href:
                                contact_urls.append(href)
            except Exception as e:
                self.logger.warning(f"Error fetching base URL to find contact pages: {e}")
                
            # Return unique URLs
            return list(dict.fromkeys(contact_urls))
            
        except Exception as e:
            self.logger.error(f"Error finding contact URLs: {e}")
            return contact_urls

    
    def _extract_emails_from_text(self, text: str) -> Set[str]:
        """
        Extract email addresses from text with advanced pattern matching.
        
        Args:
            text: The text to extract emails from
            
        Returns:
            Set of validated email addresses
        """
        if not text:
            return set()
            
        emails = set()
        
        # Standard email pattern
        standard_matches = self.email_pattern.findall(text)
        for email in standard_matches:
            if self._validate_email(email):
                emails.add(email.lower())
                
        # Obfuscated email pattern (with "at" and "dot")
        obfuscated_matches = self.obfuscated_email_pattern.findall(text)
        for match in obfuscated_matches:
            if len(match) == 3:  # username, domain, tld
                reconstructed_email = f"{match[0]}@{match[1]}.{match[2]}"
                if self._validate_email(reconstructed_email):
                    emails.add(reconstructed_email.lower())
                    
        # Look for emails with entities like &#64; instead of @
        try:
            decoded_text = self._decode_html_entities(text)
            if decoded_text != text:
                decoded_matches = self.email_pattern.findall(decoded_text)
                for email in decoded_matches:
                    if email not in standard_matches and self._validate_email(email):
                        emails.add(email.lower())
        except Exception:
            pass
            
        # Look for emails with spaces or line breaks between parts
        try:
            # Remove spaces and line breaks
            condensed_text = re.sub(r'\s+', '', text)
            if condensed_text != text:
                condensed_matches = self.email_pattern.findall(condensed_text)
                for email in condensed_matches:
                    if email not in standard_matches and self._validate_email(email):
                        emails.add(email.lower())
        except Exception:
            pass
            
        # Look for emails with text replacements like "at" for "@" and "dot" for "."
        text_replacement_pattern = re.compile(r'([a-zA-Z0-9._%+-]+)\s*(?:\[at\]|\(at\)|@at@|at)\s*([a-zA-Z0-9.-]+)\s*(?:\[dot\]|\(dot\)|dot)\s*([a-zA-Z]{2,})', re.IGNORECASE)
        text_replacement_matches = text_replacement_pattern.findall(text)
        for match in text_replacement_matches:
            if len(match) == 3:
                reconstructed_email = f"{match[0]}@{match[1]}.{match[2]}"
                if self._validate_email(reconstructed_email):
                    emails.add(reconstructed_email.lower())
                    
        # Look for emails with image or unicode replacements mentioned in text
        email_indicators = [
            r'(?:email|e-mail|mail|mailto)\s*(?:address|id|us|:)\s*([a-zA-Z0-9._%+-]+\s*@\s*[a-zA-Z0-9.-]+\s*\.\s*[a-zA-Z]{2,})',
            r'(?:email|e-mail|mail|mailto)\s*(?:address|id|us|:)\s*([a-zA-Z0-9._%+-]+\s*\[\s*@\s*\]\s*[a-zA-Z0-9.-]+\s*\[\s*\.\s*\]\s*[a-zA-Z]{2,})',
            r'(?:email|e-mail|mail|mailto)\s*(?:address|id|us|:)\s*([a-zA-Z0-9._%+-]+)\s*(?:at|@)\s*([a-zA-Z0-9.-]+)\s*(?:dot|\.)\s*([a-zA-Z]{2,})'
        ]
        
        for pattern in email_indicators:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, str):
                    # Clean up any spaces
                    cleaned_email = re.sub(r'\s+', '', match)
                    cleaned_email = cleaned_email.replace('[at]', '@').replace('[dot]', '.')
                    cleaned_email = cleaned_email.replace('(at)', '@').replace('(dot)', '.')
                    if self._validate_email(cleaned_email):
                        emails.add(cleaned_email.lower())
                elif isinstance(match, tuple) and len(match) == 3:
                    reconstructed_email = f"{match[0]}@{match[1]}.{match[2]}"
                    # Clean up any spaces
                    cleaned_email = re.sub(r'\s+', '', reconstructed_email)
                    if self._validate_email(cleaned_email):
                        emails.add(cleaned_email.lower())
                        
        # Look for URLs with mailto: links
        mailto_pattern = re.compile(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')
        mailto_matches = mailto_pattern.findall(text)
        for email in mailto_matches:
            if self._validate_email(email):
                emails.add(email.lower())
                
        return emails
    
    def _extract_phones_from_text(self, text: str, source: str = "unknown") -> Set[Union[str, Dict]]:
        """
        Extract phone numbers from text with advanced pattern matching specifically for Indian numbers.
        
        Args:
            text: The text to extract phone numbers from
            source: Source identifier for tracking
            
        Returns:
            Set of validated phone dictionaries
        """
        if not text:
            return set()
            
        phones = set()
        
        # Pre-process text to handle obfuscation
        # Replace common text obfuscations for phone numbers
        clean_text = text
        
        # Replace words with digits in confusing formats
        digit_replacements = {
            'zero': '0', 'one': '1', 'two': '2', 'three': '3', 'four': '4',
            'five': '5', 'six': '6', 'seven': '7', 'eight': '8', 'nine': '9',
            'oh': '0', 'o': '0', 'null': '0', 'ноль': '0',  # International texts
        }
        
        # Replace full words with digits, but only when they're separated and likely to be phone numbers
        # Look for patterns like "nine nine eight seven..."
        digit_word_pattern = re.compile(r'\b(zero|one|two|three|four|five|six|seven|eight|nine|oh|o|null)\b', re.IGNORECASE)
        
        # Count occurrences of digit words in sequence
        digit_word_count = len(digit_word_pattern.findall(text))
        if digit_word_count >= 4:  # Only replace if there are enough digit words in sequence
            for word, digit in digit_replacements.items():
                # Case insensitive replacement of whole words
                clean_text = re.sub(r'\b' + word + r'\b', digit, clean_text, flags=re.IGNORECASE)
        
        # Use the primary pattern
        phone_matches = self.phone_pattern.findall(clean_text)
        for match in phone_matches:
            if isinstance(match, tuple):
                # Handle tuple results from regex groups
                for group in match:
                    if group:
                        valid_phone = self.validate_indian_phone(group, source)
                        if valid_phone:
                            if isinstance(valid_phone, dict) and 'formatted' in valid_phone:
                                phones.add(valid_phone['formatted'])
                            elif isinstance(valid_phone, str):
                                phones.add(valid_phone)
            else:
                valid_phone = self.validate_indian_phone(match, source)
                if valid_phone:
                    if isinstance(valid_phone, dict) and 'formatted' in valid_phone:
                        phones.add(valid_phone['formatted'])
                    elif isinstance(valid_phone, str):
                        phones.add(valid_phone)
                    
        # Use the alternate pattern
        alt_matches = self.phone_pattern_alt.findall(clean_text)
        for match in alt_matches:
            if isinstance(match, tuple):
                # Handle tuple results from regex groups
                for group in match:
                    if group:
                        valid_phone = self.validate_indian_phone(group, source)
                        if valid_phone:
                            if isinstance(valid_phone, dict) and 'formatted' in valid_phone:
                                phones.add(valid_phone['formatted'])
                            elif isinstance(valid_phone, str):
                                phones.add(valid_phone)
            else:
                valid_phone = self.validate_indian_phone(match, source)
                if valid_phone:
                    if isinstance(valid_phone, dict) and 'formatted' in valid_phone:
                        phones.add(valid_phone['formatted'])
                    elif isinstance(valid_phone, str):
                        phones.add(valid_phone)
                    
        # Only look for 10-digit mobile numbers which are more reliable
        # Most Indian mobile numbers are 10 digits starting with 6, 7, 8, or 9
        mobile_pattern = r'\b[6789]\d{9}\b'
        mobile_matches = re.findall(mobile_pattern, clean_text)
        for digits in mobile_matches:
            valid_phone = self.validate_indian_phone(digits, f"{source}_mobile")
            if valid_phone:
                if isinstance(valid_phone, dict) and 'formatted' in valid_phone:
                    phones.add(valid_phone['formatted'])
                elif isinstance(valid_phone, str):
                    phones.add(valid_phone)
                
        # Look for +91 patterns specifically
        plus91_pattern = r'\+91[- ]?\d{10}'
        plus91_matches = re.findall(plus91_pattern, clean_text)
        for match in plus91_matches:
            valid_phone = self.validate_indian_phone(match, f"{source}_plus91")
            if valid_phone:
                if isinstance(valid_phone, dict) and 'formatted' in valid_phone:
                    phones.add(valid_phone['formatted'])
                elif isinstance(valid_phone, str):
                    phones.add(valid_phone)
                
        # Look for full STD codes (0 + 2-4 digits + 8 digits)
        # This is more selective than before to avoid partial numbers
        std_pattern = r'\b0\d{2,4}[- ]?\d{6,8}\b'
        std_matches = re.findall(std_pattern, clean_text)
        for match in std_matches:
            valid_phone = self.validate_indian_phone(match, f"{source}_std_code")
            if valid_phone:
                if isinstance(valid_phone, dict) and 'formatted' in valid_phone:
                    phones.add(valid_phone['formatted'])
                elif isinstance(valid_phone, str):
                    phones.add(valid_phone)
        
        # Look for phone numbers in text with phone/call/mobile/whatsapp prefixes
        # This helps find numbers that might be labeled explicitly
        phone_indicator_pattern = re.compile(r'(?:phone|call|mobile|cell|whatsapp|tel|telephone|contact)\s*(?:no|number|us|:|at)?\s*:?\s*((?:\+\d{1,3}[- ]?)?\d{3,4}[- ]?\d{3,4}[- ]?\d{3,4})', re.IGNORECASE)
        indicator_matches = phone_indicator_pattern.findall(clean_text)
        for match in indicator_matches:
            valid_phone = self.validate_indian_phone(match, f"{source}_indicator")
            if valid_phone:
                if isinstance(valid_phone, dict) and 'formatted' in valid_phone:
                    phones.add(valid_phone['formatted'])
                elif isinstance(valid_phone, str):
                    phones.add(valid_phone)
        
        # Look for phone number ranges or multiple numbers separated by /
        range_pattern = re.compile(r'(?:\+\d{1,3}[- ]?)?\d{3,4}[- ]?\d{3,4}[- ]?\d{3,4}\s*/\s*(?:\+\d{1,3}[- ]?)?\d{3,4}[- ]?\d{3,4}[- ]?\d{0,4}')
        range_matches = range_pattern.findall(clean_text)
        for match in range_matches:
            # Split by / and validate each part
            for part in match.split('/'):
                valid_phone = self.validate_indian_phone(part.strip(), f"{source}_range")
                if valid_phone:
                    if isinstance(valid_phone, dict) and 'formatted' in valid_phone:
                        phones.add(valid_phone['formatted'])
                    elif isinstance(valid_phone, str):
                        phones.add(valid_phone)
        
        return phones
        
    def _validate_email(self, email: str) -> bool:
        """
        Validate an email address with improved checks.
        
        Args:
            email: Email address to validate
            
        Returns:
            bool: True if the email is valid, False otherwise
        """
        if not email or not isinstance(email, str):
            return False
            
        # Basic pattern check
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False
            
        # Check length constraints
        if len(email) < 5 or len(email) > 254:
            return False
            
        # Split into local and domain parts
        try:
            local, domain = email.rsplit('@', 1)
            
            # Check local part constraints
            if not local or len(local) > 64:
                return False
                
            # Check domain constraints
            if not domain or len(domain) > 255:
                return False
                
            # Check for valid TLD
            tld = domain.rsplit('.', 1)[1]
            if len(tld) < 2:
                return False
                
            # Check for invalid characters in local part
            if re.search(r'[\s"(),;<>]', local):
                return False
                
            # Check for common disposable email domains
            disposable_domains = [
                'tempmail.com', 'throwaway.com', 'mailinator.com', 'guerrillamail.com',
                'temp-mail.org', 'yopmail.com', 'fakeinbox.com', 'sharklasers.com',
                'trashmail.com', '10minutemail.com', 'tempail.com', 'dispostable.com'
            ]
            if any(domain.lower().endswith(d) for d in disposable_domains):
                return False
                
            # Check for uncommon TLDs that are often spam
            spam_tlds = [
                'xyz', 'top', 'work', 'cricket', 'date', 'faith', 'science', 'men'
            ]
            if tld.lower() in spam_tlds:
                return False
                
            # Check for common spam patterns
            spam_patterns = [
                r'^\d{8,}@',  # Starts with many digits
                r'[A-Z]{10,}@',  # Lots of uppercase letters
                r'^admin@',  # Common spam sender
                r'^info@',  # Common spam sender
                r'^support@',  # Common spam sender
                r'^[a-z]{1,2}\d{4,}@'  # Short prefix with many numbers
            ]
            for pattern in spam_patterns:
                if re.search(pattern, email):
                    return False
                    
            # Use external validation function if available
            try:
                if validate_email(email):
                    return True
            except Exception:
                # If external function fails, fall back to our basic validation
                return True
                
            return True
            
        except Exception:
            return False
            
    def validate_indian_phone(self, phone: str, source: str = "unknown") -> Optional[Dict]:
        """
        Validate an Indian phone number and return standardized format.
        
        Args:
            phone: Phone number to validate
            source: Source identifier for tracking
            
        Returns:
            Dict with formatted phone or None if invalid
        """
        # Use the imported validator from improved_validators
        try:
            result = validate_indian_phone(phone, source)
            
            # Additional validation for short landline numbers
            # Many sites have short numbers like '28497664' which aren't useful without area code
            if result and isinstance(result, dict):
                # Check if it's a short landline without proper area code
                if 'type' in result and result['type'] == 'landline_short':
                    # Landline numbers should be at least 8 digits with area code
                    raw_number = re.sub(r'[^\d]', '', result.get('phone', ''))
                    
                    # If it's too short (less than 8 digits) or missing proper area code format
                    # (most Indian landlines have format: area code (2-4 digits) + number (6-8 digits))
                    if len(raw_number) < 8 or not ('+91' in result.get('formatted', '') or 
                                                 result.get('formatted', '').startswith('0')):
                        # Only accept if it has a proper full format
                        if not ('+91' in result.get('formatted', '') and len(raw_number) >= 10):
                            self.logger.debug(f"Rejecting short landline without proper area code: {phone}")
                            return None
            
            return result
        except Exception as e:
            self.logger.error(f"Error validating phone {phone}: {e}")
            return None
            
    def make_request(self, url, max_retries=3):
        """
        Make an HTTP request with retry logic and proper headers.
        
        Args:
            url: URL to request
            max_retries: Maximum number of retries on failure
            
        Returns:
            Response object or None if all retries fail
        """
        domain = urlparse(url).netloc
        
        # Apply domain rate limiting
        self._check_domain_rate_limit(domain)
        
        # Track this request
        self._track_domain_access(domain)
        
        session = self.get_request_session()
        
        # Random user agent for each request
        headers = {
            'User-Agent': self.get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'TE': 'Trailers',
            'DNT': '1'
        }
        
        # Add Indian-specific headers for better results
        if self.is_indian_domain(url):
            headers['Accept-Language'] = 'en-IN,en-US;q=0.9,en;q=0.8,hi;q=0.7'
        
        # Apply random delay for more human-like behavior
        time.sleep(random.uniform(1, 3))
        
        # Try with each proxy until success or max retries
        for retry in range(max_retries):
            try:
                # Get proxy for this request
                proxy = self.get_random_proxy() if retry > 0 else None
                
                # Make the request with a reasonable timeout
                response = session.get(
                    url,
                    headers=headers,
                    proxies=proxy,
                    timeout=30,
                    allow_redirects=True
                )
                
                # Check for successful response
                if response.status_code == 200:
                    # Record successful access
                    self.rate_limiter.record_success(domain)
                    return response
                    
                # Check for common error codes
                if response.status_code == 404:
                    self.logger.warning(f"404 Not Found: {url}")
                    self.rate_limiter.record_error(domain, response.status_code)
                    return None
                    
                if response.status_code == 403:
                    self.logger.warning(f"403 Forbidden: {url}")
                    self.rate_limiter.record_error(domain, response.status_code)
                    
                    # Try with a different proxy on next attempt
                    continue
                    
                if response.status_code == 429:
                    self.logger.warning(f"429 Too Many Requests: {url}")
                    self.rate_limiter.record_error(domain, response.status_code)
                    
                    # Add longer delay before retry
                    time.sleep(random.uniform(5, 10))
                    continue
                    
                # For other status codes, just retry
                self.logger.warning(f"HTTP {response.status_code}: {url}")
                self.rate_limiter.record_error(domain, response.status_code)
                
            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout requesting {url}")
                self.rate_limiter.record_error(domain)
                
            except requests.exceptions.ConnectionError:
                self.logger.warning(f"Connection error requesting {url}")
                self.rate_limiter.record_error(domain)
                
            except Exception as e:
                self.logger.error(f"Error requesting {url}: {e}")
                self.rate_limiter.record_error(domain)
                
            # Wait before retry with increasing backoff
            wait_time = (retry + 1) * random.uniform(2, 5)
            time.sleep(wait_time)
            
        self.logger.error(f"Failed to retrieve {url} after {max_retries} retries")
        return None
        
    def get_random_user_agent(self):
        """Get a random user agent string."""
        if hasattr(self, 'ua') and self.ua:
            try:
                return self.ua.random
            except Exception:
                pass
                
        # Fallback to our predefined list
        return random.choice(self.user_agents)
        
    def get_random_proxy(self):
        """Get a random proxy from our list."""
        if not self.proxy_list:
            return None
            
        return random.choice(self.proxy_list)

    async def close_browser(self):
        """Close browser resources and clean up."""
        if hasattr(self, 'browser_initialized') and self.browser_initialized:
            try:
                await self._cleanup_browser_resources()
                self.logger.info("Browser resources closed successfully")
                return True
            except Exception as e:
                self.logger.error(f"Error closing browser: {e}")
                return False
        return True
        
    def close_browser_sync(self):
        """Synchronous wrapper to close browser resources."""
        if hasattr(self, 'browser_initialized') and self.browser_initialized:
            try:
                loop = get_or_create_event_loop()
                loop.run_until_complete(self.close_browser())
                return True
            except Exception as e:
                self.logger.error(f"Error in synchronous browser close: {e}")
                return False
        return True

    def direct_search(self, keyword: str, num_results: int = 10) -> List[str]:
        """
        Direct search method that bypasses search engines for specific cases.
        This is useful when search engines block our requests.
        
        Args:
            keyword: Search keyword
            num_results: Maximum number of results to return
            
        Returns:
            List of relevant URLs to check
        """
        urls = []
        self.logger.info(f"Performing direct search for '{keyword}'")
        print(f"🔍 Performing direct search for '{keyword}'")
        
        # Parse the keyword to identify key components
        keyword_lower = keyword.lower()
        
        # Check if it's a product search in a specific location
        is_product_search = False
        product_terms = []
        location = None
        
        # Common product keywords
        product_keywords = [
            'bottle', 'container', 'packaging', 'dropper', 'jar', 'vial', 
            'flask', 'manufacturer', 'supplier', 'wholesale', 'producer'
        ]
        
        # Common Indian locations
        india_locations = [
            'delhi', 'mumbai', 'bangalore', 'chennai', 'kolkata', 'hyderabad',
            'ahmedabad', 'pune', 'jaipur', 'surat', 'lucknow', 'kanpur',
            'nagpur', 'indore', 'thane', 'bhopal', 'visakhapatnam', 'india'
        ]
        
        # Check for product terms
        for term in product_keywords:
            if term in keyword_lower:
                is_product_search = True
                product_terms.append(term)
        
        # Check for location
        for loc in india_locations:
            if loc in keyword_lower:
                location = loc
                break
        
        # Build targeted URLs based on the search type
        if is_product_search and location:
            # For product searches in specific locations, use B2B sites and business directories
            
            # Format the search terms for URL inclusion
            product_search = '+'.join(product_terms)
            location_search = location
            
            # If the keyword contains "dropper bottle" specifically, add some known suppliers
            if 'dropper' in keyword_lower and 'bottle' in keyword_lower:
                # These are websites likely to have dropper bottle suppliers
                urls.extend([
                    # Known packaging/bottle suppliers in Delhi
                    "https://www.packagingconnections.com/suppliers/dropper-bottle-delhi",
                    "https://www.glassbottleindia.com/contact-us",
                    "https://www.packagingexpo.in/delhi-exhibitors",
                    "https://www.shreeumiyapackaging.com/contact-us",
                    "https://www.aromapackaging.in/contact-us",
                    "https://www.bottlesindia.com/contact-us",
                    "https://www.acmeplastopack.com/contact-us",
                    "https://www.packingbottles.com/contact",
                    "https://www.nationalbottles.com/contact",
                    "https://www.shaktiplasticinds.com/contact",
                    "https://www.swbpl.com/contact-us",
                    # Generic packaging websites
                    "https://www.easternpkg.com/contact-us",
                    "https://www.jainplasticpack.com/contact-us",
                ])
            
            # Try some direct domain guesses based on the keyword
            keyword_parts = keyword.lower().replace("in", "").replace("delhi", "").strip().split()
            base_keyword = '-'.join([part for part in keyword_parts if len(part) > 2])
            
            # Try some common domain patterns
            if base_keyword:
                urls.extend([
                    f"https://www.{base_keyword}.com",
                    f"https://www.{base_keyword}.in",
                    f"https://www.{base_keyword}-india.com",
                    f"https://{base_keyword}.co.in",
                ])
            
            # Add B2B directories with search queries
            urls.extend([
                f"https://dir.indiamart.com/search.mp?ss={product_search}+{location_search}",
                f"https://yellowpages.indiainfo.com/search?q={product_search}+{location_search}",
                f"https://www.tradeindia.com/search.html?keyword={product_search}+{location_search}",
                f"https://www.exportersindia.com/search.php?term={product_search}+{location_search}",
                f"https://www.indianyellowpages.com/search/?q={product_search}+{location_search}",
            ])
            
            # For Delhi specifically, add some local business directories
            if location == 'delhi':
                urls.extend([
                    f"https://delhi.quikr.com/businesses?query={product_search}",
                    f"https://www.delhitradefairs.com/search?q={product_search}",
                    f"https://www.mydala.com/delhi/search?category={product_search}",
                ])
        
        # Filter for unique URLs
        unique_urls = list(dict.fromkeys(urls))
        
        # Log the direct search results
        self.logger.info(f"Direct search found {len(unique_urls)} URLs for '{keyword}'")
        print(f"✅ Direct search found {len(unique_urls)} URLs to check")
        
        return unique_urls[:num_results]

    def search_google(self, keyword: str, num_results: int = 10, page: int = 0) -> List[str]:
        """
        Search Google for a given keyword and return a list of URLs.
        
        Args:
            keyword: Search query
            num_results: Number of results to return
            page: Result page number (0-based)
            
        Returns:
            List of result URLs
        """
        self.logger.info(f"Searching Google for '{keyword}' (page {page})")
        
        try:
            # Simplify the query if it looks too complex - complex queries trigger more security checks
            simplified_keyword = keyword
            if ('"' in keyword and 'site:' in keyword) or keyword.count('-site:') > 3:
                # Remove site restrictions or reduce them
                if 'site:' in keyword:
                    parts = keyword.split('site:')
                    simplified_keyword = parts[0].strip()
                    self.logger.info(f"Simplified complex query: '{keyword}' -> '{simplified_keyword}'")
                
                # If it has too many exclusions, reduce them
                if keyword.count('-site:') > 3:
                    exclusion_count = 0
                    parts = []
                    for part in keyword.split():
                        if part.startswith('-site:') and exclusion_count >= 3:
                            continue
                        if part.startswith('-site:'):
                            exclusion_count += 1
                        parts.append(part)
                    simplified_keyword = ' '.join(parts)
                    self.logger.info(f"Reduced exclusions in query: '{keyword}' -> '{simplified_keyword}'")
            
            # First try with browser-based search (most reliable)
            browser_results = []
            if self.use_browser and hasattr(self, 'browser_initialized') and self.browser_initialized:
                try:
                    self.logger.info(f"Attempting browser-based Google search for '{simplified_keyword}'")
                    
                    # Use the event loop
                    loop = get_or_create_event_loop()
                    
                    # Run async search with browser
                    browser_results = loop.run_until_complete(
                        self._search_google_with_browser(simplified_keyword, num_results, page)
                    )
                    
                    if browser_results:
                        self.logger.info(f"Browser-based search found {len(browser_results)} results")
                        # Filter out unwanted domains and normalize URLs
                        filtered_results = self._filter_search_results(browser_results)
                        return filtered_results
                    else:
                        self.logger.warning("Browser-based search returned no results")
                except Exception as e:
                    self.logger.error(f"Error in browser-based search: {e}")
                    # Continue to fallback methods
            
            # Fallback to imported browser_search_google function
            try:
                self.logger.info(f"Trying imported browser search function for '{simplified_keyword}'")
                results = browser_search_google(simplified_keyword, num_results=num_results, page=page, debug_mode=self.debug_mode)
                
                if results:
                    self.logger.info(f"Imported browser search found {len(results)} results")
                    # Filter and return results
                    filtered_results = self._filter_search_results(results)
                    return filtered_results
            except Exception as e:
                self.logger.error(f"Error using imported browser search: {e}")
                # Continue to next fallback
            
            # If Google detected our automation, try DuckDuckGo as fallback
            self.logger.info(f"Trying DuckDuckGo as fallback for '{simplified_keyword}'")
            print(f"⚠️ Google search methods failed. Trying DuckDuckGo as fallback...")
            
            # Try DuckDuckGo search
            ddg_results = self.search_duckduckgo(simplified_keyword, num_results=num_results)
            if ddg_results:
                self.logger.info(f"Successfully found {len(ddg_results)} results from DuckDuckGo")
                print(f"✅ Found {len(ddg_results)} results from DuckDuckGo")
                filtered_results = self._filter_search_results(ddg_results)
                return filtered_results
            
            # If still no results, try direct search as a last resort
            if not ddg_results:
                self.logger.info(f"Trying direct search as last resort for '{keyword}'")
                print(f"⚠️ All search methods failed. Trying direct search...")
                direct_results = self.direct_search(keyword, num_results=num_results)
                if direct_results:
                    self.logger.info(f"Direct search found {len(direct_results)} results")
                    print(f"✅ Found {len(direct_results)} results via direct search")
                    return direct_results
            
            # Log failure if we reach here
            self.logger.warning(f"All search methods failed for '{keyword}'")
            return []
            
        except Exception as e:
            self.logger.error(f"Error searching Google: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []
    
    def _filter_search_results(self, urls: List[str]) -> List[str]:
        """
        Filter search results to remove duplicates and excluded domains.
        
        Args:
            urls: List of URLs to filter
            
        Returns:
            List of filtered URLs
        """
        if not urls:
            return []
            
        filtered_urls = []
        seen_domains = set()
        
        for url in urls:
            try:
                # Parse URL to extract domain
                parsed = urlparse(url)
                domain = parsed.netloc.lower()
                
                # Skip if domain is in excluded list
                if any(excluded in domain for excluded in self.excluded_domains):
                    self.logger.debug(f"Skipping excluded domain: {domain}")
                    continue
                
                # Skip common file types that aren't useful for contact scraping
                path = parsed.path.lower()
                if any(path.endswith(ext) for ext in self.excluded_file_extensions):
                    self.logger.debug(f"Skipping file: {path}")
                    continue
                
                # Limit to 2 URLs per domain for diversity
                if domain in seen_domains and sum(1 for d in seen_domains if d == domain) >= 2:
                    continue
                    
                # Add domain to seen set
                seen_domains.add(domain)
                
                # Add URL to filtered list
                filtered_urls.append(url)
                
                # Stop if we have enough results
                if len(filtered_urls) >= 20:  # Collect more than needed for better chance of finding contacts
                    break
                    
            except Exception as e:
                self.logger.warning(f"Error filtering URL {url}: {e}")
                continue
                
        return filtered_urls

    def save_results_to_csv(self, keyword: str, emails: Set[str], phones: Set) -> str:
        """
        Save the extracted contact information to a CSV file.
        
        Args:
            keyword: Search keyword
            emails: Set of extracted email addresses
            phones: Set of extracted phone numbers
            
        Returns:
            str: Path to the saved CSV file
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs('scraped_data', exist_ok=True)
            
            # Format the filename with keyword and timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sanitized_keyword = re.sub(r'[\\/*?:"<>|]', "_", keyword)  # Remove invalid filename chars
            filename = f"contacts_{sanitized_keyword}_{timestamp}.csv"
            filepath = os.path.join('scraped_data', filename)
            
            # Write the CSV file
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(['Type', 'Value', 'Keyword'])
                
                # Write emails
                for email in sorted(emails):
                    writer.writerow(['Email', email, keyword])
                    
                # Write phones
                for phone in sorted(phones):
                    if isinstance(phone, dict):
                        phone_value = phone.get('formatted', str(phone))
                    else:
                        phone_value = str(phone)
                    writer.writerow(['Phone', phone_value, keyword])
                    
            self.logger.info(f"Results saved to {filepath}")
            print(f"✅ Results saved to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving results to CSV: {e}")
            print(f"❌ Error saving results: {e}")
            return ""
            
    def save_detailed_results_to_csv(self, keyword: str, results_by_url: List[Dict]) -> str:
        """
        Save detailed results including source URLs to a CSV file.
        
        Args:
            keyword: Search keyword
            results_by_url: List of dictionaries with results per URL
            
        Returns:
            str: Path to the saved CSV file
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs('scraped_data', exist_ok=True)
            
            # Format the filename with keyword and timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            sanitized_keyword = re.sub(r'[\\/*?:"<>|]', "_", keyword)  # Remove invalid filename chars
            filename = f"detailed_{sanitized_keyword}_{timestamp}.csv"
            filepath = os.path.join('scraped_data', filename)
            
            # Write the CSV file
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Write header
                writer.writerow(['Type', 'Value', 'Source URL', 'Domain', 'Keyword'])
                
                # Write each result with its source URL
                for result in results_by_url:
                    url = result.get('url', '')
                    domain = result.get('domain', '')
                    
                    # Write emails for this URL
                    for email in result.get('emails', []):
                        writer.writerow(['Email', email, url, domain, keyword])
                        
                    # Write phones for this URL
                    for phone in result.get('phones', []):
                        if isinstance(phone, dict):
                            # Check for different possible keys in the phone dictionary
                            if 'formatted' in phone:
                                phone_value = phone['formatted']
                            elif 'phone' in phone:
                                phone_value = phone['phone']
                            else:
                                phone_value = str(phone)
                        else:
                            phone_value = str(phone)
                        writer.writerow(['Phone', phone_value, url, domain, keyword])
                    
            self.logger.info(f"Detailed results saved to {filepath}")
            print(f"✅ Detailed results saved to {filepath}")
            return filepath
            
        except Exception as e:
            self.logger.error(f"Error saving detailed results to CSV: {e}")
            print(f"❌ Error saving detailed results: {e}")
            return ""

    def optimize_search_query_with_gemini(self, keyword: str, optimization_type: str = "contact_info") -> str:
        """
        Use Google's Gemini API to optimize search queries for better contact information extraction.
        This version focuses on creating effective but simpler queries to avoid triggering security checks.
        
        Args:
            keyword (str): The original search keyword or business name
            optimization_type (str): Type of optimization - "contact_info", "email_focus", "phone_focus"
            
        Returns:
            str: Optimized search query designed for better extraction results
        """
        if not self.gemini_api_key or not self.gemini_model:
            self.logger.warning("Gemini API not available for query optimization. Using fallback method.")
            return self._fallback_optimize_query(keyword)
            
        try:
            # Limit exclusions to just a few to avoid complex queries that trigger security checks
            exclusion_string = ' '.join([f'-site:{site}' for site in self.search_excluded_sites[:3]])
            
            # Different prompts based on optimization type, but with instructions to keep queries simple
            prompts = {
                "contact_info": f"""
                    Create a simple and effective Google search query to find contact information for "{keyword}".
                    
                    Important: Create a SIMPLE query that won't trigger Google's security systems.
                    
                    Your query should:
                    1. Use quotation marks around the main keyword
                    2. Include only basic terms like "contact", "email", "phone" 
                    3. Limit to max 3-4 search terms total
                    4. Avoid excessive use of operators like OR, AND, site:
                    5. For Indian businesses, just add "site:.in" at the end
                    
                    Only return the optimized search query without any explanations or formatting.
                    """,
                    
                "email_focus": f"""
                    Create a simple and effective Google search query to find email addresses for "{keyword}".
                    
                    Important: Create a SIMPLE query that won't trigger Google's security systems.
                    
                    Your query should:
                    1. Use quotation marks around the main keyword
                    2. Include only 2-3 terms like "email", "@", "contact"
                    3. Avoid complex operators - just use basic terms
                    4. For Indian businesses, just add "site:.in" at the end
                    
                    Only return the optimized search query without any explanations or formatting.
                    """,
                    
                "phone_focus": f"""
                    Create a simple and effective Google search query to find phone numbers for "{keyword}".
                    
                    Important: Create a SIMPLE query that won't trigger Google's security systems.
                    
                    Your query should:
                    1. Use quotation marks around the main keyword
                    2. Include only 2-3 terms like "phone", "contact", "call"
                    3. Avoid complex operators - just use basic terms
                    4. For Indian businesses, just add "site:.in" at the end
                    
                    Only return the optimized search query without any explanations or formatting.
                    """
            }
            
            # Select appropriate prompt
            prompt = prompts.get(optimization_type, prompts["contact_info"])
            
            # Get response from Gemini
            try:
                response = self.gemini_model.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.1,  # Low temperature for more focused results
                        "top_p": 0.95,
                        "top_k": 40,
                        "max_output_tokens": 300,
                    }
                )
                
                if response and hasattr(response, 'text'):
                    optimized_query = response.text.strip()
                    
                    # Post-process the query
                    # 1. Ensure it's not too long
                    if len(optimized_query) > 150:  # Shorter maximum length
                        optimized_query = optimized_query[:150]
                        
                    # 2. Add exclusions only if the query is relatively simple
                    if '-site:' not in optimized_query and len(optimized_query.split()) < 5:
                        optimized_query += f" {exclusion_string}"
                        
                    # 3. Ensure proper formatting and quotes
                    optimized_query = self._clean_search_query(optimized_query)
                    
                    # 4. Safety check - if query has too many operators, simplify it
                    operator_count = (
                        optimized_query.count('site:') + 
                        optimized_query.count('-site:') + 
                        optimized_query.count('OR') + 
                        optimized_query.count('AND') +
                        optimized_query.count('|') +
                        optimized_query.count('filetype:')
                    )
                    
                    if operator_count > 5:
                        self.logger.warning(f"Query has too many operators ({operator_count}), simplifying")
                        # Fall back to the simpler method
                        return self._fallback_optimize_query(keyword)
                    
                    self.logger.info(f"Gemini optimized query: {optimized_query}")
                    return optimized_query
                else:
                    self.logger.warning("Empty response from Gemini API")
                    return self._fallback_optimize_query(keyword)
            except Exception as gemini_error:
                self.logger.error(f"Error generating content with Gemini: {gemini_error}")
                return self._fallback_optimize_query(keyword)
                
        except Exception as e:
            self.logger.error(f"Error using Gemini API: {e}")
            return self._fallback_optimize_query(keyword)

    def is_indian_domain(self, url_or_keyword: str) -> bool:
        """
        Check if a URL or keyword appears to be related to an Indian domain.
        
        Args:
            url_or_keyword (str): URL or keyword to check
            
        Returns:
            bool: True if appears to be Indian, False otherwise
        """
        if not url_or_keyword:
            return False
            
        # Check for Indian TLDs
        if url_or_keyword.endswith('.in') or '.in/' in url_or_keyword or '.co.in' in url_or_keyword:
            return True
            
        # Check for Indian keywords
        indian_keywords = ['india', 'delhi', 'mumbai', 'bangalore', 'kolkata', 'chennai', 'hyderabad',
                          'ahmedabad', 'pune', 'jaipur', 'lucknow', 'surat', 'kanpur', 'nagpur',
                          'indore', 'bhopal', 'vadodara', 'ghaziabad', 'ludhiana', 'agra', 'nashik',
                          'rajasthan', 'gujarat', 'kerala', 'telangana', 'punjab', 'haryana']
                          
        keyword_lower = url_or_keyword.lower()
        
        for kw in indian_keywords:
            if kw in keyword_lower:
                return True
                
        return False

    def _extract_from_attributes(self, soup, domain):
        """Extract contact information from HTML element attributes."""
        try:
            emails = set()
            phones = set()
            
            # Extract from href attributes
            for link in soup.find_all('a', href=True):
                href = link.get('href', '')
                # Email extraction
                if href.startswith('mailto:'):
                    email = href[7:].split('?')[0].strip()
                    if self._validate_email(email):
                        emails.add(email)
                        
                # Phone extraction
                elif href.startswith('tel:'):
                    phone_text = href[4:].strip()
                    validated_phones = self._extract_phones_from_text(phone_text, source=f"{domain}_tel_link")
                    for phone in validated_phones:
                        # Safely handle both string and dictionary phone objects
                        if isinstance(phone, dict):
                            # Add safety check for 'formatted' key
                            if 'phone' in phone:
                                phones.add(phone['phone'])
                            elif 'formatted' in phone:
                                phones.add(phone['formatted'])
                            else:
                                phones.add(str(phone))
                        else:
                            phones.add(phone)
        
            # Extract from other common attributes
            for elem in soup.find_all(attrs={'data-phone': True}):
                phone_text = elem['data-phone'].strip()
                validated_phones = self._extract_phones_from_text(phone_text, source=f"{domain}_data_attr")
                for phone in validated_phones:
                    # Safely handle phone objects
                    if isinstance(phone, dict):
                        if 'phone' in phone:
                            phones.add(phone['phone'])
                        elif 'formatted' in phone:
                            phones.add(phone['formatted'])
                        else:
                            phones.add(str(phone))
                    else:
                        phones.add(phone)
        
            return emails, phones
        except Exception as e:
            self.logger.error(f"Error extracting from HTML attributes: {e}")
            return set(), set()

    def _extract_from_structured_data(self, html_content, domain):
        """Extract contact information from structured data (JSON-LD, microdata)."""
        try:
            emails = set()
            phones = set()
            
            # Extract JSON-LD data
            json_ld_data = extract_json_ld(html_content)
            
            if json_ld_data:
                for item in json_ld_data:
                    # Check for Organization or LocalBusiness schema
                    if '@type' in item and item['@type'] in ['Organization', 'LocalBusiness', 'Store', 'Restaurant', 'Hotel']:
                        # Extract email
                        if 'email' in item:
                            email = item['email']
                            if self._validate_email(email):
                                emails.add(email)
                        
                        # Extract phone
                        if 'telephone' in item:
                            phone_text = item['telephone']
                            validated_phones = self._extract_phones_from_text(phone_text, source=f"{domain}_jsonld_direct")
                            for phone in validated_phones:
                                # Safely handle phone objects
                                if isinstance(phone, dict):
                                    if 'phone' in phone:
                                        phones.add(phone['phone'])
                                    elif 'formatted' in phone:
                                        phones.add(phone['formatted'])
                                    else:
                                        phones.add(str(phone))
                                else:
                                    phones.add(phone)
                
                    # Check for ContactPoint schema
                    if '@type' in item and item['@type'] == 'ContactPoint':
                        if 'telephone' in item:
                            phone_text = item['telephone']
                            validated_phones = self._extract_phones_from_text(phone_text, source=f"{domain}_jsonld_contact")
                            for phone in validated_phones:
                                # Safely handle phone objects
                                if isinstance(phone, dict):
                                    if 'phone' in phone:
                                        phones.add(phone['phone'])
                                    elif 'formatted' in phone:
                                        phones.add(phone['formatted'])
                                    else:
                                        phones.add(str(phone))
                                else:
                                    phones.add(phone)
                
                    # Check for nested ContactPoint
                    if 'contactPoint' in item:
                        contact_point = item['contactPoint']
                        if isinstance(contact_point, dict) and 'telephone' in contact_point:
                            phone_text = contact_point['telephone']
                            validated_phones = self._extract_phones_from_text(phone_text, source=f"{domain}_jsonld_nested")
                            for phone in validated_phones:
                                # Safely handle phone objects
                                if isinstance(phone, dict):
                                    if 'phone' in phone:
                                        phones.add(phone['phone'])
                                    elif 'formatted' in phone:
                                        phones.add(phone['formatted'])
                                    else:
                                        phones.add(str(phone))
                                else:
                                    phones.add(phone)
            
            return emails, phones
        except Exception as e:
            self.logger.error(f"Error extracting from structured data: {e}")
            return set(), set()

    def _extract_from_javascript(self, html_content):
        """Extract contact information from JavaScript code in the HTML."""
        try:
            emails = set()
            phones = set()
            
            # Find all script tags
            script_pattern = re.compile(r'<script[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)
            scripts = script_pattern.findall(html_content)
            
            # Email patterns in JavaScript
            email_patterns = [
                r'[\'"]((?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}))[\'"]',  # Quoted email
                r'email[\'"\s]*[:=][\'"\s]*((?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}))',  # email: "user@example.com"
                r'mail[\'"\s]*[:=][\'"\s]*((?:[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}))',   # mail: "user@example.com"
            ]
            
            # Phone patterns in JavaScript
            phone_patterns = [
                r'[\'"]((?:\+\d{1,3}[\s.-]?)?\(?\d{3,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4})[\'"]',  # Quoted phone
                r'phone[\'"\s]*[:=][\'"\s]*((?:\+\d{1,3}[\s.-]?)?\(?\d{3,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4})',  # phone: "1234567890"
                r'mobile[\'"\s]*[:=][\'"\s]*((?:\+\d{1,3}[\s.-]?)?\(?\d{3,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4})',  # mobile: "1234567890"
                r'tel[\'"\s]*[:=][\'"\s]*((?:\+\d{1,3}[\s.-]?)?\(?\d{3,4}\)?[\s.-]?\d{3,4}[\s.-]?\d{3,4})',     # tel: "1234567890"
            ]
            
            # Extract emails and phones from scripts
            for script in scripts:
                # Skip very large scripts to avoid processing analytics or libraries
                if len(script) > 50000:
                    continue
                
                # Extract emails
                for pattern in email_patterns:
                    email_matches = re.findall(pattern, script)
                    for email in email_matches:
                        if self._validate_email(email):
                            emails.add(email)
                
                # Extract phones
                for pattern in phone_patterns:
                    phone_matches = re.findall(pattern, script)
                    for phone_text in phone_matches:
                        validated_phones = self._extract_phones_from_text(phone_text, source="javascript")
                        for phone in validated_phones:
                            # Safely handle phone objects
                            if isinstance(phone, dict):
                                if 'phone' in phone:
                                    phones.add(phone['phone'])
                                elif 'formatted' in phone:
                                    phones.add(phone['formatted'])
                                else:
                                    phones.add(str(phone))
                            else:
                                phones.add(phone)
            
            return emails, phones
        except Exception as e:
            self.logger.error(f"Error extracting from JavaScript: {e}")
            return set(), set()

    def _extract_obfuscated_emails(self, html_content):
        """
        Extract obfuscated email addresses from HTML content.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            set: Set of validated email addresses
        """
        emails = set()
        
        try:
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 1. Look for HTML entity encoded emails
            # First decode all HTML entities
            decoded_html = self._decode_html_entities(html_content)
            
            # Then find emails in the decoded content
            if decoded_html != html_content:
                soup_decoded = BeautifulSoup(decoded_html, 'html.parser')
                text_decoded = soup_decoded.get_text()
                email_matches = self.email_pattern.findall(text_decoded)
                
                for email in email_matches:
                    if self._validate_email(email):
                        emails.add(email.lower())
            
            # 2. Look for emails split across multiple elements
            # This is a common obfuscation technique where each character or segment is in a separate element
            
            # Find elements that might contain email parts
            potential_containers = soup.select('span, div, p, li, a')
            
            for container in potential_containers:
                # Check if the container or its children contain the @ symbol or common email segments
                container_text = container.get_text()
                
                if '@' in container_text or (' at ' in container_text.lower()) or (' dot ' in container_text.lower()):
                    # Get all child elements and their text
                    parts = []
                    for elem in container.find_all(text=True):
                        part = elem.strip()
                        if part:
                            parts.append(part)
                    
                    # Join all text parts and look for email patterns
                    full_text = ''.join(parts)
                    
                    # Look for emails in the combined text
                    email_matches = self.email_pattern.findall(full_text)
                    for email in email_matches:
                        if self._validate_email(email):
                            emails.add(email.lower())
                    
                    # Also look for "at" and "dot" text replacements
                    at_dot_pattern = re.compile(r'([a-zA-Z0-9._%+-]+)\s*(?:at|@|\[@\]|&#64;)\s*([a-zA-Z0-9.-]+)\s*(?:dot|\.)\s*([a-zA-Z]{2,})')
                    at_dot_matches = at_dot_pattern.findall(full_text)
                    
                    for match in at_dot_matches:
                        if len(match) == 3:
                            email = f"{match[0]}@{match[1]}.{match[2]}"
                            if self._validate_email(email):
                                emails.add(email.lower())
            
            # 3. Look for CSS unicode-escape or direction tricks
            # Some obfuscation uses CSS unicode-escape or direction changes to hide email addresses
            
            # Check style attributes for unicode-escape patterns
            elements_with_style = soup.select('[style*="unicode"]')
            for elem in elements_with_style:
                style = elem.get('style', '')
                if 'unicode' in style:
                    # Get the text content and check for emails
                    text = elem.get_text()
                    email_matches = self.email_pattern.findall(text)
                    for email in email_matches:
                        if self._validate_email(email):
                            emails.add(email.lower())
            
            return emails
            
        except Exception as e:
            self.logger.error(f"Error extracting obfuscated emails: {e}")
            return set()
    
    def _decode_html_entities(self, text):
        """
        Decode HTML entities in text.
        
        Args:
            text: Text to decode
            
        Returns:
            str: Decoded text
        """
        try:
            # Replace common email encoding patterns
            text = text.replace('&#64;', '@')
            text = text.replace('&#46;', '.')
            text = text.replace('&amp;', '&')
            
            # Use HTML parser to decode entities
            decoded = BeautifulSoup(text, 'html.parser').get_text()
            return decoded
        except Exception as e:
            self.logger.error(f"Error decoding HTML entities: {e}")
            return text

    # If there's a search_duckduckgo method, add a comment that it's disabled
    def search_duckduckgo(self, keyword: str, num_results: int = 10) -> List[str]:
        """
        DISABLED: This search method has been disabled.
        
        Args:
            keyword (str): Search keyword
            num_results (int): Maximum number of results to return
            
        Returns:
            List[str]: Empty list (method disabled)
        """
        self.logger.info("DuckDuckGo search method has been disabled")
        print("⚠️ DuckDuckGo search method has been disabled by administrator")
        return []

    async def _search_google_with_browser(self, keyword: str, num_results: int = 10, page: int = 0) -> List[str]:
        """
        Use browser automation to search Google with enhanced anti-detection measures.
        
        Args:
            keyword: Search query
            num_results: Number of results to return
            page: Result page number (0-based)
            
        Returns:
            List of result URLs
        """
        if not self.use_browser or not self.browser_initialized:
            self.logger.warning("Browser not initialized for Google search")
            return []
            
        urls = []
        try:
            # Ensure browser is initialized
            if not self.browser_initialized:
                await self.initialize_browser()
                
            # Calculate the start parameter for pagination
            start_param = page * 10
            
            # Build the search URL with randomized parameters to appear more natural
            search_params = {
                'q': keyword,
                'start': start_param if page > 0 else None,
                'num': min(num_results, 100),  # Google's maximum is 100
                'hl': random.choice(['en-US', 'en-IN', 'en-GB', 'en']),  # Randomize language
                'gl': random.choice(['in', 'us', 'uk']),  # Randomize geolocation
                'pws': random.choice(['0', '1']),  # Randomize personalized results
                'client': random.choice(['firefox-b-d', 'chrome', '']),  # Mimic different browsers
                'source': 'hp',
                'ei': ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_', k=16)),
                'oq': keyword,
                'gs_lcp': ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789', k=60))
            }
            
            # Clean up None values
            search_params = {k: v for k, v in search_params.items() if v is not None}
            
            # Construct query string
            query_string = '&'.join([f"{k}={quote(str(v))}" for k, v in search_params.items()])
            search_url = f"https://www.google.com/search?{query_string}"
            
            self.logger.info(f"Browser searching Google: {search_url}")
            
            # Navigate to the search URL with better timeout handling
            try:
                await self.page.goto(search_url, timeout=30000)
                
                # Wait for search results to load with multiple fallback selectors
                result_selectors = [
                    'div.g', 'div.tF2Cxc', 'div.yuRUbf', 
                    'h3.LC20lb', 'div[data-header-feature="0"]',
                    'div[jscontroller]', '.v7W49e'
                ]
                
                # Try each selector until one works
                found_selector = False
                for selector in result_selectors:
                    try:
                        await self.page.wait_for_selector(selector, timeout=5000)
                        found_selector = True
                        self.logger.info(f"Found results with selector: {selector}")
                        break
                    except Exception:
                        continue
                        
                if not found_selector:
                    self.logger.warning("Could not find result elements with known selectors")
                    
                # Add random delays and scrolling to mimic human behavior
                await self._simulate_human_browsing()
                
                # Wait for network to be idle to ensure all content is loaded
                try:
                    await self.page.wait_for_load_state('networkidle', timeout=5000)
                except Exception:
                    self.logger.info("Network idle timeout, continuing anyway")
                
                # Check for CAPTCHA or other security challenges
                if await self._detect_google_security_challenge():
                    self.logger.warning("Detected Google security challenge/CAPTCHA")
                    return []
                
                # Extract search result URLs with multiple approaches for redundancy
                urls = await self._extract_google_search_results()
                
                if not urls:
                    self.logger.warning("First extraction method found no URLs, trying alternate method")
                    # Try alternate extraction method
                    urls = await self._extract_google_results_alternate()
                
                # Limit results to requested number
                urls = urls[:num_results]
                
                self.logger.info(f"Browser Google search found {len(urls)} URLs")
                
                # Only extract contact information if specifically requested
                return urls
                
            except PlaywrightTimeoutError:
                self.logger.warning(f"Timeout loading Google search results for '{keyword}'")
                return []
                
        except Exception as e:
            self.logger.error(f"Error in browser Google search: {e}")
            return []
            
    async def _extract_google_search_results(self) -> List[str]:
        """Extract search result URLs from Google search page with improved resilience."""
        urls = []
        try:
            # Try multiple approaches to extract URLs
            
            # Approach 1: Use JavaScript to extract all search result links
            js_urls = await self.page.evaluate("""
                () => {
                    const links = [];
                    // Selector for main search results (handles multiple possible layouts)
                    const searchResultElements = document.querySelectorAll('div.g div.yuRUbf > a, div.tF2Cxc > div.yuRUbf > a, .v7W49e a, .DhN8Cf a, .g a');
                    
                    for (const element of searchResultElements) {
                        const href = element.href;
                        if (href && 
                            !href.includes('google.com/') && 
                            !href.includes('/search?') && 
                            !href.includes('webcache.googleusercontent') &&
                            !href.includes('translate.google')) {
                            links.push(href);
                        }
                    }
                    return links;
                }
            """)
            
            if js_urls and len(js_urls) > 0:
                urls.extend(js_urls)
                
            # Approach 2: Use Playwright's selector API as backup
            if len(urls) == 0:
                # Try with CSS selectors
                selectors = [
                    'div.g div.yuRUbf > a', 
                    'div.tF2Cxc > div.yuRUbf > a',
                    '.v7W49e a[href*="http"]',
                    '.DhN8Cf a[href*="http"]',
                    '.g a[href*="http"]',
                    'div[jscontroller] a[jsname]'
                ]
                
                for selector in selectors:
                    links = await self.page.query_selector_all(selector)
                    for link in links:
                        try:
                            href = await link.get_attribute('href')
                            if href and not any(x in href for x in [
                                'google.com/', '/search?', 'webcache.googleusercontent', 'translate.google'
                            ]):
                                urls.append(href)
                        except Exception:
                            continue
                
            # De-duplicate URLs while preserving order
            seen = set()
            unique_urls = []
            for url in urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
                    
            return unique_urls
                
        except Exception as e:
            self.logger.error(f"Error extracting Google search results: {e}")
            return urls
            
    async def _extract_google_results_alternate(self) -> List[str]:
        """Alternate method to extract Google search results using more direct DOM parsing."""
        urls = []
        try:
            # Get the page content and parse with BeautifulSoup
            content = await self.page.content()
            soup = BeautifulSoup(content, 'html.parser')
            
            # Try multiple selectors and approaches
            
            # 1. Look for standard result links
            for a_tag in soup.select('a[href^="http"]'):
                href = a_tag.get('href', '')
                
                # Filter out Google's internal links
                if (href.startswith('http') and 
                    not 'google.com/' in href and 
                    not '/search?' in href and
                    not 'accounts.google' in href):
                    urls.append(href)
            
            # 2. Look specifically for search result patterns
            for h3_tag in soup.find_all('h3'):
                # Search result titles are often in h3 tags
                parent = h3_tag.parent
                while parent and parent.name != 'a' and parent.name != 'body':
                    parent = parent.parent
                
                if parent and parent.name == 'a' and 'href' in parent.attrs:
                    href = parent['href']
                    if (href.startswith('http') and 
                        not 'google.com/' in href and 
                        not '/search?' in href):
                        urls.append(href)
            
            # De-duplicate while preserving order
            seen = set()
            unique_urls = []
            for url in urls:
                if url not in seen:
                    seen.add(url)
                    unique_urls.append(url)
                    
            return unique_urls
            
        except Exception as e:
            self.logger.error(f"Error in alternate Google results extraction: {e}")
            return []
            
    async def _detect_google_security_challenge(self) -> bool:
        """Detect if Google is showing a security challenge or CAPTCHA."""
        try:
            # Check for common CAPTCHA and security check indicators
            security_indicators = [
                # Text indicators
                'unusual traffic', 'automated queries', 'verify you are a human',
                'solve this puzzle', 'confirm you are not a robot', 'security check',
                'please show you are not a robot', 'captcha', 'recaptcha',
                
                # URL indicators
                'google.com/sorry', 'accounts.google.com/ServiceLogin',
                
                # Element indicators
                'input[name="g-recaptcha-response"]', 'iframe[src*="recaptcha"]',
                'div[data-sitekey]', 'div.g-recaptcha', 'form#captcha-form'
            ]
            
            # Check page URL
            current_url = self.page.url
            if 'google.com/sorry' in current_url or 'accounts.google.com/ServiceLogin' in current_url:
                self.logger.warning(f"Detected Google security page: {current_url}")
                return True
            
            # Check page content
            content = await self.page.content()
            content_lower = content.lower()
            
            # Check for text indicators
            for indicator in security_indicators[:9]:  # Text indicators
                if indicator.lower() in content_lower:
                    self.logger.warning(f"Detected Google security challenge: '{indicator}'")
                    return True
            
            # Check for element indicators
            for selector in security_indicators[9:]:  # Element indicators
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        self.logger.warning(f"Detected Google security element: {selector}")
                        return True
                except Exception:
                    continue
            
            # Check if no search results are present but page loaded
            result_elements = await self.page.query_selector_all('div.g, div.tF2Cxc, div.yuRUbf, h3.LC20lb')
            if len(result_elements) == 0 and 'google.com/search' in current_url:
                # Take a screenshot for debugging if debug mode is on
                if self.debug_mode:
                    try:
                        screenshot_dir = os.path.join('scraper_logs', 'screenshots')
                        os.makedirs(screenshot_dir, exist_ok=True)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        screenshot_path = os.path.join(screenshot_dir, f"google_no_results_{timestamp}.png")
                        await self.page.screenshot(path=screenshot_path)
                        self.logger.info(f"Saved screenshot to {screenshot_path}")
                    except Exception as e:
                        self.logger.error(f"Failed to save screenshot: {e}")
                
                self.logger.warning("No search results found on Google search page")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"Error detecting Google security challenge: {e}")
            return False

    async def _maybe_interact_with_content(self, page):
        """Sometimes interact with page content in a human-like way."""
        try:
            # Find a safe area to interact with (avoid links and inputs)
            safe_element = await page.evaluate("""
                () => {
                    // Look for content elements that are safe to interact with
                    const contentSelectors = [
                        'p', '.content', 'article', 'section', '.text', 
                        'h1', 'h2', 'h3', '.about', '.description'
                    ];
                    
                    // Try each selector
                    for (const selector of contentSelectors) {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length === 0) continue;
                        
                        // Filter for visible, non-interactive elements
                        const safeElements = Array.from(elements).filter(el => {
                            // Skip if too small
                            if (el.offsetWidth < 20 || el.offsetHeight < 20) return false;
                            
                            // Skip if not visible
                            const rect = el.getBoundingClientRect();
                            if (rect.top < 0 || rect.left < 0 || 
                                rect.bottom > window.innerHeight || 
                                rect.right > window.innerWidth) return false;
                                
                            // Skip if clickable or inside form
                            let node = el;
                            while (node) {
                                if (node.tagName === 'A' || node.tagName === 'BUTTON' || 
                                    node.tagName === 'INPUT' || node.tagName === 'FORM' ||
                                    node.onclick) {
                                    return false;
                                }
                                node = node.parentElement;
                            }
                            
                            return true;
                        });
                        
                        if (safeElements.length > 0) {
                            // Pick one randomly
                            const element = safeElements[Math.floor(Math.random() * safeElements.length)];
                            const rect = element.getBoundingClientRect();
                            
                            // Return coordinates within this element
                            return {
                                x: rect.left + rect.width * Math.random(),
                                y: rect.top + rect.height * Math.random(),
                                text: element.textContent.trim().substring(0, 50)
                            };
                        }
                    }
                    return null;
                }
            """)
            
            if safe_element:
                # Log what we're interacting with
                self.logger.debug(f"Interacting with content: {safe_element.get('text', '')}...")
                
                # Move to the element with natural motion
                await page.mouse.move(
                    safe_element['x'], 
                    safe_element['y'],
                    steps=random.randint(3, 5)
                )
                await asyncio.sleep(random.uniform(0.1, 0.3))
                
                # Randomly choose between different interactions
                interaction = random.choice(['click', 'double_click', 'hover', 'select_text'])
                
                if interaction == 'click':
                    # Simple click
                    await page.mouse.down()
                    await asyncio.sleep(random.uniform(0.05, 0.1))
                    await page.mouse.up()
                elif interaction == 'double_click':
                    # Double click
                    await page.mouse.down()
                    await asyncio.sleep(random.uniform(0.05, 0.1))
                    await page.mouse.up()
                    await asyncio.sleep(random.uniform(0.08, 0.12))
                    await page.mouse.down()
                    await asyncio.sleep(random.uniform(0.05, 0.1))
                    await page.mouse.up()
                elif interaction == 'hover':
                    # Just hover for a moment
                    await asyncio.sleep(random.uniform(0.5, 1.0))
                elif interaction == 'select_text':
                    # Try to select some text
                    await page.mouse.down()
                    
                    # Move a short distance to select text
                    move_x = safe_element['x'] + random.randint(10, 50)
                    move_y = safe_element['y']
                    await page.mouse.move(move_x, move_y, steps=2)
                    
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    await page.mouse.up()
                
                # Pause after interaction
                await asyncio.sleep(random.uniform(0.3, 0.7))
                
        except Exception as e:
            # Don't log the full exception as this is non-critical
            self.logger.debug(f"Error during content interaction: {e}")
            # Continue execution - interaction is optional

# Function for Celery to call
def run_web_scraper_task(keyword, num_results=50, max_runtime_minutes=15, task_id=None, task_record=None, use_browser=True, *args, **kwargs):
    """
    Function to be called by Celery for running the scraper as a background task.
    
    Args:
        keyword: Search keyword
        num_results: Number of results to find
        max_runtime_minutes: Maximum runtime in minutes
        task_id: Task ID for tracking
        task_record: Database record object
        use_browser: Whether to use browser automation
        
    Returns:
        Dict with scraping results and task information
    """
    # Set up logging to file
    try:
        # Create a new scraper instance
        if args.api_mode:
            print(f"update BackgroundTask record")
    except Exception as e:
        print(f"Error updating BackgroundTask record: {e}")
    
    



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
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        
        for script in json_ld_scripts:
            try:
                # Get the script content
                json_text = script.string
                if not json_text:
                    continue
                    
                # Parse the JSON
                data = json.loads(json_text)
                
                # Handle case where the JSON-LD is a list
                if isinstance(data, list):
                    results.extend(data)
                # Handle case where the JSON-LD is a single object
                else:
                    results.append(data)
            except json.JSONDecodeError:
                continue
            except Exception:
                continue
    except Exception:
        pass
        
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
                    
                    // Create fake plugins array
                    const makePluginsArray = () => {
                        const plugins = [
                            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: 'Portable Document Format' },
                            { name: 'Native Client', filename: 'internal-nacl-plugin', description: 'Native Client Executable' }
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
                    
                    // Randomize hardware concurrency
                    const originalHardwareConcurrency = navigator.hardwareConcurrency;
                    Object.defineProperty(navigator, 'hardwareConcurrency', {
                        get: () => Math.min(originalHardwareConcurrency || 4, 8)
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
                })();
            """)
            
            # Set user agent with improved consistency
            user_agent = self.get_random_user_agent()
            
            # Set headers that better mimic real browsers
            await page.set_extra_http_headers({
                'User-Agent': user_agent,
                'Accept-Language': 'en-IN,en-US;q=0.9,en;q=0.8,hi;q=0.7',
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
                'Sec-CH-UA-Platform': '"Windows"'
            })
            
            # Improved human-like behavior simulation
            await self._simulate_human_browsing(page)
            
            return True
        except Exception as e:
            self.logger.error(f"Error applying stealth settings: {e}")
            return False
            
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
            num_points = random.randint(5, 10)
            
            # Generate random curve points
            start_x, start_y = random.randint(0, width), random.randint(0, height)
            points.append((start_x, start_y))
            
            for _ in range(num_points):
                next_x = max(0, min(width, points[-1][0] + random.randint(-300, 300)))
                next_y = max(0, min(height, points[-1][1] + random.randint(-300, 300)))
                points.append((next_x, next_y))
            
            # Move mouse along the curved path
            await page.mouse.move(points[0][0], points[0][1])
            for x, y in points[1:]:
                # Randomize speed for more human-like movement
                delay = random.uniform(0.05, 0.2)
                await page.mouse.move(x, y, steps=random.randint(2, 5))
                await asyncio.sleep(delay)
                
            # Random scrolling behavior
            scroll_count = random.randint(2, 5)
            for _ in range(scroll_count):
                # Random scroll amount
                scroll_amount = random.randint(100, 800)
                
                # Random scroll speed (slower = more human)
                scroll_steps = random.randint(3, 8)
                for step in range(1, scroll_steps + 1):
                    step_amount = scroll_amount * step / scroll_steps
                    await page.evaluate(f"window.scrollTo(0, {step_amount})")
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                
                # Random pause between scrolls
                await asyncio.sleep(random.uniform(0.5, 2.0))
                
            # Sometimes scroll back up (partial)
            if random.random() < 0.4:  # 40% chance
                up_scroll = random.randint(100, 400)
                await page.evaluate(f"window.scrollBy(0, -{up_scroll})")
                await asyncio.sleep(random.uniform(0.3, 1.0))
                
            # Random clicks on non-interactive elements (avoiding links)
            if random.random() < 0.3:  # 30% chance to click
                # Find a safe area to click (avoid links and inputs)
                safe_element = await page.evaluate("""
                    () => {
                        const elements = document.querySelectorAll('div, p, span, section, article');
                        const safeElements = Array.from(elements).filter(el => {
                            // Check if this element or its parents are clickable
                            let node = el;
                            while (node) {
                                if (node.tagName === 'A' || node.tagName === 'BUTTON' || 
                                    node.tagName === 'INPUT' || node.tagName === 'FORM' ||
                                    node.onclick) {
                                    return false;
                                }
                                node = node.parentElement;
                            }
                            
                            // Check if element is visible and has size
                            const rect = el.getBoundingClientRect();
                            return rect.width > 10 && rect.height > 10 && 
                                   rect.top >= 0 && rect.left >= 0 && 
                                   rect.bottom <= window.innerHeight && 
                                   rect.right <= window.innerWidth;
                        });
                        
                        if (safeElements.length === 0) return null;
                        
                        const randomElement = safeElements[Math.floor(Math.random() * safeElements.length)];
                        const rect = randomElement.getBoundingClientRect();
                        
                        return {
                            x: rect.left + rect.width * Math.random(),
                            y: rect.top + rect.height * Math.random()
                        };
                    }
                """)
                
                if safe_element:
                    # Move to the element with natural motion
                    await page.mouse.move(
                        safe_element['x'], 
                        safe_element['y'],
                        steps=random.randint(3, 7)
                    )
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                    # Click with a slight delay as humans would
                    await page.mouse.down()
                    await asyncio.sleep(random.uniform(0.05, 0.15))
                    await page.mouse.up()
                    
                    # Pause after clicking
                    await asyncio.sleep(random.uniform(0.5, 1.5))
                
        except Exception as e:
            self.logger.error(f"Error simulating human browsing: {e}")

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
                            
                            # Minimal scroll to make page more realistic but faster
                            await self.page.evaluate("window.scrollBy(0, 300)")
                            
                            # Look for lazy-loaded content
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
    
    async def _ensure_lazy_content_loaded(self):
        """Ensure lazy-loaded content appears by scrolling and waiting."""
        if not self.page:
            return
            
        try:
            # Get page height
            page_height = await self.page.evaluate("""
                () => Math.max(
                    document.body ? document.body.scrollHeight : 0,
                    document.documentElement ? document.documentElement.scrollHeight : 0
                )
            """)
            
            # Return early if page is very short
            if page_height < 1000:
                return
                
            # Scroll down in steps to trigger lazy loading
            viewport_height = await self.page.evaluate("window.innerHeight")
            scroll_steps = min(3, max(1, page_height // viewport_height))
            
            for i in range(1, scroll_steps + 1):
                # Scroll to position
                position = (page_height * i) // (scroll_steps + 1)
                await self.page.evaluate(f"window.scrollTo(0, {position})")
                
                # Wait briefly for lazy content to load
                await asyncio.sleep(0.5)
                
                # Look for infinite scroll markers
                try:
                    # Check if new content might be loading
                    has_loading_indicator = await self.page.evaluate("""
                        () => {
                            const loaders = document.querySelectorAll('.loading, .spinner, .loader, [class*="loading"], [class*="spinner"], [class*="loader"]');
                            return loaders.length > 0;
                        }
                    """)
                    
                    if has_loading_indicator:
                        # Wait a bit longer for content to load
                        await asyncio.sleep(1)
                except Exception:
                    pass
            
            # Scroll back to top
            await self.page.evaluate("window.scrollTo(0, 0)")
            
        except Exception as e:
            self.logger.warning(f"Error ensuring lazy content loaded: {e}")
    
    def _track_proxy_success(self, success=True, proxy_id=None):
        """Track success/failure of proxy usage for better rotation decisions."""
        if proxy_id is None:
            proxy_id = str(self.current_proxy_index)
            
        if success:
            self.proxy_success_count[proxy_id] = self.proxy_success_count.get(proxy_id, 0) + 1
            self.consecutive_failures = 0
        else:
            self.proxy_failure_count[proxy_id] = self.proxy_failure_count.get(proxy_id, 0) + 1
            self.consecutive_failures += 1
            
        # Calculate success rate for this proxy
        total_requests = (self.proxy_success_count.get(proxy_id, 0) + 
                         self.proxy_failure_count.get(proxy_id, 0))
        success_rate = (self.proxy_success_count.get(proxy_id, 0) / 
                       max(1, total_requests))
        
        # If success rate is too low, mark proxy as bad
        if total_requests >= 5 and success_rate < 0.3:
            self.logger.warning(f"Proxy {proxy_id} has low success rate ({success_rate:.2%}), marking as bad")
            self.bad_proxies.add(proxy_id)
            
    def get_random_proxy(self):
        """Get a random proxy from the available pool."""
        if not self.proxy_list:
            return None
            
        # Filter out bad proxies
        available_proxies = [p for p in self.proxy_list if str(self.proxy_list.index(p)) not in self.bad_proxies]
        
        if not available_proxies:
            self.logger.warning("No good proxies available, resetting proxy list")
            self.bad_proxies.clear()
            available_proxies = self.proxy_list
            
        # Weight proxies by their success rate
        proxy_weights = []
        for proxy in available_proxies:
            proxy_id = str(self.proxy_list.index(proxy))
            success_count = self.proxy_success_count.get(proxy_id, 0)
            failure_count = self.proxy_failure_count.get(proxy_id, 0)
            total_requests = success_count + failure_count
            
            if total_requests == 0:
                weight = 1.0  # Give new proxies a chance
            else:
                success_rate = success_count / total_requests
                weight = success_rate + 0.1  # Add small bias to avoid zero weights
                
            proxy_weights.append(weight)
            
        # Normalize weights
        total_weight = sum(proxy_weights)
        if total_weight > 0:
            proxy_weights = [w/total_weight for w in proxy_weights]
        else:
            proxy_weights = [1.0/len(available_proxies)] * len(available_proxies)
            
        # Select proxy based on weights
        selected_proxy = random.choices(available_proxies, weights=proxy_weights, k=1)[0]
        self.current_proxy_index = self.proxy_list.index(selected_proxy)
        
        return selected_proxy
        
    def make_request(self, url, max_retries=3):
        """Make an HTTP request with retry logic and proxy rotation."""
        # Extract domain for rate limiting
        domain = urlparse(url).netloc
        
        # Skip known blocked domains
        if domain in self.blocked_domains:
            self.logger.warning(f"Skipping known blocked domain: {domain}")
            return None
            
        # Check for CAPTCHA detection
        if domain in self.captcha_detected_domains:
            self.logger.info(f"Domain {domain} previously showed CAPTCHA. Trying with browser.")
            
            # Use browser automation for CAPTCHA domains
            if self.use_browser:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    browser_initialized = loop.run_until_complete(self.initialize_browser())
                    if browser_initialized:
                        return loop.run_until_complete(self.browser_get_page(url, max_retries=1))
                except Exception as e:
                    self.logger.error(f"Browser request failed: {e}")
                finally:
                    loop.close()
            return None
            
        # Check if we've exceeded max requests for this domain
        if self.domain_request_count.get(domain, 0) >= self.max_requests_per_domain:
            self.logger.warning(f"Maximum request limit reached for domain {domain}")
            return None
            
        # Check and enforce rate limiting
        self._check_domain_rate_limit(domain)
        
        # Track this request
        self._track_domain_access(domain)
        
        retries = 0
        headers = self._get_realistic_headers(url)
        
        while retries < max_retries:
            try:
                # Get a proxy for this request
                proxy = self.get_random_proxy()
                
                # Make the request
                response = requests.get(
                    url,
                    headers=headers,
                    proxies=proxy,
                    timeout=30,
                    allow_redirects=True,
                    verify=True
                )
                
                # Record proxy success
                self._track_proxy_success(True, str(self.current_proxy_index))
                
                if response.status_code == 200:
                    # Check for CAPTCHA or bot detection
                    content_lower = response.text.lower()
                    if 'captcha' in content_lower or 'robot' in content_lower or 'automated' in content_lower:
                        self.logger.warning(f"CAPTCHA detected at {url}. Adding to CAPTCHA domains list.")
                        self.captcha_detected_domains.add(domain)
                        
                        # Try browser automation as fallback
                        if self.use_browser and retries >= 1:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                browser_initialized = loop.run_until_complete(self.initialize_browser())
                                if browser_initialized:
                                    return loop.run_until_complete(self.browser_get_page(url, max_retries=1))
                            except Exception as e:
                                self.logger.error(f"Browser fallback request failed: {e}")
                            finally:
                                loop.close()
                        
                        retries += 1
                        time.sleep(random.uniform(1, 3))
                    else:
                        return response
                        
                elif response.status_code == 403 or response.status_code == 429:
                    self.logger.warning(f"Request blocked or rate limited (status {response.status_code}). Rotating proxy and retrying...")
                    
                    # Record proxy failure
                    self._track_proxy_success(False, str(self.current_proxy_index))
                    
                    # Add to blocked domains if consistently getting blocked
                    if retries >= 1:
                        self.blocked_domains.add(domain)
                        
                    # Try browser automation as fallback
                    if retries >= 1 and self.use_browser:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            browser_initialized = loop.run_until_complete(self.initialize_browser())
                            if browser_initialized:
                                return loop.run_until_complete(self.browser_get_page(url, max_retries=1))
                        except Exception as e:
                            self.logger.error(f"Browser fallback request failed: {e}")
                        finally:
                            loop.close()
                        
                    retries += 1
                    time.sleep(random.uniform(1 * (retries + 1), 3 * (retries + 1)))
                    
                else:
                    self.logger.warning(f"Request failed with status code: {response.status_code}")
                    self._track_proxy_success(False, str(self.current_proxy_index))
                    retries += 1
                    time.sleep(random.uniform(1, 2))
                    
            except (requests.exceptions.ProxyError, requests.exceptions.SSLError) as e:
                self.logger.warning(f"Proxy error: {e}. Trying different proxy...")
                self._track_proxy_success(False, str(self.current_proxy_index))
                retries += 1
                time.sleep(random.uniform(0.5, 1))
                
            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout, 
                   requests.exceptions.ReadTimeout, socket.timeout) as e:
                self.logger.warning(f"Connection error: {e}. Retrying...")
                self._track_proxy_success(False, str(self.current_proxy_index))
                retries += 1
                time.sleep(random.uniform(0.5, 1))
                
            except Exception as e:
                self.logger.error(f"Unexpected error: {e}")
                self._track_proxy_success(False, str(self.current_proxy_index))
                retries += 1
                time.sleep(random.uniform(0.5, 1))
        
        # If all retries failed with regular requests, try browser automation
        if self.use_browser:
            self.logger.info(f"All request retries failed for {url}. Trying with browser automation...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                browser_initialized = loop.run_until_complete(self.initialize_browser())
                if browser_initialized:
                    return loop.run_until_complete(self.browser_get_page(url, max_retries=1))
            except Exception as e:
                self.logger.error(f"Final browser fallback failed: {e}")
            finally:
                loop.close()
            
        # If all retries failed, return None
        self.logger.error(f"All retries failed for URL: {url}")
        return None
    
    def _get_realistic_headers(self, url):
        """Generate realistic HTTP headers that vary between requests with improved browser fingerprinting."""
        domain = urlparse(url).netloc
        user_agent = self.get_random_user_agent()
        
        # Browser type detection for consistent headers
        is_chrome = 'Chrome/' in user_agent or 'CriOS/' in user_agent
        is_firefox = 'Firefox/' in user_agent or 'FxiOS/' in user_agent
        is_safari = 'Safari/' in user_agent and not is_chrome and not is_firefox and 'Version/' in user_agent
        is_edge = 'Edg/' in user_agent or 'EdgA/' in user_agent or 'EdgiOS/' in user_agent
        
        # Pick language list appropriate for the browser
        if 'en-IN' in user_agent or 'in' in domain.split('.')[-1]:
            # Indian locale
            accept_language = random.choice([
                'en-IN,en-US;q=0.9,en;q=0.8,hi;q=0.7',
                'en-IN,en;q=0.9,hi;q=0.8',
                'en-US,en;q=0.9,hi;q=0.8',
                'en;q=0.9,hi;q=0.8,en-GB;q=0.7',
                'hi-IN,hi;q=0.9,en;q=0.8'
            ])
        else:
            # Generic English locale
            accept_language = random.choice([
                'en-US,en;q=0.9', 
                'en-GB,en;q=0.9', 
                'en-CA,en;q=0.9',
                'en,en-US;q=0.9,fr;q=0.8'
            ])
            
        # Base headers that most browsers send
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': accept_language,
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': random.choice(['max-age=0', 'no-cache', 'no-store', 'must-revalidate', 'max-age=0, private'])
        }
        
        # Add Sec-* headers which are important for modern browsers
        headers.update({
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        })
        
        # Browser-specific headers
        if is_chrome:
            headers['sec-ch-ua'] = '"Google Chrome";v="111", "Not(A:Brand";v="8", "Chromium";v="111"'
            headers['sec-ch-ua-mobile'] = '?0'
            headers['sec-ch-ua-platform'] = random.choice(['"Windows"', '"macOS"', '"Linux"', '"Android"'])
        elif is_firefox:
            # Firefox doesn't send sec-ch-ua headers
            pass
        elif is_safari:
            # Safari specific behaviors
            headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        elif is_edge:
            headers['sec-ch-ua'] = '"Microsoft Edge";v="111", "Not(A:Brand";v="8", "Chromium";v="111"'
            headers['sec-ch-ua-mobile'] = '?0'
            headers['sec-ch-ua-platform'] = random.choice(['"Windows"', '"macOS"'])
            
        # Sometimes include a referer for requests to look more natural
        if random.random() > 0.3:  # 70% chance to include referer
            # Choose referer based on URL
            if 'google' in domain:
                # For Google, no referer or same-origin referer
                if random.random() > 0.5:
                    headers['Referer'] = f'https://{domain}/'
            elif 'search' in url or 'query' in url or 'q=' in url:
                # For search pages, referer usually comes from a search engine
                referers = [
                    'https://www.google.com/',
                    'https://www.google.co.in/',
                    'https://www.bing.com/',
                    'https://search.yahoo.com/',
                    'https://duckduckgo.com/'
                ]
                headers['Referer'] = random.choice(referers)
            else:
                # For regular pages, referer could be the domain's homepage or search engine
                if random.random() > 0.5:
                    headers['Referer'] = f'https://{domain}/'
                else:
                    headers['Referer'] = random.choice([
                        'https://www.google.com/search?q=',
                        'https://www.google.co.in/search?q=',
                        'https://www.bing.com/search?q='
                    ]) + quote(domain)
                    
        # Add random viewport dimensions for more realism
        resolutions = [
            (1366, 768), (1920, 1080), (1536, 864), (1440, 900),
            (1280, 720), (1600, 900), (2560, 1440), (3840, 2160)
        ]
        if random.random() > 0.5:
            chosen_res = random.choice(resolutions)
            headers['Viewport-Width'] = str(chosen_res[0])
            headers['viewport-width'] = str(chosen_res[0])
        
        # Add Privacy and DNT flags with some randomness
        if random.random() > 0.5:
            headers['DNT'] = '1'
            
        if random.random() > 0.7:
            headers['Sec-GPC'] = '1'  # Global Privacy Control
            
        return headers
    
    def _detect_captcha(self, response):
        """Detect if a response contains a CAPTCHA page."""
        try:
            # Check status code first
            if response.status_code in [429, 403]:
                self.logger.warning(f"CAPTCHA likely - HTTP status {response.status_code}")
                return True
                
            # Check for common CAPTCHA markers in the text
            captcha_indicators = [
                'captcha', 'CAPTCHA', 
                'robot', 'Robot', 
                'unusual traffic', 'unusual activity',
                'automated queries', 'automated requests',
                'verify you are a human', 'not a robot',
                'security check', 'Security Challenge',
                'something about your browser', 'suspicious activity',
                'detected unusual traffic', 'detected automated traffic',
                'verify your identity', 'complete this security check',
                'solve this puzzle', 'reCAPTCHA',
                'suspicious request', 'automated software'
            ]
            
            # Check response text for captcha indicators
            for indicator in captcha_indicators:
                if indicator in response.text:
                    self.logger.warning(f"CAPTCHA detected: '{indicator}' found in response")
                    return True
            
            # Look for specific HTML elements commonly used in CAPTCHA pages
            captcha_elements = [
                'input[name="captcha"]', 
                'iframe[src*="recaptcha"]',
                'iframe[src*="captcha"]',
                'div.g-recaptcha',
                'form#captcha-form',
                'div[id*="captcha"]',
                'div[class*="captcha"]'
            ]
            
            # Parse HTML to check for CAPTCHA elements
            try:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                for element_selector in captcha_elements:
                    selector_type, selector_value = element_selector.split('[')[0], element_selector.split('[')[1].rstrip(']')
                    
                    if selector_type and ']' in element_selector:
                        # CSS selector with attribute
                        attr_name, attr_value = selector_value.split('=')
                        attr_value = attr_value.strip('"*')
                        
                        for elem in soup.find_all(selector_type):
                            if attr_name in elem.attrs and attr_value in elem.attrs[attr_name]:
                                self.logger.warning(f"CAPTCHA element found: {element_selector}")
                                return True
                    elif selector_type and '[' not in element_selector:
                        # Simple element or class selector
                        if '.' in selector_type:
                            elem_type, elem_class = selector_type.split('.')
                            if soup.find(elem_type, class_=elem_class):
                                self.logger.warning(f"CAPTCHA element found: {element_selector}")
                                return True
                        elif '#' in selector_type:
                            elem_type, elem_id = selector_type.split('#')
                            if elem_type:
                                if soup.find(elem_type, id=elem_id):
                                    self.logger.warning(f"CAPTCHA element found: {element_selector}")
                                    return True
                            else:
                                if soup.find(id=elem_id):
                                    self.logger.warning(f"CAPTCHA element found: {element_selector}")
                                    return True
            except Exception as e:
                self.logger.error(f"Error parsing HTML for CAPTCHA detection: {e}")
            
            # No CAPTCHA detected
            return False
        except Exception as e:
            self.logger.error(f"Error in CAPTCHA detection: {e}")
            # If we can't parse the response properly, assume it might be a CAPTCHA
            return True
    
    def search_google(self, keyword: str, num_results: int = 10, page: int = 0) -> List[str]:
        """
        Search Google for a keyword and return a list of URLs
        
        Args:
            keyword (str): Search keyword
            num_results (int): Maximum number of results to return
            page (int): Page number (0-indexed)
            
        Returns:
            List[str]: List of URLs
        """
        self.logger.info(f"Searching Google for '{keyword}' using specialized browser automation")
        
        # Apply domain rate limiting for Google
        self._check_domain_rate_limit('google.com')
        self._track_domain_access('google.com')
        
        # Use the specialized Google browser search module
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Use our improved browser search module that avoids detection
                results = browser_search_google(
                    query=keyword,
                    num_results=num_results,
                    page=page,
                    debug_mode=self.debug_mode
                )
                
                # If we got results, return them
                if results and len(results) > 0:
                    self.logger.info(f"Successfully found {len(results)} Google results for '{keyword}'")
                    return results
                
                # If no results, apply exponential backoff
                backoff_time = (2 ** attempt) * random.uniform(10, 20)
                self.logger.warning(f"No results from browser search for '{keyword}'. Retry {attempt+1}/{max_retries} after {backoff_time:.2f}s")
                time.sleep(backoff_time)
                
            except Exception as e:
                self.logger.error(f"Error using browser search module (attempt {attempt+1}/{max_retries}): {str(e)}")
                
                # Apply exponential backoff
                backoff_time = (2 ** attempt) * random.uniform(15, 25)
                self.logger.info(f"Waiting {backoff_time:.2f}s before retrying browser search")
                time.sleep(backoff_time)
        
        # If all browser search attempts failed, try fallback method
        self.logger.warning(f"All specialized browser search attempts failed for '{keyword}'")
        
        # Fall back to the built-in browser search
        return self._fallback_to_browser_search(keyword, num_results, page)

    def _fallback_to_browser_search(self, keyword: str, num_results: int, page: int) -> List[str]:
        """
        Fallback to browser-based search when HTTP search fails
        
        Args:
            keyword (str): Search keyword
            num_results (int): Number of results to fetch
            page (int): Page number
            
        Returns:
            List[str]: Search result URLs
        """
        logging.info(f"Using fallback browser-based search for: {keyword}")
        
        try:
            # First try the older built-in browser method
            # Create a new event loop if needed
            loop = get_or_create_event_loop()
            
            # Run the browser search
            search_results = loop.run_until_complete(
                self._search_google_with_browser(keyword, num_results, page)
            )
            
            if search_results:
                logging.info(f"Built-in browser search succeeded with {len(search_results)} results")
                return search_results
            
            # If that fails, try one last attempt with the specialized module but with increased delays
            try:
                from data_miner.google_browser_search import search_google as browser_search_google
                
                logging.info("Trying specialized browser search one last time with extra delays")
                
                # Add an extended delay before last attempt to reset any rate limiting
                extended_delay = random.uniform(30, 60)
                logging.info(f"Adding extended delay of {extended_delay:.2f}s before final attempt")
                time.sleep(extended_delay)
                
                # Try one last time with increased debug
                results = browser_search_google(
                    query=keyword,
                    num_results=num_results,
                    page=page,
                    debug_mode=True  # Force debug mode on for last attempt
                )
                
                if results:
                    logging.info(f"Final specialized browser search succeeded with {len(results)} results")
                    return results
                    
            except Exception as e:
                logging.error(f"Final specialized browser search also failed: {e}")
                
        except Exception as e:
            logging.error(f"Browser fallback search failed: {e}")
            logging.error(traceback.format_exc())
        
        # Return empty list if all methods fail
        return []

    async def _search_google_with_browser(self, keyword: str, num_results: int = 10, page_num: int = 0) -> List[str]:
        """
        Search Google using a browser (Playwright) to bypass bot detection
        
        Args:
            keyword (str): Search keyword
            num_results (int): Maximum number of results to return
            page_num (int): Page number (0-indexed)
            
        Returns:
            List[str]: List of URLs
        """
        # Check if we've already been rate limited recently for Google
        base_domain = "google.com"
        await self._check_domain_rate_limit_async(base_domain)
        
        # Prepare the search query
        if 'site:' not in keyword:
            if self.is_indian_domain(keyword):
                search_query = f'"{keyword}" site:.in'
            else:
                search_query = f'"{keyword}"'
        else:
            search_query = keyword
        
        # Initialize a new browser if needed
        if not hasattr(self, 'browser') or self.browser is None:
            await self.initialize_browser()
        
        if not self.browser:
            logging.error("Failed to initialize browser for Google search")
            return []
        
        results = []
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries and len(results) < num_results:
            try:
                # Create a new page with stealth settings
                page = await self.browser.new_page()
                await self._apply_stealth_settings(page)
                
                # Record this access for rate limiting
                self.rate_limiter.record_request(base_domain)
                
                # Set up a longer timeout for Google
                page.set_default_timeout(60000)  # 60 seconds
                
                # Always use India's country code and Indian English locale
                country_param = 'in'  # Always use India
                lang_param = 'en-IN'  # Always use Indian English
                
                # Construct the Google search URL with Indian geo-targeting parameters
                start_index = page_num * 10
                google_url = f"https://www.google.co.in/search?q={quote(search_query)}&start={start_index}&gl={country_param}&hl={lang_param}"
                
                # Log the URL being accessed
                logging.info(f"Browser accessing with Indian geo-location: {google_url}")
                print(f"🇮🇳 Searching with Indian geo-location: {google_url}")
                
                # Add a random delay before accessing Google (between 5-15 seconds)
                delay = random.uniform(5, 15)
                logging.info(f"Adding pre-request delay of {delay:.1f}s")
                await asyncio.sleep(delay)
                
                # Navigate to Google
                response = await page.goto(google_url, wait_until="networkidle", timeout=90000)
                
                # Check for rate limiting or other issues
                if response.status == 429:
                    logging.warning("⚠️ Browser received 429 Too Many Requests from Google")
                    self.rate_limiter.record_error(base_domain, status_code=429)
                    
                    # Save the page for debugging
                    await page.screenshot(path=f"google_rate_limit_{int(time.time())}.png")
                    
                    # Wait longer before retry
                    backoff_time = 60 * (2 ** retry_count)
                    logging.info(f"Backing off for {backoff_time}s before retry")
                    await asyncio.sleep(backoff_time)
                    retry_count += 1
                    await page.close()
                    continue
                
                if response.status != 200:
                    logging.warning(f"Browser received non-200 status ({response.status}) from Google")
                    self.rate_limiter.record_error(base_domain, status_code=response.status)
                    retry_count += 1
                    await page.close()
                    continue
                
                # Wait some time for JavaScript to execute
                await asyncio.sleep(3)
                
                # Check for CAPTCHA
                captcha_detected = await self._detect_captcha_in_browser(page)
                if captcha_detected:
                    logging.warning("❌ CAPTCHA detected in browser Google search")
                    self.rate_limiter.record_error(base_domain, status_code=403)
                    
                    # Take a screenshot of the CAPTCHA
                    await page.screenshot(path=f"google_captcha_{int(time.time())}.png")
                    
                    # Close this page and try again after a longer delay
                    await page.close()
                    await asyncio.sleep(120)  # 2 minute delay after CAPTCHA
                    retry_count += 1
                    continue
                
                # Simulate human behavior to avoid detection
                await self._simulate_human_browsing(page)
                
                # Extract URLs from the search results
                page_results = await self._extract_search_results_from_page(page)
                
                if not page_results:
                    logging.warning("No results found in browser Google search - may be blocked")
                    self.rate_limiter.record_error(base_domain)
                    
                    # Save the page content for debugging
                    content = await page.content()
                    with open(f"google_search_page_{page_num}.html", "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    # Take a screenshot
                    await page.screenshot(path=f"google_search_page_{page_num}.png")
                    
                    # Close this page and try again
                    await page.close()
                    retry_count += 1
                    await asyncio.sleep(30)  # 30 second delay
                    continue
                
                # Record successful access
                self.rate_limiter.record_success(base_domain)
                
                # Add results to the list
                results.extend(page_results)
                
                # Close the page
                await page.close()
                
                # Wait before potentially going to the next page (if needed)
                await asyncio.sleep(random.uniform(3, 8))
                
                # If we haven't collected enough results and there are more pages
                if len(results) < num_results and page_num < 2:  # Limit to first 3 pages (0, 1, 2)
                    page_num += 1
                else:
                    break
                    
            except Exception as e:
                logging.error(f"Error in browser-based Google search: {e}")
                logging.error(traceback.format_exc())
                retry_count += 1
                
                # Wait before retry
                await asyncio.sleep(10 * retry_count)
        
        # Return unique results up to the requested number
        unique_results = list(dict.fromkeys(results))
        return unique_results[:num_results]
    
    def rotate_proxy(self):
        """Rotate to the next available proxy in the list."""
        if not self.proxy_list or len(self.proxy_list) <= 1:
            self.logger.warning("No alternative proxies available to rotate")
            return
            
        # Move first proxy to the end of the list
        current_proxy = self.proxy_list.pop(0)
        self.proxy_list.append(current_proxy)
        
        # Log the rotation
        proxy_desc = "direct connection" if current_proxy is None else f"proxy {self.proxy_list[0]}"
        self.logger.info(f"Rotated to next proxy: {proxy_desc}")
        print(f"🔄 Rotated to next proxy")

    def rotate_proxy_if_needed(self):
        """Check if proxy rotation is needed and rotate if so."""
        if random.random() < 0.2:  # 20% chance to rotate on any request
            self.rotate_proxy()

    def search_duckduckgo(self, keyword: str, num_results: int = 10) -> List[str]:
        """Search DuckDuckGo and return a list of result URLs."""
        urls = []
        
        # Use browser for DuckDuckGo which is better at handling their JavaScript
        if self.use_browser:
            self.logger.info("Using browser automation for DuckDuckGo search")
            
            # Create a new event loop for this synchronous method
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                # First initialize the browser
                browser_initialized = loop.run_until_complete(self.initialize_browser())
                if browser_initialized:
                    # Then run the search function
                    results = loop.run_until_complete(self._search_duckduckgo_with_browser(keyword, num_results))
                    return results
                else:
                    self.logger.warning("Failed to initialize browser for DuckDuckGo search")
            except Exception as e:
                self.logger.warning(f"Browser-based DuckDuckGo search failed: {e}, falling back to regular search")
            finally:
                # Close the loop when done
                loop.close()
        
        try:
            # DuckDuckGo's HTML frontend is more scraping-friendly
            search_url = f"https://html.duckduckgo.com/html/?q={quote(keyword)}&kl=in-en"
            print(f"🦆 Searching DuckDuckGo (HTML): {search_url}")
            
            # Get realistic headers
            headers = self._get_realistic_headers(search_url)
            headers['Accept-Language'] = 'en-IN,en-US;q=0.9,en;q=0.8,hi;q=0.7'
            
            # Make the request
            response = requests.get(search_url, headers=headers, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                results = soup.find_all('a', {'class': 'result__a'})
                
                for result in results:
                    if result.get('href'):
                        href = result.get('href')
                        if 'duckduckgo.com' in href:
                            # Extract actual URL from DuckDuckGo's redirect
                            href = href.split('uddg=')[1].split('&')[0] if 'uddg=' in href else None
                        if href and href.startswith('http'):
                            urls.append(unquote(href))
            else:
                self.logger.warning(f"DuckDuckGo search returned status code {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error in DuckDuckGo search: {e}")
        
        return list(set(urls))[:num_results]
    
    def _find_contact_urls(self, html_content: str, base_url: str, domain: str) -> List[str]:
        """Find contact page URLs from the main page.
        
        Args:
            html_content: HTML content to parse
            base_url: Base URL for resolving relative URLs
            domain: Domain of the website
            
        Returns:
            List of contact page URLs
        """
        contact_urls = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Common patterns for contact page links
        contact_patterns = [
            'contact', 'contact-us', 'reach-us', 'connect', 'get-in-touch',
            'about-us', 'feedback', 'support', 'help', 'contactus'
        ]
        
        # Look for links with contact-related text or URLs
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text().lower().strip()
            
            # Skip empty links, anchor links, and javascript links
            if not href or href.startswith('#') or href.startswith('javascript:'):
                continue
                
            # Skip external links to other domains
            if href.startswith(('http://', 'https://')) and domain not in href:
                continue
            
            # Check if the link text contains contact-related keywords
            is_contact_text = any(pattern in text for pattern in contact_patterns)
            
            # Check if the URL contains contact-related keywords
            is_contact_url = any(pattern in href.lower() for pattern in contact_patterns)
            
            if is_contact_text or is_contact_url:
                # Use our URL resolver to build absolute URL if relative
                contact_url = self._resolve_url(base_url, href)
                
                # Verify the URL is valid and within the same domain
                try:
                    parsed_contact = urlparse(contact_url)
                    parsed_base = urlparse(base_url)
                    
                    # Only include links to the same domain
                    if parsed_contact.netloc and parsed_contact.netloc != parsed_base.netloc:
                        continue
                        
                    # Apply additional filtering to exclude non-content pages
                    if contact_url != base_url and contact_url not in contact_urls:
                        # Apply normalization and filtering
                        normalized_url = self._normalize_url(contact_url)
                        if not normalized_url.startswith('noindex:') and self._filter_url(normalized_url):
                            contact_urls.append(contact_url)
                except Exception as e:
                    self.logger.warning(f"Error parsing contact URL {href}: {e}")
                    continue
        
        # Prioritize URLs with clearer contact indicators
        contact_urls.sort(key=lambda url: 
            (1 if 'contact' in url.lower() else 2) +
            (1 if 'about' in url.lower() else 2)
        )
        
        # Limit to a reasonable number to avoid excessive requests
        return contact_urls[:3]
    
    def _extract_emails_from_text(self, text: str) -> Set[str]:
        """Extract and validate email addresses from text."""
        emails = set()
        
        # Standard email pattern
        email_matches = self.email_pattern.findall(text)
        for email in email_matches:
            # Basic validation to filter out false positives
            if self._validate_email(email):
                emails.add(email.lower())
        
        # Obfuscated email pattern (e.g., "user at domain dot com")
        obfuscated_matches = self.obfuscated_email_pattern.findall(text)
        for match in obfuscated_matches:
            if len(match) == 3:  # Should have 3 parts: username, domain, TLD
                reconstructed_email = f"{match[0]}@{match[1]}.{match[2]}"
                if self._validate_email(reconstructed_email):
                    emails.add(reconstructed_email.lower())
        
        return emails
    
    def _validate_email(self, email: str) -> bool:
        """Validate an email address with enhanced filtering for HTML/CSS artifacts."""
        # Use our improved validator
        return validate_email(email)
    
    def _extract_phones_from_text(self, text: str, source: str = "unknown") -> Set[Union[str, Dict]]:
        """Extract and validate phone numbers from text with enhanced logic for better detection.
        
        Args:
            text: The text to extract phone numbers from
            source: Where the text was found (e.g., 'homepage', 'contact_page')
            
        Returns:
            Set of validated phone numbers in E.164 format or as dictionaries with metadata
        """
        phones = set()
        
        if not text or len(text) < 5:
            return phones
        
        # ENHANCEMENT: Better preprocessing for phone number detection
        # 1. Normalize different types of separators
        text = re.sub(r'(\d)\s*[.\-–—·•|:/\\]\s*(\d)', r'\1-\2', text)
        
        # 2. Better handle non-breaking spaces and other Unicode whitespace
        text = re.sub(r'\u00A0|\u2007|\u202F', ' ', text)
        
        # 3. Normalize parentheses with proper spacing 
        text = re.sub(r'(\d)\s*\(\s*(\d)', r'\1 (\2', text)
        text = re.sub(r'(\d)\s*\)\s*(\d)', r'\1) \2', text)
        
        # 4. Replace known formats like "Tel: ", "Phone: " with space for better extraction
        text = re.sub(r'(?i)(phone|mobile|telephone|contact|call|ph|tel|mob|cell)(\s*)(:|at|us|on|no|\#|number)(\s*)', ' ', text)
        
        # 5. Clean multiple spaces
        text = re.sub(r'\s+', ' ', text)
        
        # 6. Replace or with digits to handle formats like +91 or +91-
        text = re.sub(r'(\+\d+)\s+or\s+', r'\1 ', text)
        
        # 7. Explicitly handle hyphenated numbers and phone extensions
        text = re.sub(r'(\d+)\s*-\s*(\d+)', r'\1-\2', text)  # Fix spaced hyphens
        text = re.sub(r'(?i)ext\.?\s*(\d+)', r' ext\1', text)  # Normalize extensions
        
        # 8. Handle "dot" text separators sometimes used to obfuscate numbers
        text = re.sub(r'(\d+)\s*dot\s*(\d+)', r'\1.\2', text, flags=re.IGNORECASE)
        
        # Primary extraction using enhanced detection patterns
        # Try different patterns including our main patterns
        extraction_patterns = [
            # Standard 10-digit Indian mobile with optional +91 prefix
            r'(?:\+91[\s\-.]?)?[6789]\d{9}',
            
            # Format with spaces or hyphens every 3-4 digits
            r'(?:\+91[\s\-.]?)?[6789]\d{2,4}[\s\-.]?\d{2,4}[\s\-.]?\d{2,4}',
            
            # Format with STD code (landline)
            r'0\d{2,4}[\s\-.]?\d{6,8}',
            
            # Format with country code and parentheses
            r'\(\+?91\)[\s\-.]?[6789]\d{9}',
            
            # Format with parentheses around area/STD code
            r'\(\d{2,5}\)[\s\-.]?\d{5,8}',
            
            # International format without explicit country code (often business numbers)
            r'\+\d{1,3}[\s\-.]?\d{6,14}',
            
            # Explicit check for WhatsApp numbers which often use different formatting
            r'(?:whatsapp|wa)[\s:]*(?:\+91[\s\-.]?)?[6789]\d{9}'
        ]
        
        for pattern in extraction_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                valid_phone = self.validate_indian_phone(match, f"{source}_enhanced_pattern")
                if valid_phone:
                    phones.add(valid_phone)
        
        # Use our existing patterns as fallback
        # Main pattern
        phone_matches = self.phone_pattern.findall(text)
        for phone_match in phone_matches:
            if isinstance(phone_match, tuple):
                for group in phone_match:
                    if group and len(group.strip()) >= 5:
                        valid_phone = self.validate_indian_phone(group, source)
                        if valid_phone:
                            phones.add(valid_phone)
            else:
                if phone_match and len(phone_match.strip()) >= 5:
                    valid_phone = self.validate_indian_phone(phone_match, source)
                    if valid_phone:
                        phones.add(valid_phone)
        
        # Alternative pattern
        alt_matches = self.phone_pattern_alt.findall(text)
        for phone_match in alt_matches:
            if isinstance(phone_match, tuple):
                for group in phone_match:
                    if group and len(group.strip()) >= 5:
                        valid_phone = self.validate_indian_phone(group, source)
                        if valid_phone:
                            phones.add(valid_phone)
            else:
                if phone_match and len(phone_match.strip()) >= 5:
                    valid_phone = self.validate_indian_phone(phone_match, source)
                    if valid_phone:
                        phones.add(valid_phone)
        
        # ENHANCEMENT: Look for specific contexts that strongly indicate phone numbers
        contexts = [
            # Look for phrases like "Call us at" followed by numbers
            (r'(?i)(?:call|dial|phone|contact)\s+(?:us|our|me)?\s*(?:at|on|:)?\s*((?:\+?91)?[\s\-.]?[0-9\s\-\.]{8,16})', 1),
            # Look for "WhatsApp" followed by numbers
            (r'(?i)(?:whatsapp|wa)[\s:]+([0-9\s\+\-\.]{8,16})', 1),
            # Look for For Sales: followed by numbers
            (r'(?i)(?:for|sales|support|help|service)[\s:]+([0-9\s\+\-\.]{8,16})', 1),
            # Look for Mobile: followed by numbers
            (r'(?i)(?:mobile|cell|m)[\s:]+([0-9\s\+\-\.]{8,16})', 1),
            # Look for tel: links which often contain phone numbers
            (r'tel:([0-9\s\+\-\.]{8,16})', 1)
        ]
        
        for pattern, group_idx in contexts:
            context_matches = re.findall(pattern, text)
            for match in context_matches:
                if isinstance(match, tuple) and len(match) > group_idx:
                    phone_text = match[group_idx]
                else:
                    phone_text = match
                    
                valid_phone = self.validate_indian_phone(phone_text, f"{source}_context")
                if valid_phone:
                    phones.add(valid_phone)
        
        # ENHANCEMENT: Additional check for Indian number formats with different prefixes
        # Some Indian numbers might be displayed with different formatting for better readability
        for raw_digits in re.findall(r'\b(0?[6789]\d{9})\b', text):
            if len(raw_digits) >= 10:
                valid_phone = self.validate_indian_phone(raw_digits, f"{source}_raw_digits")
                if valid_phone:
                    phones.add(valid_phone)
        
        return phones
    
    def test_extraction(self, test_urls=None):
        """Test the extraction functionality with sample URLs."""
        if test_urls is None:
            # Default test URLs with known contact information
            test_urls = [
                "https://www.digitalmarketingdelhi.in/",
                "https://www.socialbeat.in/", 
                "https://digitalready.co/",
                "https://www.webchutney.com/contact",
                "https://www.techmagnate.com/contact-us.html"
            ]
        
        print("\n=== CONTACT EXTRACTION TEST ===")
        all_emails = set()
        all_phones = set()
        
        for url in test_urls:
            print(f"\nTesting URL: {url}")
            try:
                emails, phones = self.extract_contacts_from_url(url)
                
                if emails:
                    print("Emails found:")
                    for email in emails:
                        print(f"  - {email}")
                        all_emails.add(email)
                else:
                    print("No emails found")
                    
                if phones:
                    print("Phones found:")
                    for phone in phones:
                        print(f"  - {phone}")
                        all_phones.add(phone)
                else:
                    print("No phones found")
                    
            except Exception as e:
                print(f"Error: {e}")
        
        print("\nTest Summary:")
        print(f"Total unique emails found: {len(all_emails)}")
        print(f"Total unique phones found: {len(all_phones)}")
        return all_emails, all_phones
    
    def _check_domain_rate_limit(self, domain):
        """Check if we should rate limit a domain access and wait if needed."""
        current_time = time.time()
        
        # If we've accessed this domain recently, enforce a delay
        if domain in self.domain_access_times:
            last_access = self.domain_access_times[domain]
            elapsed = current_time - last_access
            
            if elapsed < self.domain_min_interval:
                wait_time = self.domain_min_interval - elapsed + random.uniform(1, 5)
                self.logger.info(f"Rate limiting domain {domain}. Waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
    
    def _track_domain_access(self, domain):
        """Track when we accessed a domain and how many times."""
        self.domain_access_times[domain] = time.time()
        
        if domain in self.domain_request_count:
            self.domain_request_count[domain] += 1
        else:
            self.domain_request_count[domain] = 1
            
        # Add to recent domains set for rate limiting
        self.recent_domains.add(domain)
        
    async def _check_domain_rate_limit_async(self, domain):
        """Async version of domain rate limiting."""
        current_time = time.time()
        
        # If we've accessed this domain recently, enforce a delay
        if domain in self.domain_access_times:
            last_access = self.domain_access_times[domain]
            elapsed = current_time - last_access
            
            if elapsed < self.domain_min_interval:
                wait_time = self.domain_min_interval - elapsed + random.uniform(1, 5)
                self.logger.info(f"Rate limiting domain {domain}. Waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                
    def is_indian_domain(self, url):
        """Check if a domain is likely to be Indian based on TLD or content."""
        # First check TLD for .in domains
        domain = urlparse(url).netloc
        if self.indian_domain_pattern.search(domain):
            return True
            
        # Check for common Indian domain names
        indian_terms = ['india', 'bharat', 'desi', 'hindustan', 'bharatiya', 'sarkari']
        for term in indian_terms:
            if term in domain.lower():
                return True
                
        # Use TLD extract to check if the site is from India
        extract_result = tldextract.extract(url)
        if extract_result.suffix == 'in':
            return True
            
        return False
        
    def __enter__(self):
        """Support for 'with' context manager."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources when exiting 'with' context."""
        # Use our run_async helper function for cleanup
        try:
            run_async(self.close_browser())
        except Exception as e:
            self.logger.warning(f"Error during browser cleanup in context exit: {e}")
        
        return False  # Don't suppress exceptions
        
    def __del__(self):
        """Destructor to ensure proper cleanup."""
        try:
            # Attempt to safely clean up browser resources
            if hasattr(self, 'browser') and self.browser:
                # Use our run_async helper for proper event loop management
                try:
                    run_async(self.close_browser())
                except Exception as e:
                    self.logger.warning(f"Browser cleanup failed in destructor: {e}")
        except Exception as e:
            # Log but continue since we're in destructor
            if hasattr(self, 'logger'):
                self.logger.warning(f"Error in destructor: {e}")
            else:
                print(f"Error in destructor: {e}")

    def test_regex(self, sample_html=None):
        """Unit test function to validate email and phone extraction patterns."""
        if sample_html is None:
            sample_html = """
            <p>Contact us at: contact@example.com, support@company.co.in</p>
            <p>Call us: +91 9876543210, 8765432109, 07654321098</p>
            <p>Email: info@domain.in or marketing@site.com</p>
            """
        
        print("=== REGEX PATTERN TEST ===")
        soup = BeautifulSoup(sample_html, 'html.parser')
        text = soup.get_text()
        
        print("Text sample:", text.strip()[:100] + "..." if len(text) > 100 else text.strip())
        print("\nEmail pattern:", self.email_pattern.pattern)
        emails = self.email_pattern.findall(text)
        print("Emails found:", emails)
        
        print("\nPhone pattern:", self.phone_pattern.pattern)
        phone_matches = self.phone_pattern.findall(text)
        print("Phone matches:", phone_matches)
        
        # Test the phone validation with source information
        print("\nTesting phone validation:")
        for phone_match in phone_matches:
            if isinstance(phone_match, tuple):
                for group in phone_match:
                    if group:
                        print(f"\nTesting: {group}")
                        valid_phone = self.validate_indian_phone(phone_match, "test_sample")
                        if valid_phone:
                            print(f"  ✓ Valid: {valid_phone['phone']} (Source: {valid_phone['source']})")
                        else:
                            print(f"  ✗ Invalid")
            else:
                print(f"\nTesting: {phone_match}")
                valid_phone = self.validate_indian_phone(phone_match, "test_sample")
                if valid_phone:
                    print(f"  ✓ Valid: {valid_phone['phone']} (Source: {valid_phone['source']})")
                else:
                    print(f"  ✗ Invalid")
        
        # Test using the improved validator directly
        print("\nTesting improved validator directly:")
        for phone_match in ["+91 9876543210", "8765432109", "07654321098"]:
            print(f"\nDirect test: {phone_match}")
            result = validate_indian_phone(phone_match, "test_sample")
            if result:
                print(f"  ✓ Valid: {result['phone']} (Original: {result['original']}, Source: {result['source']})")
            else:
                print(f"  ✗ Invalid")

    def save_detailed_results_to_csv(self, keyword: str, results_by_url: List[Dict]):
        """Save detailed extraction results to a CSV file, including per-URL findings."""
        # Create directory if it doesn't exist
        os.makedirs('scraped_data', exist_ok=True)
        
        # Create a safe filename
        safe_keyword = re.sub(r'[^\w\s-]', '', keyword).strip().replace(' ', '_')
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"scraped_data/{safe_keyword}_{timestamp}_detailed.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['url', 'domain', 'emails', 'phones', 'phone_sources', 'error']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for result in results_by_url:
                # Process phone numbers to extract source information
                phones_list = []
                sources_list = []
                
                for phone in result.get('phones', []):
                    if isinstance(phone, dict):
                        # If phone is in the new dictionary format
                        phones_list.append(phone.get('phone', ''))
                        sources_list.append(f"{phone.get('phone', '')}: {phone.get('source', 'unknown')}")
                    else:
                        # If phone is a string (legacy format)
                        phones_list.append(phone)
                        sources_list.append(f"{phone}: unknown")
                
                # Convert list fields to comma-separated strings
                row = {
                    'url': result.get('url', ''),
                    'domain': result.get('domain', ''),
                    'emails': ','.join(result.get('emails', [])),
                    'phones': ','.join(phones_list),
                    'phone_sources': '; '.join(sources_list),
                    'error': result.get('error', '')
                }
                writer.writerow(row)
            
        self.logger.info(f"Detailed results saved to {filename}")
        return filename
        
    def save_results_to_csv(self, keyword: str, emails: Set[str], phones: Set[str]):
        """Save extracted contacts to a CSV file with enhanced phone information."""
        # Create directory if it doesn't exist
        os.makedirs('scraped_data', exist_ok=True)
        
        # Create a safe filename
        safe_keyword = re.sub(r'[^\w\s-]', '', keyword).strip().replace(' ', '_')
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"scraped_data/{safe_keyword}_{timestamp}_contacts.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            # Updated header with source information
            writer.writerow(['Type', 'Contact', 'Original', 'Source'])
            
            # Write emails
            for email in emails:
                writer.writerow(['Email', email, '', ''])
            
            # Write phones with original format and source if available
            for phone in phones:
                if isinstance(phone, dict):
                    # If phone is already in the new dictionary format
                    writer.writerow(['Phone', phone.get('phone', ''), 
                                    phone.get('original', ''), 
                                    phone.get('source', 'unknown')])
                else:
                    # If phone is in the legacy string format
                    writer.writerow(['Phone', phone, '', ''])
                
        self.logger.info(f"Results saved to {filename}")
        return filename

    # Add Gemini API query optimization methods
    def optimize_search_query_with_gemini(self, keyword: str) -> str:
        """
        Use Google's Gemini API to optimize the search query for finding emails and phone numbers.
        
        Args:
            keyword (str): The original search keyword
            
        Returns:
            str: Optimized search query for Google
        """
        if not self.gemini_model:
            self.logger.warning("Gemini API not available. Using manual query optimization.")
            return self._fallback_optimize_query(keyword)
            
        try:
            # Create exclusion string for sites we want to exclude
            exclusion_string = ' '.join([f'-site:{site}' for site in self.search_excluded_sites[:10]])
            
            # Create prompt for Gemini
            prompt = f"""
            I need to find business contact information (emails and phone numbers) for "{keyword}".
            Please create an optimized Google search query that will help me find this information.
            
            The query should:
            1. Focus on finding contact pages, email addresses, and phone numbers
            2. Target business websites related to "{keyword}"
            3. Exclude social media and marketplace sites
            4. Use Google search operators effectively
            5. Be optimized to find Indian businesses if possible
            
            Return ONLY the optimized search query without any explanations.
            """
            
            # Get response from Gemini
            try:
                response = self.gemini_model.generate_content(prompt)
                
                if response and hasattr(response, 'text'):
                    optimized_query = response.text.strip()
                    
                    # Ensure the query isn't too long
                    if len(optimized_query) > 250:
                        optimized_query = optimized_query[:250]
                        
                    # Add exclusions if not already present
                    if '-site:' not in optimized_query:
                        optimized_query += f" {exclusion_string}"
                        
                    self.logger.info(f"Gemini optimized query: {optimized_query}")
                    return optimized_query
                else:
                    self.logger.warning("Empty response from Gemini API")
                    return self._fallback_optimize_query(keyword)
            except Exception as e:
                self.logger.error(f"Error generating content with Gemini API: {e}")
                return self._fallback_optimize_query(keyword)
                
        except Exception as e:
            self.logger.error(f"Error using Gemini API: {e}")
            return self._fallback_optimize_query(keyword)
    
    def _fallback_optimize_query(self, keyword: str) -> str:
        """
        Fallback method to manually optimize the search query if Gemini API is unavailable.
        
        Args:
            keyword (str): The original search keyword
            
        Returns:
            str: Manually optimized search query
        """
        # Create exclusion string for sites we want to exclude
        exclusion_string = ' '.join([f'-site:{site}' for site in self.search_excluded_sites])
        
        # Check if keyword appears to be a company or business name
        if ' ' in keyword or keyword[0].isupper():
            # Likely a business name
            optimized_query = f'"{keyword}" (contact OR "contact us" OR "email us" OR "phone" OR "mobile") (email OR "contact information" OR "get in touch") {exclusion_string}'
        else:
            # More generic keyword
            optimized_query = f'"{keyword}" business (contact OR "contact us" OR "email" OR "phone" OR "mobile") {exclusion_string}'
            
        # Add India-specific terms if appropriate
        if self.is_indian_domain(keyword) or 'india' in keyword.lower():
            optimized_query += ' india'
            
        self.logger.info(f"Fallback optimized query: {optimized_query}")
        return optimized_query

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
        
        # Optimize the search query using Gemini API
        optimized_query = self.optimize_search_query_with_gemini(keyword)
        self.logger.info(f"Original keyword: '{keyword}' | Optimized query: '{optimized_query}'")
        print(f"🧠 Optimized search query: {optimized_query}")
        
        # Initialize task status if tracking is enabled
        if task_id:
            status_data = {
                "status": "processing",
                "progress": 5,
                "message": f"Starting search with optimized query: '{optimized_query}'",
                "keyword": keyword,
                "task_id": task_id,
                "results_count": 0,
                "elapsed_time": 0
            }
            self.update_task_status(task_id, status_data, task_record)
        
        try:
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
                print(f"🔍 Searching Google for {keyword} (page {search_page})...")
                
                # First optimize the search query if we haven't done so yet
                if not 'optimized_query' in locals():
                    optimized_query = self.optimize_search_query_with_gemini(keyword)
                    self.logger.info(f"Original keyword: '{keyword}' | Optimized query: '{optimized_query}'")
                    print(f"🧠 Optimized search query: {optimized_query}")
                
                # Use our search function to get URLs with the optimized query instead of the original keyword
                search_results = self.search_google(optimized_query, num_results=10, page=search_page-1)
                search_page += 1  # Increment page counter for next iteration
                
                if not search_results:
                    print("❌ No search results found. Trying alternative method...")
                    # Try DuckDuckGo as a fallback
                    search_results = self.search_duckduckgo(optimized_query, num_results=num_results)
                    
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
            
            self.logger.info(f"Scraping completed: found {len(emails)} emails and {len(phones)} phones")
            return result
            
        except Exception as e:
            self.logger.error(f"Error during scraping: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            
            status_data = {
                "status": "error",
                "progress": 0,
                "message": f"Error: {str(e)}",
                "keyword": keyword,
                "task_id": task_id,
                "results_count": 0,
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
                    "elapsed_time_minutes": (time.time() - start_time) / 60.0
                }
            }

    # Update the status with better database handling
    def update_task_status(task_id, status, task_record=None):
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
        Search DuckDuckGo using a browser (Playwright) to bypass bot detection
        
        Args:
            keyword (str): Search keyword
            num_results (int): Maximum number of results to return
            
        Returns:
            List[str]: List of URLs
        """
        # Check rate limiting
        base_domain = "duckduckgo.com"
        await self._check_domain_rate_limit_async(base_domain)
        
        # Prepare the search query
        if 'site:' not in keyword:
            if self.is_indian_domain(keyword):
                search_query = f'"{keyword}" site:.in'
            else:
                search_query = f'"{keyword}"'
        else:
            search_query = keyword
        
        # Initialize a new browser if needed
        if not self.browser_initialized or not self.page:
            browser_ready = await self.initialize_browser()
            if not browser_ready:
                self.logger.error("Failed to initialize browser for DuckDuckGo search")
                return []
        
        results = []
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries and len(results) < num_results:
            try:
                # Create a new page with stealth settings
                page = await self.browser.new_page()
                await self._apply_stealth_settings(page)
                
                # Record this access for rate limiting
                self.rate_limiter.record_request(base_domain)
                
                # Set up a reasonable timeout
                page.set_default_timeout(30000)  # 30 seconds
                
                # Construct the DuckDuckGo search URL with region parameter for India
                duckduckgo_url = f"https://duckduckgo.com/?q={quote(search_query)}&kl=in-en&ia=web"
                
                # Log the URL being accessed
                self.logger.info(f"Browser accessing DuckDuckGo: {duckduckgo_url}")
                print(f"🦆 Searching DuckDuckGo (India region): {duckduckgo_url}")
                
                # Add a small delay before request
                delay = random.uniform(2, 5)
                self.logger.info(f"Adding pre-request delay of {delay:.1f}s")
                await asyncio.sleep(delay)
                
                # Navigate to DuckDuckGo
                response = await page.goto(duckduckgo_url, wait_until="domcontentloaded", timeout=30000)
                
                # Check for successful response
                if not response or response.status >= 400:
                    self.logger.warning(f"Error response from DuckDuckGo: {response.status if response else 'No response'}")
                    retry_count += 1
                    await page.close()
                    continue
                
                # Wait for results to load
                try:
                    # Wait for results to appear
                    await page.wait_for_selector("a.result__a", timeout=10000)
                except Exception:
                    # Try alternative selector if the first one fails
                    try:
                        await page.wait_for_selector(".result__url", timeout=5000)
                    except Exception as e:
                        self.logger.warning(f"Timeout waiting for DuckDuckGo results: {e}")
                        # Take a screenshot for debugging if in debug mode
                        if self.debug_mode:
                            await page.screenshot(path=f"duckduckgo_timeout_{int(time.time())}.png")
                        retry_count += 1
                        await page.close()
                        continue
                
                # Extract search results
                page_results = await page.evaluate("""
                    () => {
                        const links = Array.from(document.querySelectorAll('a.result__a, .result__url'));
                        return links.map(link => {
                            // DuckDuckGo uses redirects for external links
                            let href = link.getAttribute('href');
                            if (href.startsWith('/l/?')) {
                                // Extract the actual URL from the redirect
                                const urlMatch = href.match(/uddg=([^&]+)/);
                                if (urlMatch && urlMatch[1]) {
                                    return decodeURIComponent(urlMatch[1]);
                                }
                            }
                            return href;
                        }).filter(url => url && url.startsWith('http') && !url.includes('duckduckgo.com'));
                    }
                """)
                
                # Log results
                if page_results:
                    self.logger.info(f"Found {len(page_results)} results from DuckDuckGo")
                    # Filter for unique, valid URLs
                    for url in page_results:
                        if url and url.startswith('http') and url not in results:
                            results.append(url)
                else:
                    self.logger.warning("No results found from DuckDuckGo search")
                    # Take a screenshot for debugging if in debug mode
                    if self.debug_mode:
                        await page.screenshot(path=f"duckduckgo_no_results_{int(time.time())}.png")
                
                # Close the page
                await page.close()
                
                # If we have enough results, stop
                if len(results) >= num_results:
                    break
                
                # Wait before potentially trying again
                await asyncio.sleep(random.uniform(3, 5))
                
            except Exception as e:
                self.logger.error(f"Error in browser-based DuckDuckGo search: {e}")
                import traceback
                self.logger.error(traceback.format_exc())
                
                retry_count += 1
                
                # Wait before retry
                await asyncio.sleep(random.uniform(3, 7))
        
        # Return unique results up to the requested number
        unique_results = list(dict.fromkeys(results))
        return unique_results[:num_results]

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
        
        # Check if domain is in excluded list
        if domain in self.excluded_domains:
            self.logger.info(f"Skipping excluded domain: {domain}")
            return set(), set()
        
        emails = set()
        phones = set()
        
        # Apply advanced anti-bot detection techniques
        self.rate_limiter.adaptive_delay(domain, 0.8)  # Lower importance means we're willing to wait longer
        
        # First, try to use the browser (more reliable for modern sites)
        if self.use_browser:
            try:
                # Use our async function with proper event loop management
                loop = get_or_create_event_loop()
                html_content = loop.run_until_complete(self.browser_get_page(url, max_retries=2))
                
                if html_content:
                    self.logger.info(f"Successfully retrieved content for {url} using browser")
                    
                    # Parse with BeautifulSoup for easier extraction
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Extract both visible and hidden content
                    visible_text = soup.get_text()
                    
                    # Look for emails in visible text
                    emails_found = self._extract_emails_from_text(visible_text)
                    emails.update(emails_found)
                    
                    # Look for phones in visible text with enhanced extraction
                    phones_found = self._extract_phones_from_text(visible_text, source=f"{domain}_visible")
                    phones.update(phones_found)
                    
                    # Extract from HTML attributes (like href="mailto:" or href="tel:")
                    attr_emails, attr_phones = self._extract_from_attributes(soup, domain)
                    emails.update(attr_emails)
                    phones.update(attr_phones)
                    
                    # Extract from meta tags and JSON-LD structured data
                    struct_emails, struct_phones = self._extract_from_structured_data(html_content, domain)
                    emails.update(struct_emails)
                    phones.update(struct_phones)
                    
                    # Extract from common obfuscation patterns
                    obfs_emails = self._extract_obfuscated_emails(html_content)
                    emails.update(obfs_emails)
                    
                    # Look for contact pages and follow them for more information
                    if not emails and not phones:
                        contact_urls = self._find_contact_urls(html_content, url, domain)
                        
                        for contact_url in contact_urls[:2]:  # Limit to 2 contact pages
                            self.logger.info(f"Following contact URL: {contact_url}")
                            
                            # Add a short delay before requesting contact page
                            time.sleep(random.uniform(1, 3))
                            
                            # Get the contact page content
                            contact_html = loop.run_until_complete(self.browser_get_page(contact_url, max_retries=1))
                            
                            if contact_html:
                                contact_soup = BeautifulSoup(contact_html, 'html.parser')
                                contact_text = contact_soup.get_text()
                                
                                # Extract from contact page
                                contact_emails = self._extract_emails_from_text(contact_text)
                                emails.update(contact_emails)
                                
                                contact_phones = self._extract_phones_from_text(
                                    contact_text, source=f"{domain}_contact_page"
                                )
                                phones.update(contact_phones)
                                
                                # Extract from HTML attributes on contact page
                                attr_emails, attr_phones = self._extract_from_attributes(
                                    contact_soup, f"{domain}_contact_page"
                                )
                                emails.update(attr_emails)
                                phones.update(attr_phones)
                else:
                    self.logger.warning(f"Failed to get content from {url} using browser")
            
            except Exception as e:
                self.logger.error(f"Error using browser for {url}: {e}")
                traceback.print_exc()
        
        # If browser fails or is disabled, try with requests
        if not emails and not phones:
            try:
                # Make the HTTP request with retry logic
                response = self.make_request(url)
                
                if response and response.status_code == 200:
                    # Parse with BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Extract visible text
                    visible_text = soup.get_text()
                    
                    # Extract emails and phones from visible text
                    emails_found = self._extract_emails_from_text(visible_text)
                    emails.update(emails_found)
                    
                    phones_found = self._extract_phones_from_text(visible_text, source=f"{domain}_requests")
                    phones.update(phones_found)
                    
                    # Extract from HTML attributes
                    attr_emails, attr_phones = self._extract_from_attributes(soup, domain)
                    emails.update(attr_emails)
                    phones.update(attr_phones)
                    
                    # Extract from structured data
                    struct_emails, struct_phones = self._extract_from_structured_data(response.text, domain)
                    emails.update(struct_emails)
                    phones.update(struct_phones)
                    
                    # Extract obfuscated emails
                    obfs_emails = self._extract_obfuscated_emails(response.text)
                    emails.update(obfs_emails)
                    
                    # If no contacts found, try contact pages
                    if not emails and not phones:
                        contact_urls = self._find_contact_urls(response.text, url, domain)
                        
                        for contact_url in contact_urls[:2]:
                            self.logger.info(f"Following contact URL: {contact_url}")
                            
                            # Add a delay before requesting contact page
                            time.sleep(random.uniform(1, 3))
                            
                            # Get the contact page
                            contact_response = self.make_request(contact_url)
                            
                            if contact_response and contact_response.status_code == 200:
                                contact_soup = BeautifulSoup(contact_response.text, 'html.parser')
                                contact_text = contact_soup.get_text()
                                
                                # Extract from contact page
                                contact_emails = self._extract_emails_from_text(contact_text)
                                emails.update(contact_emails)
                                
                                contact_phones = self._extract_phones_from_text(
                                    contact_text, source=f"{domain}_contact_page"
                                )
                                phones.update(contact_phones)
                                
                                # Extract from HTML attributes on contact page
                                attr_emails, attr_phones = self._extract_from_attributes(
                                    contact_soup, f"{domain}_contact_page"
                                )
                                emails.update(attr_emails)
                                phones.update(attr_phones)
                else:
                    self.logger.warning(f"Failed to get content from {url} using requests")
                    
            except Exception as e:
                self.logger.error(f"Error using requests for {url}: {e}")
        
        # Validate all emails before returning
        validated_emails = set()
        for email in emails:
            if self._validate_email(email):
                validated_emails.add(email)
        
        self.logger.info(f"Extraction from {url} complete. Found {len(validated_emails)} emails and {len(phones)} phones")
        return validated_emails, phones

    def _extract_from_attributes(self, soup, domain_source):
        """
        Extract contact information from HTML attributes like href="mailto:" or href="tel:".
        
        Args:
            soup: BeautifulSoup object
            domain_source: Source domain for attribution
            
        Returns:
            tuple: (set of emails, set of phones)
        """
        emails = set()
        phones = set()
        
        # Extract from mailto links
        mailto_links = soup.select('a[href^="mailto:"]')
        for link in mailto_links:
            href = link.get('href', '')
            if href.startswith('mailto:'):
                email = href[7:].split('?')[0].strip()  # Remove mailto: prefix and any parameters
                if self._validate_email(email):
                    emails.add(email)
        
        # Extract from tel links
        tel_links = soup.select('a[href^="tel:"], a[href^="phone:"]')
        for link in tel_links:
            href = link.get('href', '')
            if href.startswith('tel:') or href.startswith('phone:'):
                phone = href.split(':')[1].strip()
                validated_phone = self.validate_indian_phone(phone, f"{domain_source}_tel_link")
                if validated_phone:
                    phones.add(validated_phone)
        
        # Extract from data attributes that might contain contact info
        data_elements = soup.select('[data-email], [data-contact], [data-phone]')
        for element in data_elements:
            # Check for email data attributes
            email_attr = element.get('data-email', '')
            if email_attr and '@' in email_attr:
                if self._validate_email(email_attr):
                    emails.add(email_attr)
            
            # Check for phone data attributes
            phone_attr = element.get('data-phone', '') or element.get('data-contact', '')
            if phone_attr:
                validated_phone = self.validate_indian_phone(phone_attr, f"{domain_source}_data_attr")
                if validated_phone:
                    phones.add(validated_phone)
        
        return emails, phones

    def _extract_from_structured_data(self, html_content, domain_source):
        """
        Extract contact information from structured data like JSON-LD, microdata, etc.
        
        Args:
            html_content: HTML content to parse
            domain_source: Source domain for attribution
            
        Returns:
            tuple: (set of emails, set of phones)
        """
        emails = set()
        phones = set()
        
        # Extract JSON-LD data
        json_ld_data = extract_json_ld(html_content)
        
        for data in json_ld_data:
            # Extract emails from JSON-LD
            if isinstance(data, dict):
                # Check for email in standard properties
                email_properties = ['email', 'emailAddress', 'contactEmail', 'contactPoint.email']
                for prop in email_properties:
                    if '.' in prop:
                        # Handle nested properties
                        parts = prop.split('.')
                        value = data
                        for part in parts:
                            if isinstance(value, dict) and part in value:
                                value = value[part]
                            else:
                                value = None
                                break
                        
                        if value and isinstance(value, str) and '@' in value:
                            if self._validate_email(value):
                                emails.add(value)
                    elif prop in data and isinstance(data[prop], str) and '@' in data[prop]:
                        if self._validate_email(data[prop]):
                            emails.add(data[prop])
                
                # Check for phone in standard properties
                phone_properties = ['telephone', 'phone', 'contactPhone', 'contactPoint.telephone']
                for prop in phone_properties:
                    if '.' in prop:
                        # Handle nested properties
                        parts = prop.split('.')
                        value = data
                        for part in parts:
                            if isinstance(value, dict) and part in value:
                                value = value[part]
                            else:
                                value = None
                                break
                        
                        if value:
                            validated_phone = self.validate_indian_phone(str(value), f"{domain_source}_jsonld")
                            if validated_phone:
                                phones.add(validated_phone)
                    elif prop in data:
                        validated_phone = self.validate_indian_phone(str(data[prop]), f"{domain_source}_jsonld")
                        if validated_phone:
                            phones.add(validated_phone)
                
                # Check in contactPoint array
                if 'contactPoint' in data and isinstance(data['contactPoint'], list):
                    for contact_point in data['contactPoint']:
                        if isinstance(contact_point, dict):
                            if 'telephone' in contact_point:
                                validated_phone = self.validate_indian_phone(
                                    str(contact_point['telephone']), f"{domain_source}_contactPoint"
                                )
                                if validated_phone:
                                    phones.add(validated_phone)
                            
                            if 'email' in contact_point and '@' in contact_point['email']:
                                if self._validate_email(contact_point['email']):
                                    emails.add(contact_point['email'])
        
        # Extract from meta tags that might contain contact info
        soup = BeautifulSoup(html_content, 'html.parser')
        meta_tags = soup.select('meta[name*="email"], meta[name*="contact"], meta[property*="email"], meta[property*="contact"]')
        
        for tag in meta_tags:
            content = tag.get('content', '')
            
            # Check for email
            if '@' in content:
                email_match = self.email_pattern.search(content)
                if email_match:
                    email = email_match.group(0)
                    if self._validate_email(email):
                        emails.add(email)
            
            # Check for phone
            phone_matches = self.phone_pattern.findall(content)
            for match in phone_matches:
                if isinstance(match, tuple):
                    # Handle tuple results from regex groups
                    for group in match:
                        if group:
                            validated_phone = self.validate_indian_phone(group, f"{domain_source}_meta_tag")
                            if validated_phone:
                                phones.add(validated_phone)
                else:
                    validated_phone = self.validate_indian_phone(match, f"{domain_source}_meta_tag")
                    if validated_phone:
                        phones.add(validated_phone)
        
        return emails, phones

    def _extract_obfuscated_emails(self, html_content):
        """
        Extract emails that are obfuscated to avoid scraping.
        
        Args:
            html_content: HTML content to parse
            
        Returns:
            set: Set of extracted emails
        """
        emails = set()
        
        # Look for common JavaScript obfuscation patterns
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Pattern 1: Split emails with multiple spans
        try:
            # Find elements with email parts
            email_spans = soup.select('span[data-email-part], span[class*="email"], span[id*="email"]')
            
            if email_spans:
                # Group by parent to reconstruct emails split across multiple spans
                email_parents = {}
                for span in email_spans:
                    parent = span.parent
                    if parent not in email_parents:
                        email_parents[parent] = []
                    email_parents[parent].append(span.get_text())
                
                # Reconstruct emails
                for parts in email_parents.values():
                    reconstructed = ''.join(parts)
                    if '@' in reconstructed:
                        if self._validate_email(reconstructed):
                            emails.add(reconstructed)
        except Exception as e:
            self.logger.warning(f"Error extracting obfuscated emails (pattern 1): {e}")
        
        # Pattern 2: document.write with concatenation
        js_patterns = [
            r'document\.write\s*\(\s*[\'"][^\'"]+'  # document.write with string
            r'[a-zA-Z0-9._%+-]+\s*(?:[\[\(]?\s*at\s*[\]\)]?|\[@\]|&#64;|@)\s*[a-zA-Z0-9.-]+'  # username @ domain pattern
            r'[^\'"]+[\'"]\s*\)',  # rest of the string
            
            # Unicode encoding
            r'(?:&#[0-9]{2,4};){5,}',  # Unicode chars that might be an email
            
            # Reversed email with JavaScript reversal
            r'var\s+[a-z]\s*=\s*[\'"][a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}[\'"]\s*;.*\.split\s*\(\s*[\'"][\'"]'
        ]
        
        for pattern in js_patterns:
            try:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    # Look for email patterns in the match
                    email_matches = self.email_pattern.findall(match)
                    for email in email_matches:
                        if self._validate_email(email):
                            emails.add(email)
                    
                    # For unicode encoding, try to decode
                    if '&#' in match:
                        try:
                            decoded = self._decode_html_entities(match)
                            email_matches = self.email_pattern.findall(decoded)
                            for email in email_matches:
                                if self._validate_email(email):
                                    emails.add(email)
                        except Exception:
                            pass
            except Exception as e:
                self.logger.warning(f"Error extracting obfuscated emails (JS patterns): {e}")
        
        # Check for emails in HTML comments
        try:
            comments = soup.find_all(string=lambda text: isinstance(text, Comment))
            for comment in comments:
                email_matches = self.email_pattern.findall(comment)
                for email in email_matches:
                    if self._validate_email(email):
                        emails.add(email)
        except Exception as e:
            self.logger.warning(f"Error extracting emails from comments: {e}")
        
        # Check for CSS obfuscation (display:none, visibility:hidden)
        try:
            hidden_elements = soup.select('[style*="display:none"], [style*="visibility:hidden"], .hidden, [hidden]')
            for element in hidden_elements:
                text = element.get_text()
                email_matches = self.email_pattern.findall(text)
                for email in email_matches:
                    if self._validate_email(email):
                        emails.add(email)
        except Exception as e:
            self.logger.warning(f"Error extracting emails from hidden elements: {e}")
        
        return emails

    def _decode_html_entities(self, text):
        """
        Decode HTML entities in text.
        
        Args:
            text: Text with HTML entities
            
        Returns:
            str: Decoded text
        """
        # Replace common HTML entities
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        # Replace numeric entities (&#xx;)
        def replace_entity(match):
            entity = match.group(1)
            if entity.startswith('x'):
                return chr(int(entity[1:], 16))
            else:
                return chr(int(entity))
                
        return re.sub(r'&#([0-9a-fA-F]+);', replace_entity, text)

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
    if not args.api_mode:
        print(f"⚠️ Could not update BackgroundTask record: {e}")



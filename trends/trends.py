# trends_fetcher.py

from pytrends.request import TrendReq
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import numpy as np
import datetime
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import requests
import json
import os
from matplotlib import cm
from mpl_toolkits.axes_grid1 import make_axes_locatable
import logging
import re
import random
import string
import socket
from fake_useragent import UserAgent
import socks
import backoff
import urllib3
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from requests_cache import CachedSession
from time import sleep
import hashlib
# Import exceptions from correct modules
from urllib3.exceptions import (
    ReadTimeoutError,
    ProtocolError,
    NewConnectionError,
    MaxRetryError,
    ConnectTimeoutError
)
# Import ConnectionError and TimeoutError from requests instead
from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
    ChunkedEncodingError,
    ReadTimeout,
    ProxyError,
    Timeout as RequestsTimeoutError
)
# Import http.client exceptions for RemoteDisconnected
import http.client
from serpapi import GoogleSearch

# Configure logging
logger = logging.getLogger(__name__)

# Initialize cache directory
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

# --------- Rate Limiting Prevention Configuration ---------
# Constants for request throttling
MAX_REQUESTS_PER_MINUTE = 10  # More conservative limit
MIN_INTERVAL_BETWEEN_REQUESTS = 6  # seconds - increased from 4
MAX_RETRIES = 5  # Increased from 3
BACKOFF_FACTOR = 2.0  # Increased from 1.5
REQUEST_TIMEOUT = 60  # seconds - increased from 30 for more reliable data retrieval
CACHE_EXPIRY = 3600 * 24  # 24 hours in seconds - increased cache duration

# Global rate limiting lock
rate_limit_lock = threading.Lock()
last_request_time = time.time() - MIN_INTERVAL_BETWEEN_REQUESTS  # Initialize to allow immediate first request

# --------- Headers and User Agents for Rotation ---------
# Collection of diverse browser user agents
BROWSER_USER_AGENTS = [
    # Chrome
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.0.0 Safari/537.36',
    
    # Firefox
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/113.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/112.0',
    
    # Safari
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15',
    
    # Edge
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36 Edg/114.0.1823.43',
    
    # Mobile
    'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5672.76 Mobile Safari/537.36',
]

# Collection of accept languages for rotation
ACCEPT_LANGUAGES = [
    'en-US,en;q=0.9',
    'en-GB,en;q=0.9',
    'en-CA,en;q=0.9,fr-CA;q=0.8',
    'en-AU,en;q=0.9',
    'fr-FR,fr;q=0.9,en;q=0.8',
    'de-DE,de;q=0.9,en;q=0.8',
    'es-ES,es;q=0.9,en;q=0.8',
]

# Various referer domains to simulate different sources
REFERERS = [
    'https://trends.google.com/',
    'https://www.google.com/',
    'https://trends.google.com/trends/explore',
    'https://trends.google.com/trends/trendingsearches/daily',
    'https://analytics.google.com/',
    'https://marketingplatform.google.com/',
]

proxy = 'geo.iproyal.com:12321'
proxy_auth = 'vnkl9BGvMRlmvWfO:EjFoKHcjcchVYwZ9_country-in'
proxy_url = f'http://{proxy_auth}@{proxy}'

# Define proxies dictionary for session configuration
proxies = {
   'http': proxy_url,
   'https': proxy_url
}

# Expanded proxy list with actual proxy URLs for rotation
PROXIES = [
    proxy_url  # Add more proxy URLs here if you have multiple proxies
]

# --------- Anti-Bot Detection Techniques ---------
# Browser fingerprinting avoidance methods
BROWSER_SCREEN_SIZES = [
    {"width": 1366, "height": 768},   # Most common laptop
    {"width": 1920, "height": 1080},  # Full HD
    {"width": 1440, "height": 900},   # MacBook Pro 15"
    {"width": 1536, "height": 864},   # Common Windows laptop
    {"width": 2560, "height": 1440},  # 2K display
]

# Common time zones by region for more realistic request patterns
TIMEZONES_BY_REGION = {
    'US': [-480, -420, -360, -300, -240],  # PST, MST, CST, EST, etc.
    'EU': [0, 60, 120, 180],               # GMT, CET, EET, etc.
    'IN': [330],                           # IST
    'JP': [540],                           # JST
    'AU': [480, 570, 600],                 # AWST, ACST, AEST
}

# Common color depths for browsers
COLOR_DEPTHS = [24, 30, 48]

# Common platform information
PLATFORMS = [
    "Win32",
    "MacIntel",
    "Linux x86_64",
    "Linux armv8l",
    "iPhone",
    "iPad",
    "Android"
]

# Common browser plugins (to be carefully reported)
BROWSER_PLUGINS = ["PDF Viewer", "Chrome PDF Viewer", "Chromium PDF Viewer"]

# Human-like navigation patterns - paths that a real user might visit before trends
NAVIGATION_PATTERNS = [
    ["https://www.google.com/", "https://www.google.com/search?q={keyword}", "https://trends.google.com/trends/explore"],
    ["https://news.google.com/", "https://trends.google.com/trends/"],
    ["https://www.google.com/search?q=trending+topics", "https://trends.google.com/trends/trendingsearches/daily"],
    ["https://www.google.com/", "https://trends.google.com/"]
]

# Common tracking cookies to include
COMMON_COOKIES = {
    "NID": "value_will_be_fetched",
    "1P_JAR": "timestamp_based",
    "CONSENT": "YES+",
    "ANID": "random_value"
}

# Delays between keyboard presses for sending "human-like" input (milliseconds)
TYPING_DELAYS = {
    "min": 50,
    "max": 200,
    "backspace_chance": 0.05,
    "pause_chance": 0.1,
    "pause_min": 300,
    "pause_max": 1000
}

# Function to generate more realistic browser fingerprints
def generate_browser_fingerprint():
    """Generate a realistic browser fingerprint to avoid detection"""
    # Choose a browser family and its corresponding properties
    browser_type = random.choice(['chrome', 'firefox', 'safari', 'edge'])
    screen_size = random.choice(BROWSER_SCREEN_SIZES)
    platform = random.choice(PLATFORMS)
    
    # Generate random but valid webGL information
    webgl_vendor = "Google Inc." if browser_type in ['chrome', 'edge'] else "Intel Inc." if random.random() > 0.5 else "NVIDIA Corporation"
    webgl_renderer = random.choice([
        "ANGLE (Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0)",
        "ANGLE (NVIDIA GeForce GTX 1060 Direct3D11 vs_5_0 ps_5_0)",
        "Intel(R) Iris(TM) Plus Graphics 640",
        "ANGLE (Apple M1)"
    ])
    
    # Return complete fingerprint
    return {
        "screen": screen_size,
        "platform": platform,
        "webgl": {
            "vendor": webgl_vendor,
            "renderer": webgl_renderer
        },
        "timezone": random.choice(TIMEZONES_BY_REGION.get('IN', [330])),
        "plugins_length": random.randint(3, 8) if browser_type in ['chrome', 'firefox'] else 0
    }

# Function to simulate human-like browsing behavior
def simulate_human_browsing(session, keyword=None):
    """Simulate human-like browsing behavior before accessing trends data"""
    try:
        # Choose a random navigation pattern
        pattern = random.choice(NAVIGATION_PATTERNS)
        
        # Format URLs if keyword is provided
        if keyword:
            pattern = [url.format(keyword=keyword) if "{keyword}" in url else url for url in pattern]
        
        # Visit URLs in sequence with realistic timing
        for url in pattern:
            # Add human-like delay between page visits
            delay = random.uniform(1.5, 5.0)
            logger.debug(f"Simulating human browsing: visiting {url} (delay: {delay:.2f}s)")
            time.sleep(delay)
            
            try:
                # Make the request with a reasonable timeout
                response = session.get(url, timeout=REQUEST_TIMEOUT)
                
                # Sometimes scroll the page (simulate with a delay)
                if random.random() > 0.7:
                    scroll_time = random.uniform(0.5, 3.0)
                    logger.debug(f"Simulating scrolling for {scroll_time:.2f}s")
                    time.sleep(scroll_time)
                
                # Extract and store any cookies from the response
                if response.cookies:
                    logger.debug(f"Received {len(response.cookies)} cookies from {url}")
            except Exception as e:
                logger.warning(f"Error during human browsing simulation at {url}: {str(e)}")
                
        return True
    except Exception as e:
        logger.error(f"Error in simulate_human_browsing: {str(e)}")
        return False

# Function to set privacy-respecting but realistic cookies
def set_realistic_cookies(session):
    """Set realistic cookies that might be expected by Google"""
    try:
        # Get current timestamp for cookie freshness
        timestamp = int(time.time())
        
        # Generate semi-realistic cookie values
        cookie_values = {
            "NID": ''.join(random.choices(string.digits + string.ascii_lowercase, k=random.randint(130, 150))),
            "1P_JAR": time.strftime("%Y-%m-%d", time.gmtime(timestamp)),
            "CONSENT": f"YES+{random.randint(100, 999)}",
            "ANID": ''.join(random.choices(string.ascii_lowercase + string.digits, k=26))
        }
        
        # Set cookies in the session
        for name, value in cookie_values.items():
            session.cookies.set(name, value, domain=".google.com")
            
        logger.debug("Set realistic cookies for the session")
        return True
    except Exception as e:
        logger.error(f"Error setting realistic cookies: {str(e)}")
        return False

# Function to apply random headers to avoid detection patterns
def apply_random_headers(session):
    """Apply randomized headers to a session to avoid bot detection patterns"""
    try:
        # Generate a complete browser fingerprint
        fingerprint = generate_browser_fingerprint()
        
        # Try to use fake_useragent first
        try:
            ua = UserAgent(fallback=random.choice(BROWSER_USER_AGENTS))
            user_agent = ua.random
        except Exception:
            # If fake_useragent fails, use our predefined list
            user_agent = random.choice(BROWSER_USER_AGENTS)
        
        # Select random accept language
        accept_language = random.choice(ACCEPT_LANGUAGES)
        
        # Select random referer
        referer = random.choice(REFERERS)
        
        # Create a somewhat unique browser fingerprint appearance
        accept = random.choice([
            "application/json, text/plain, */*",
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        ])
        
        # Randomize cache-control behavior
        cache_control = random.choice([
            "max-age=0",
            "no-cache",
            "no-store, max-age=0",
            None  # Sometimes don't send this header
        ])
        
        # Basic headers that every request should have
        headers = {
            "User-Agent": user_agent,
            "Accept": accept,
            "Accept-Language": accept_language,
            "Referer": referer,
            "Origin": referer.rsplit('/', 1)[0],
            "DNT": "1" if random.random() > 0.5 else None,  # Randomly include Do Not Track
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Viewport-Width": str(fingerprint["screen"]["width"]),
            "Device-Memory": f"{random.choice([2, 4, 8])}"
        }
        
        # Add more realistic header values based on fingerprint
        headers.update({
            "Sec-Ch-Ua": f"\" Not A;Brand\";v=\"{random.randint(90, 99)}\", \"Chromium\";v=\"{random.randint(100, 114)}\"",
            "Sec-Ch-Ua-Mobile": "?0" if "Mobile" not in user_agent else "?1",
            "Sec-Ch-Ua-Platform": f"\"{fingerprint['platform']}\"",
        })
        
        # Add conditional headers
        if cache_control:
            headers["Cache-Control"] = cache_control
            
        # Add Accept-Encoding header (common in browsers)
        headers["Accept-Encoding"] = "gzip, deflate, br"
        
        # Remove None values
        headers = {k: v for k, v in headers.items() if v is not None}
        
        # Update session headers
        session.headers.update(headers)
        
        logger.debug(f"Applied enhanced randomized headers with User-Agent: {user_agent[:30]}...")
        return True
    
    except Exception as e:
        logger.error(f"Error applying random headers: {str(e)}")
        
        # Apply simple fallback headers
        session.headers.update({
            "User-Agent": BROWSER_USER_AGENTS[0],
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://trends.google.com/",
        })
        return False

# Enhanced session creation with browser fingerprinting and proxy support
def create_retry_session(use_cache=True, use_proxy=True):
    try:
        # Create a session with or without caching
        if use_cache:
            session = CachedSession(
                cache_name=os.path.join(CACHE_DIR, 'trends_cache'),
                backend='sqlite',
                expire_after=CACHE_EXPIRY
            )
        else:
            session = requests.Session()
            
        # Fix the retry configuration for this session
        fix_session_retry(session)
        
        # Configure diverse headers to avoid detection
        apply_random_headers(session)
        
        # Set realistic cookies for the session
        set_realistic_cookies(session)
        
        # Apply proxy if requested
        if use_proxy and PROXIES:
            # Get a random proxy from the list
            proxy = get_random_proxy()
            if proxy:
                # Store the proxy URL for reference
                session._proxy = proxy
                # Set the proxy in the session
                session.proxies = {
                    'http': proxy,
                    'https': proxy
                }
                logger.info(f"Session configured with proxy: {proxy}")
            else:
                logger.warning("No working proxies available, using direct connection")
        
        logger.info("Successfully created session with enhanced anti-bot protection")
        return session
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        # Return a basic session as fallback
        return requests.Session()

# Function to select a random proxy from the available options
def get_random_proxy():
    """Select a random proxy from the available options with error handling"""
    
    # Initialize failed_proxies set if it doesn't exist
    if not hasattr(get_random_proxy, 'failed_proxies'):
        get_random_proxy.failed_proxies = set()
    
    # Make sure PROXIES is not empty
    if not PROXIES:
        logger.warning("No proxies configured in PROXIES list")
        return None
    
    # Get proxies that haven't failed recently
    working_proxies = [p for p in PROXIES if p is not None and p not in get_random_proxy.failed_proxies]
    
    # If no working proxies available, reset the failed list and try all again
    if not working_proxies:
        logger.warning("No more working proxies available, resetting failed proxy list")
        get_random_proxy.failed_proxies = set()
        
        # Try again with all proxies
        working_proxies = [p for p in PROXIES if p is not None]
        
        # If still no working proxies, return None
        if not working_proxies:
            logger.error("No valid proxies available in PROXIES list")
            return None
    
    # Select a random proxy
    proxy = random.choice(working_proxies)
    logger.debug(f"Selected proxy: {proxy}")
    return proxy

# Add a function to mark a proxy as failed
def mark_proxy_as_failed(proxy):
    """Mark a proxy as failed so it won't be used for a while"""
    if not hasattr(get_random_proxy, 'failed_proxies'):
        get_random_proxy.failed_proxies = set()
    
    if proxy is not None:
        logger.warning(f"Marking proxy as failed: {proxy}")
        get_random_proxy.failed_proxies.add(proxy)
        
        # If all proxies have failed, reset
        if len(get_random_proxy.failed_proxies) >= len([p for p in PROXIES if p is not None]):
            logger.warning("All proxies have failed, resetting failed list")
            get_random_proxy.failed_proxies = set()

# Update the TrendReq initialization to handle urllib3 version differences and use proxies
def create_pytrends_instance(hl='en', tz=420, timeout=None, proxy=None, use_proxy=True):
    """Create a pytrends instance with the correct retry configuration for the urllib3 version and proxy support"""
    try:
        # Determine urllib3 version
        import urllib3
        import importlib.metadata
        
        try:
            urllib3_version = importlib.metadata.version('urllib3')
        except (ImportError, AttributeError):
            urllib3_version = getattr(urllib3, '__version__', '1.0.0')
        
        # Set up proxies list - either use the provided proxy or get a random one
        if proxy:
            # Use the specific proxy provided
            proxy_to_use = proxy
            logger.info(f"Using provided proxy: {proxy}")
        elif use_proxy and PROXIES:
            # Get a random proxy from our list with pre-validation
            proxy_to_use = get_validated_proxy()
            logger.info(f"Using validated random proxy: {proxy_to_use}")
        else:
            # Get a random proxy if specified, or None if direct connection
            proxy_to_use = get_validated_proxy() if use_proxy else None
            if proxy_to_use:
                logger.info(f"No proxy specified, using validated random proxy: {proxy_to_use}")
            else:
                logger.info("No proxy specified, using direct connection")
                # Skip the availability check when direct connection is intended
                if use_proxy:
                    logger.warning("No proxies available, forced to use direct connection")
        
        # Format proxies for pytrends
        proxies_list = [proxy_to_use] if proxy_to_use else []
        
        # Use a higher timeout value to prevent premature connection termination
        if timeout is None:
            timeout = REQUEST_TIMEOUT
        extended_timeout = max(timeout * 2, 60)  # At least 60 seconds or double the normal timeout
        
        # Configure the request args
        requests_args = {
            'verify': True,
            'timeout': (15, extended_timeout)  # (connect, read) timeout
        }
        
        # Create the TrendReq instance - do NOT pass timeout parameter directly
        pytrends = TrendReq(
            hl=hl,
            tz=tz,
            retries=3,  # Increase retries
            backoff_factor=2.0,  # More aggressive backoff
            proxies=proxies_list,
            requests_args=requests_args
        )
        
        # Replace the session with a properly configured one
        # Pass the proxy to the session creation
        session = create_retry_session(use_cache=False, use_proxy=use_proxy and proxy_to_use is not None)
        
        # If we have a proxy, make sure it's set in the session
        if proxy_to_use:
            session.proxies = {
                'http': proxy_to_use,
                'https': proxy_to_use
            }
            # Store the proxy URL for reference
            session._proxy = proxy_to_use
            # Test the proxy with a simple request to ensure it's working
            try:
                test_url = "https://trends.google.com/trends/"
                logger.debug(f"Testing proxy connection to {test_url}")
                # Use a short timeout for the test to fail fast if there's an issue
                test_response = session.get(test_url, timeout=(5, 10))
                if test_response.status_code == 200:
                    logger.info(f"Proxy connection test successful: {proxy_to_use}")
                else:
                    logger.warning(f"Proxy connection test returned status {test_response.status_code}: {proxy_to_use}")
            except Exception as e:
                logger.warning(f"Proxy connection test failed for {proxy_to_use}: {str(e)}")
                # If test failed, try to get another proxy
                mark_proxy_as_failed(proxy_to_use)
                new_proxy = get_validated_proxy()
                if new_proxy:
                    logger.info(f"Switching to backup proxy: {new_proxy}")
                    session.proxies = {
                        'http': new_proxy,
                        'https': new_proxy
                    }
                    session._proxy = new_proxy
        
        # Configure the session with proper keep-alive settings to prevent disconnects
        session.headers.update({
            'Connection': 'keep-alive',
            'Keep-Alive': '300'  # Keep connection alive for 300 seconds
        })
            
        pytrends.requests_session = session
        
        return pytrends
        
    except Exception as e:
        logger.error(f"Error creating PyTrends instance: {str(e)}")
        
        # Fallback to a basic configuration
        try:
            # Try to create a basic instance - with proxy if available, otherwise direct
            proxy_to_use = get_validated_proxy() if use_proxy else None
            if proxy_to_use:
                logger.info(f"Fallback: Using validated random proxy: {proxy_to_use}")
            else:
                logger.info("Fallback: Using direct connection (no proxy)")
                
            proxies_list = [proxy_to_use] if proxy_to_use else []
            
            # Create with simple parameters but longer timeout
            extended_timeout = 60 if timeout is None else max(timeout * 2, 60)
            requests_args = {
                'verify': True,
                'timeout': (15, extended_timeout)  # (connect, read) timeout
            }
            
            pytrends = TrendReq(
                hl=hl,
                tz=tz,
                geo='IN',
                proxies=proxies_list,
                requests_args=requests_args
            )
            
            # Configure session
            session = create_retry_session(use_cache=False, use_proxy=use_proxy and proxy_to_use is not None)
            if proxy_to_use:
                session.proxies = {
                    'http': proxy_to_use,
                    'https': proxy_to_use
                }
                session._proxy = proxy_to_use
            
            # Add keep-alive to prevent connection closing
            session.headers.update({
                'Connection': 'keep-alive',
                'Keep-Alive': '300'
            })
            
            pytrends.requests_session = session
            
            return pytrends
        except Exception as fallback_err:
            logger.error(f"Failed to create fallback PyTrends instance: {str(fallback_err)}")
            raise

# Function to get a validated proxy that actually works
def get_validated_proxy():
    """Get a random proxy and validate it actually works before returning"""
    # Try up to 3 different proxies
    for attempt in range(3):
        proxy = get_random_proxy()
        if not proxy:
            logger.warning("No proxies available")
            return None
            
        # Test if the proxy actually works
        try:
            logger.debug(f"Testing proxy {proxy}")
            test_session = requests.Session()
            test_session.proxies = {
                'http': proxy,
                'https': proxy
            }
            # Use a simple test URL with a short timeout
            test_urls = [
                "https://www.google.com",
                "https://trends.google.com"
            ]
            
            # Try multiple URLs in case one is blocked
            for test_url in test_urls:
                try:
                    # Use a very short timeout to fail fast
                    response = test_session.get(test_url, timeout=(5, 5))
                    if response.status_code == 200:
                        logger.info(f"Proxy validation successful on {test_url}: {proxy}")
                        return proxy
                    else:
                        logger.warning(f"Proxy validation failed with status {response.status_code} on {test_url}: {proxy}")
                except Exception as url_error:
                    logger.warning(f"Proxy test failed for {test_url}: {str(url_error)}")
                    continue
            
            # If we get here, all test URLs failed
            logger.warning(f"All test URLs failed for proxy: {proxy}")
            mark_proxy_as_failed(proxy)
            
        except Exception as e:
            logger.warning(f"Proxy validation failed with error: {str(e)}")
            mark_proxy_as_failed(proxy)
    
    # Try direct connection as last resort
    logger.warning("No working proxies found, trying direct connection")
    return None

# Function to add random delay to avoid rate limiting
def add_random_delay(min_seconds=1, max_seconds=3):
    """Add a small random delay between requests to avoid rate limiting"""
    delay = random.uniform(min_seconds, max_seconds)
    time.sleep(delay)
    return delay

# Improved backoff with jitter for rate limit handling
def backoff_with_jitter(attempt, base_delay=5, max_delay=30):
    """
    Calculate exponential backoff time with jitter to prevent thundering herd problem
    """
    exponential_delay = min(base_delay * (2 ** attempt), max_delay)
    jitter = random.uniform(0, exponential_delay / 2)
    return exponential_delay + jitter

# Function to get cookies for Google Trends
def get_google_cookies():
    """Get Google cookies with human-like browsing behavior"""
    try:
        # Create a session specifically for getting cookies
        session = create_retry_session(use_cache=False)
        
        # First simulate some normal browsing behavior
        simulate_human_browsing(session)
        
        # Then visit Google Trends with realistic timing
        add_random_delay(1, 3)
        response = session.get("https://trends.google.com/trends/", timeout=REQUEST_TIMEOUT)
        
        if response.status_code == 200:
            # Before returning cookies, possibly interact with the page
            if random.random() > 0.7:  # 30% chance to interact
                # Simulate a click or interaction by making another request
                add_random_delay(0.5, 2)
                session.get("https://trends.google.com/trends/explore", timeout=REQUEST_TIMEOUT)
            
            # Extract and return cookies
            cookies = session.cookies.get_dict()
            logger.info(f"Successfully obtained {len(cookies)} Google cookies")
            return cookies
        else:
            logger.warning(f"Failed to get Google cookies, status code: {response.status_code}")
            return {}
    except Exception as e:
        logger.error(f"Error getting Google cookies: {str(e)}")
        return {}

# --------- Cache Management ---------
def get_cache_key(keywords, timeframe, geo, analysis_type='default'):
    """Generate a unique cache key based on request parameters"""
    if isinstance(keywords, list):
        keywords_str = ','.join(sorted(keywords))
    else:
        keywords_str = str(keywords)
        
    key_parts = [keywords_str, timeframe, geo, analysis_type]
    key_string = '_'.join(key_parts)
    return f"trends_{hashlib.md5(key_string.encode()).hexdigest()}"

def get_cached_data(keywords, timeframe, geo, analysis_type='default'):
    """Try to get cached data for this request"""
    cache_key = get_cache_key(keywords, timeframe, geo, analysis_type)
    cached_result = cache.get(cache_key)
    
    if cached_result:
        logger.info(f"Cache hit for {cache_key}")
        return cached_result
    
    # Also check file cache as fallback
    file_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Store in Django cache for faster future access
                cache.set(cache_key, data, CACHE_EXPIRY)
                logger.info(f"File cache hit for {cache_key}")
                return data
        except Exception as e:
            logger.error(f"Error reading cache file: {str(e)}")
    
    return None

def save_to_cache(data, keywords, timeframe, geo, analysis_type='default'):
    """Save data to cache"""
    cache_key = get_cache_key(keywords, timeframe, geo, analysis_type)
    
    # Save to Django cache
    cache.set(cache_key, data, CACHE_EXPIRY)
    
    # Also save to file cache as backup
    file_path = os.path.join(CACHE_DIR, f"{cache_key}.json")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        logger.info(f"Saved data to cache: {cache_key}")
    except Exception as e:
        logger.error(f"Error saving to cache file: {str(e)}")

# --------- Rate Limiting Prevention ---------
def enforce_rate_limit():
    """Enforce stricter rate limiting to avoid 429 errors"""
    global last_request_time
    
    with rate_limit_lock:
        current_time = time.time()
        elapsed = current_time - last_request_time
        
        if elapsed < MIN_INTERVAL_BETWEEN_REQUESTS:
            sleep_time = MIN_INTERVAL_BETWEEN_REQUESTS - elapsed + random.uniform(0.5, 2.0)  # Added jitter
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
            
        last_request_time = time.time()

# Function to generate fallback time trends data when API fails
def generate_fallback_trends_data(keywords, timeframe):
    """Generate fallback time trends data when the API fails to return results"""
    logger.warning("Generating fallback time trends data")
    
    # Determine date range based on timeframe
    now = datetime.datetime.now()
    
    if "now" in timeframe:
        # Handle "now X-d" format
        days_match = re.search(r'now (\d+)-d', timeframe)
        if days_match:
            days = int(days_match.group(1))
            start_date = now - datetime.timedelta(days=days)
            periods = days
            freq = 'D'  # Daily
        else:
            # Default to 7 days
            start_date = now - datetime.timedelta(days=7)
            periods = 7
            freq = 'D'  # Daily
    elif "today" in timeframe:
        # Handle "today X-m" and "today X-y" formats
        months_match = re.search(r'today (\d+)-m', timeframe)
        years_match = re.search(r'today (\d+)-y', timeframe)
        
        if months_match:
            months = int(months_match.group(1))
            start_date = now - datetime.timedelta(days=30*months)
            periods = months
            freq = 'ME'  # Monthly
        elif years_match:
            years = int(years_match.group(1))
            start_date = now - datetime.timedelta(days=365*years)
            periods = years * 12
            freq = 'ME'  # Monthly
        else:
            # Default to 1 year
            start_date = now - datetime.timedelta(days=365)
            periods = 12
            freq = 'ME'  # Monthly
    else:
        # Default to 1 year
        start_date = now - datetime.timedelta(days=365)
        periods = 12
        freq = 'ME'  # Monthly
    
    # Generate date range
    try:
        dates = pd.date_range(start=start_date, periods=periods, freq=freq)
        
        # Generate data for each keyword
        data = {}
        for kw in keywords:
            # Generate random values with an upward or downward trend
            trend_direction = random.choice([1, -1])  # 1 for upward, -1 for downward
            trend_strength = random.uniform(0.1, 0.3)  # How strong the trend is
            
            # Start with a base value between 30 and 70
            base_value = random.randint(30, 70)
            values = []
            
            for i in range(periods):
                # Add trend component
                trend = i * trend_strength * trend_direction
                
                # Add randomness
                noise = random.uniform(-10, 10)
                
                # Calculate value with constraints
                value = max(5, min(100, base_value + trend + noise))
                values.append(int(value))
            
            data[kw] = values
        
        # Create the DataFrame
        df = pd.DataFrame(data, index=dates)
        
        # Add isPartial column
        df['isPartial'] = False
        
        # Mark as fallback data
        if not hasattr(df, 'is_fallback'):
            setattr(df, 'is_fallback', True)
        
        logger.info(f"Generated fallback data with {len(df)} points for {len(keywords)} keywords")
        return df
    
    except Exception as e:
        logger.error(f"Error generating fallback data: {str(e)}")
        
        # Create a very basic fallback if all else fails
        try:
            dates = pd.date_range(start=(datetime.datetime.now() - datetime.timedelta(days=365*5)).strftime('%Y-%m-%d'), periods=12, freq='M')
            data = {kw: [random.randint(20, 80) for _ in range(12)] for kw in keywords}
            df = pd.DataFrame(data, index=dates)
            df['isPartial'] = False
            return df
        except:
            # Empty DataFrame as last resort
            return pd.DataFrame()

# Function to generate fallback region data when API fails
def generate_fallback_region_data(keywords, geo):
    """Generate fallback region data when the API fails to return results"""
    logger.warning(f"Generating fallback region data for {geo}")
    
    # Create a basic fallback dataset with some regions
    try:
        # For India
        if geo == 'IN':
            regions = [
                "Maharashtra", "Delhi", "Karnataka", "Tamil Nadu", "Telangana",
                "Gujarat", "Uttar Pradesh", "West Bengal", "Rajasthan", "Kerala"
            ]
        # For US
        elif geo == 'US':
            regions = [
                "California", "New York", "Texas", "Florida", "Illinois",
                "Pennsylvania", "Ohio", "Georgia", "North Carolina", "Michigan"
            ]
        # For other countries, use generic region names
        else:
            regions = [f"Region {i+1}" for i in range(10)]
        
        # Create a DataFrame with random values
        data = {}
        for kw in keywords:
            # Generate random values between 0 and 100
            values = [random.randint(20, 100) for _ in range(len(regions))]
            data[kw] = values
        
        # Create DataFrame
        df = pd.DataFrame(data, index=regions)
        
        # Mark as fallback data
        if not hasattr(df, 'is_fallback'):
            setattr(df, 'is_fallback', True)
        
        logger.info(f"Generated fallback region data with {len(df)} regions for {len(keywords)} keywords")
        return df
    
    except Exception as e:
        logger.error(f"Error generating fallback region data: {str(e)}")
        # Return empty DataFrame as last resort
        return pd.DataFrame()

# Optimized function to fetch trend data with rate limiting prevention
def get_trends_data(pytrends, keywords, timeframe, geo, max_retries=MAX_RETRIES):
    """
    Fetch time trends data with retry logic and rate limiting prevention
    """
    enforce_rate_limit()
    
    # Check if we need to fix the session's retry mechanism due to urllib3 version issues
    try:
        # Safely access the retry mechanism and check for potential issues
        if hasattr(pytrends.requests_session, 'adapters'):
            adapter = list(pytrends.requests_session.adapters.values())[0]
            if hasattr(adapter, 'max_retries') and not isinstance(adapter.max_retries, bool):
                # It seems we already have a configured adapter, no need to fix
                logger.debug("Session already has a configured retry adapter")
            else:
                # Create a new retry adapter
                logger.info("Configuring session with correct retry adapter")
                fix_session_retry(pytrends.requests_session)
    except Exception as retry_err:
        logger.warning(f"Error checking/fixing retry configuration: {str(retry_err)}")
        # Create a new session with properly configured retry
        try:
            logger.info("Creating fresh session with correct retry configuration")
            pytrends.requests_session = create_retry_session(use_cache=False)
        except Exception as sess_err:
            logger.warning(f"Error creating fresh session: {str(sess_err)}")
    
    # Add small delay to make the request pattern look more natural
    add_random_delay(0.8, 2.2)
    
    # Occasionally simulate a user clicking around first
    if random.random() > 0.7:  # 30% chance
        try:
            # Make a random request to simulate a user exploring the interface
            random_page = random.choice([
                "https://trends.google.com/trends/explore",
                "https://trends.google.com/trends/trendingsearches/daily",
                "https://trends.google.com/trends/hottrends"
            ])
            pytrends.requests_session.get(random_page, timeout=REQUEST_TIMEOUT)
            logger.debug(f"Simulated user exploring interface at {random_page}")
            
            # Add natural delay after "clicking"
            add_random_delay(1, 3)
        except Exception as click_error:
            logger.debug(f"Error simulating user interface interaction: {str(click_error)}")
    
    connection_errors = 0
    max_connection_errors = 3
    
    for attempt in range(max_retries):
        try:
            # Build the payload with error handling
            try:
                # Add jitter delay as if user is selecting parameters
                add_random_delay(0.5, 1.5)
                
                # If this is a retry attempt, try with slightly different parameters
                modified_timeframe = timeframe
                if attempt > 0:
                    # Try to adjust the timeframe slightly to improve chance of getting data
                    if timeframe == 'today 5-y':
                        modified_timeframe = random.choice(['today 3-y', 'today 4-y', 'today 5-y'])
                    elif timeframe == 'today 3-y':
                        modified_timeframe = random.choice(['today 2-y', 'today 3-y', 'today 4-y'])
                    elif timeframe == 'today 1-y':
                        modified_timeframe = random.choice(['today 9-m', 'today 1-y', 'today 15-m'])
                    # Add shorter timeframes for better chance of getting data
                    elif timeframe == 'today 1-m':
                        modified_timeframe = random.choice(['today 1-m', 'today 3-m', 'now 7-d'])
                    
                    if modified_timeframe != timeframe:
                        logger.info(f"Retry attempt {attempt+1}: trying with modified timeframe {modified_timeframe}")
                        timeframe = modified_timeframe
                
                # Try building with different user-agent and proxy for better success
                if attempt > 0:
                    # Use a direct connection on second attempt (no proxy)
                    if attempt == 1:
                        logger.info("Retry attempt 2: using direct connection (no proxy)")
                        pytrends.requests_session.proxies = {}
                    # Switch proxy on third+ attempt
                    elif attempt >= 2:
                        # Get a new proxy
                        current_proxy = None
                        if hasattr(pytrends.requests_session, 'proxies'):
                            current_proxy = pytrends.requests_session.proxies.get('http')
                        
                        # If we had a proxy and it failed, mark it as failed
                        if current_proxy:
                            mark_proxy_as_failed(current_proxy)
                        
                        # Use a validated proxy to avoid RemoteDisconnected errors
                        new_proxy = get_validated_proxy()
                        if new_proxy:
                            # Update the session proxy
                            pytrends.requests_session.proxies = {"http": new_proxy, "https": new_proxy}
                            logger.info(f"Retry {attempt+1}: using different validated proxy: {new_proxy}")
                            
                            # Refresh connection keep-alive settings
                            pytrends.requests_session.headers.update({
                                'Connection': 'keep-alive',
                                'Keep-Alive': '300'
                            })
                        else:
                            # Use no proxy if none available
                            pytrends.requests_session.proxies = {}
                            logger.info(f"Retry {attempt+1}: using direct connection (no available proxy)")
                
                # Build the payload - catch specific connection errors
                try:
                    pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
                except (RequestsConnectionError, RequestsTimeoutError, requests.exceptions.ConnectionError,
                       ChunkedEncodingError, ReadTimeout,
                       ProtocolError, http.client.RemoteDisconnected) as conn_err:
                    logger.warning(f"Connection error during build_payload: {str(conn_err)}")
                    connection_errors += 1
                    
                    if connection_errors >= max_connection_errors:
                        logger.error(f"Too many connection errors ({connection_errors}), falling back to cached data")
                        return generate_fallback_trends_data(keywords, timeframe)
                        
                    # Try again with a different proxy after a longer delay
                    delay = backoff_with_jitter(attempt + connection_errors, base_delay=10, max_delay=60)
                    logger.info(f"Connection error recovery: waiting {delay:.2f} seconds before retry")
                    time.sleep(delay)
                    
                    # Create a fresh session with a new proxy
                    pytrends.requests_session = create_retry_session(use_cache=False, use_proxy=True)
                    new_proxy = get_validated_proxy()
                    if new_proxy:
                        pytrends.requests_session.proxies = {"http": new_proxy, "https": new_proxy}
                        logger.info(f"Using new validated proxy after connection error: {new_proxy}")
                    
                    # Try again with the new session
                    pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
                
            except Exception as build_error:
                logger.warning(f"Error building payload: {str(build_error)}")
                
                # Check if this is a RemoteDisconnected error
                if "RemoteDisconnected" in str(build_error) or "ConnectionError" in str(build_error):
                    logger.warning("RemoteDisconnected error detected during build_payload")
                    connection_errors += 1
                    
                    if connection_errors >= max_connection_errors:
                        logger.error(f"Too many connection errors ({connection_errors}), falling back to cached data")
                        return generate_fallback_trends_data(keywords, timeframe)
                        
                    # Wait with exponential backoff
                    delay = backoff_with_jitter(attempt + connection_errors, base_delay=10, max_delay=60)
                    logger.info(f"RemoteDisconnected recovery: waiting {delay:.2f} seconds before retry with new proxy")
                    time.sleep(delay)
                    
                    # Create a fresh pytrends instance with a validated proxy
                    new_proxy = get_validated_proxy()
                    if new_proxy:
                        pytrends = create_pytrends_instance(proxy=new_proxy)
                        logger.info(f"Created new PyTrends instance with validated proxy: {new_proxy}")
                    else:
                        pytrends = create_pytrends_instance(use_proxy=False)
                        logger.info("Created new PyTrends instance with direct connection")
                    
                    # Try again with the new instance
                    continue
                
                # If the error is about parsing JSON, it might be an IP block or rate limit
                if "json" in str(build_error).lower():
                    if attempt < max_retries - 1:
                        # Wait longer and try with a different approach
                        delay = backoff_with_jitter(attempt, base_delay=15, max_delay=60)
                        logger.warning(f"Possible IP block, retrying in {delay:.2f} seconds")
                        time.sleep(delay)
                        
                        # Clear session and try with different proxy/approach
                        pytrends.requests_session = create_retry_session(use_cache=False)
                        add_random_delay(1, 3)
                        
                        # Try direct connection on even attempts, proxy on odd
                        if attempt % 2 == 0:
                            # Try direct
                            pytrends.requests_session.proxies = {}
                            logger.info("Trying with direct connection")
                        else:
                            # Try with a new proxy
                            new_proxy = get_validated_proxy()
                            if new_proxy:
                                pytrends.requests_session.proxies = {"http": new_proxy, "https": new_proxy}
                                logger.info(f"Trying with new validated proxy: {new_proxy}")
                        
                        continue
                    else:
                        # If we've tried everything and still fail, return fallback data
                        logger.warning("Unable to build payload after all retries, generating fallback data")
                        return generate_fallback_trends_data(keywords, timeframe)
                
                # If we've already made multiple attempts, try a clean approach with a new proxy
                if attempt > 0:
                    logger.info("Creating fresh session with new proxy for payload building")
                    # Create a fresh session
                    session = create_retry_session(use_cache=False)
                    
                    # Get a new proxy, preferring a different one if possible
                    current_proxy = None
                    if hasattr(pytrends.requests_session, '_proxy'):
                        current_proxy = pytrends.requests_session._proxy
                    
                    new_proxy = get_validated_proxy()
                    if new_proxy:
                        logger.info(f"Switching to different validated proxy: {new_proxy}")
                        proxy_list = [new_proxy] if new_proxy else []
                        # Create a new pytrends instance with the new proxy
                        try:
                            new_pytrends = TrendReq(
                                hl='en',
                                tz=420,
                                geo='IN',
                                proxies=proxy_list,
                                retries=0
                            )
                            # Use the new pytrends instance
                            pytrends = new_pytrends
                            logger.info("Successfully created new pytrends instance with different proxy")
                        except Exception as proxy_err:
                            logger.warning(f"Failed to create new pytrends with proxy: {str(proxy_err)}")
                    
                    # Still update the session in the existing pytrends
                    pytrends.requests_session = session
                
                # Add longer delay before retrying
                add_random_delay(2, 4.5)
                
                # Try again with the new session
                pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
            
            # Simulate user waiting for results (with jitter)
            add_random_delay(0.8, 2.2)
            
            # Get interest over time data - protect against connection errors
            try:
                interest_over_time_df = pytrends.interest_over_time()
                logger.info(f"Retrieved interest_over_time data for {keywords}, empty: {interest_over_time_df.empty}")
            except (RequestsConnectionError, RequestsTimeoutError, requests.exceptions.ConnectionError,
                   ChunkedEncodingError, ReadTimeout,
                   ProtocolError, http.client.RemoteDisconnected) as conn_err:
                logger.warning(f"Connection error during interest_over_time: {str(conn_err)}")
                connection_errors += 1
                
                if connection_errors >= max_connection_errors:
                    logger.error(f"Too many connection errors ({connection_errors}), falling back to cached data")
                    return generate_fallback_trends_data(keywords, timeframe)
                
                # Wait with exponential backoff
                delay = backoff_with_jitter(attempt + connection_errors, base_delay=10, max_delay=60)
                logger.info(f"Connection error recovery: waiting {delay:.2f} seconds before retry")
                time.sleep(delay)
                
                # Try with a different proxy before retrying
                if attempt < max_retries - 1:
                    # Create a fresh pytrends instance with a validated proxy
                    new_proxy = get_validated_proxy()
                    if new_proxy:
                        pytrends = create_pytrends_instance(proxy=new_proxy)
                        logger.info(f"Created new PyTrends instance with validated proxy: {new_proxy}")
                    else:
                        pytrends = create_pytrends_instance(use_proxy=False)
                        logger.info("Created new PyTrends instance with direct connection")
                    
                    # Continue to the next attempt
                    continue
                else:
                    # Last attempt failed with connection error, return fallback data
                    logger.warning("Max retries reached with connection errors, using fallback data")
                    return generate_fallback_trends_data(keywords, timeframe)
            except Exception as e:
                logger.error(f"Error retrieving interest_over_time data: {str(e)}")
                
                # Check specifically for the "No time series data available" error
                error_msg = str(e).lower()
                if "no time series data" in error_msg:
                    logger.warning("Encountered 'No time series data available' error")
                    
                    if attempt < max_retries - 1:
                        # Try a different approach with shorter timeframe
                        shorter_timeframes = ['today 1-m', 'today 3-m', 'now 7-d', 'now 1-d']
                        modified_timeframe = random.choice(shorter_timeframes)
                        logger.info(f"Trying with shorter timeframe: {modified_timeframe}")
                        
                        # Add delay to avoid rate limiting
                        add_random_delay(2, 5)
                        
                        # Try with a new session and different region
                        try:
                            logger.info("Creating new session for retry")
                            pytrends.requests_session = create_retry_session(use_cache=False)
                            pytrends.build_payload(keywords, timeframe=modified_timeframe, geo=geo)
                            interest_over_time_df = pytrends.interest_over_time()
                            logger.info(f"Retry successful with modified timeframe: {modified_timeframe}")
                        except Exception as retry_err:
                            logger.warning(f"Retry failed with modified timeframe: {str(retry_err)}")
                            
                            if attempt == max_retries - 2:  # Last retry
                                # For final retry, use fallback data
                                logger.warning("Final retry failed, using fallback data")
                                return generate_fallback_trends_data(keywords, timeframe)
                            
                            # Continue to next retry attempt
                            continue
                    else:
                        # If all retries failed, provide fallback data
                        logger.warning("All retries failed with 'No time series data available', using fallback data")
                        return generate_fallback_trends_data(keywords, timeframe)
                else:
                    # For other errors, retry with different parameters if attempts remain
                    if attempt < max_retries - 1:
                        logger.warning(f"Unexpected error, will retry: {str(e)}")
                        # Add backoff delay
                        delay = backoff_with_jitter(attempt, base_delay=10, max_delay=60)
                        time.sleep(delay)
                        
                        # Try with a new pytrends instance
                        new_proxy = get_validated_proxy()
                        if new_proxy:
                            pytrends = create_pytrends_instance(proxy=new_proxy)
                            logger.info(f"Created new PyTrends instance with validated proxy: {new_proxy}")
                        else:
                            pytrends = create_pytrends_instance(use_proxy=False)
                            logger.info("Created new PyTrends instance with direct connection")
                            
                        continue
                    else:
                        # Last retry attempt failed, use fallback data
                        logger.warning("All retries failed with unexpected errors, using fallback data")
                        return generate_fallback_trends_data(keywords, timeframe)
            
            # Check if we got valid data
            if interest_over_time_df is None or interest_over_time_df.empty:
                logger.warning("No data returned (empty dataframe)")
                
                if attempt < max_retries - 1:
                    # Try again with a different approach
                    logger.info(f"Retry attempt {attempt+1}/{max_retries}")
                    
                    # Add longer delay with backoff for empty results
                    delay = backoff_with_jitter(attempt, base_delay=10, max_delay=45)
                    logger.info(f"Waiting {delay:.2f} seconds before retry")
                    time.sleep(delay)
                    
                    # Continue to next retry
                    continue
                else:
                    # Last retry attempt resulted in empty data, use fallback data
                    logger.warning("All retries resulted in empty data, using fallback data")
                    return generate_fallback_trends_data(keywords, timeframe)
            
            # Success! Process the data
            result = interest_over_time_df
            logger.info(f"Successfully retrieved and processed trends data with {len(result)} points")
            return result
        
        except Exception as e:
            logger.error(f"Error in get_trends_data: {str(e)}")
            
            # Check for connection-related errors
            if "RemoteDisconnected" in str(e) or "ConnectionError" in str(e) or "ProtocolError" in str(e):
                logger.warning("Connection error detected in overall try/except block")
                connection_errors += 1
                
                if connection_errors >= max_connection_errors:
                    logger.error(f"Too many connection errors ({connection_errors}), falling back to cached data")
                    return generate_fallback_trends_data(keywords, timeframe)
            
            if attempt < max_retries - 1:
                # Calculate backoff time
                delay = backoff_with_jitter(attempt, base_delay=10, max_delay=60)
                logger.warning(f"Error occurred, retrying in {delay:.2f} seconds ({attempt+1}/{max_retries})")
                time.sleep(delay)
                
                # Try with a completely fresh session and instance for the next attempt
                try:
                    logger.info("Creating completely fresh PyTrends instance for next attempt")
                    pytrends = create_pytrends_instance()
                except Exception as instance_err:
                    logger.error(f"Failed to create fresh PyTrends instance: {str(instance_err)}")
            else:
                # If this was the last attempt, return fallback data
                logger.warning("All retry attempts failed, generating fallback data")
                return generate_fallback_trends_data(keywords, timeframe)
    
    # If we exhausted all retries, provide fallback data
    logger.warning(f"Exhausted all {max_retries} retry attempts, generating fallback data")
    return generate_fallback_trends_data(keywords, timeframe)

# Function to get related queries
def get_related_queries(pytrends, keywords, timeframe, geo, max_retries=MAX_RETRIES):
    """
    Fetch related queries with retry logic and rate limiting prevention
    """
    enforce_rate_limit()
    
    # Add small delay to make the request pattern look more natural
    add_random_delay(0.6, 2.0)
    
    for attempt in range(max_retries):
        try:
            # Build the payload (if not already built)
            try:
                # Add small delay like a user selecting options
                add_random_delay(0.4, 1.3)
                
                pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
            except Exception as build_error:
                logger.warning(f"Error building payload, may be already built: {str(build_error)}")
                
                # If multiple retries, try with fresh session and different proxy
                if attempt > 0:
                    logger.info("Creating fresh session with new proxy for related queries")
                    # Create a fresh session
                    session = create_retry_session(use_cache=False)
                    
                    # Try with a different proxy
                    current_proxy = None
                    if hasattr(pytrends.requests_session, '_proxy'):
                        current_proxy = pytrends.requests_session._proxy
                    
                    new_proxy = get_random_proxy()
                    if new_proxy:
                        logger.info(f"Switching to different proxy for related queries: {new_proxy}")
                        proxy_list = [new_proxy] if new_proxy else []
                        try:
                            new_pytrends = TrendReq(
                                hl='en',
                                tz=420,
                                timeout=REQUEST_TIMEOUT,
                                proxies=proxy_list,
                                retries=0
                            )
                            pytrends = new_pytrends
                            logger.info("Created new pytrends instance for related queries")
                        except Exception as proxy_err:
                            logger.warning(f"Failed to create new pytrends: {str(proxy_err)}")
                    
                    pytrends.requests_session = session
                    add_random_delay(1.5, 3.5)
                    
                    # Try again
                    pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
            
            # Add delay like a user clicking on related queries tab
            add_random_delay(0.7, 1.7)
            
            # Get related queries
            related_queries = pytrends.related_queries()
            
            if not related_queries or all(related_queries[kw] is None for kw in related_queries):
                logger.warning(f"No related queries available for {keywords} in {geo}")
                return {}
            
            # Simulate a user looking at related queries    
            if random.random() > 0.7:  # 30% chance to interact
                add_random_delay(0.8, 2.2)
                logger.debug("Simulating user examining related queries")
                
            return related_queries
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Handle specific errors
            if "429" in error_msg or "too many requests" in error_msg:
                if attempt < max_retries - 1:
                    delay = backoff_with_jitter(attempt, base_delay=10, max_delay=60)  # Increased delays
                    logger.warning(f"Rate limit hit, retrying in {delay:.2f} seconds (attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                    
                    # If we hit a rate limit, refresh the session with new fingerprints and proxy
                    try:
                        logger.info("Refreshing session after rate limit with new proxy")
                        current_proxy = None
                        if hasattr(pytrends.requests_session, '_proxy'):
                            current_proxy = pytrends.requests_session._proxy
                        
                        # Try to get a completely different proxy
                        new_proxy = get_random_proxy()
                        if new_proxy:
                            logger.info(f"Switching to different proxy after rate limit: {new_proxy}")
                            proxy_list = [new_proxy] if new_proxy else []
                            
                            # Create a new session with the new proxy
                            session = create_retry_session(use_cache=False)
                            
                            # Try to create a new pytrends instance with the new proxy
                            try:
                                new_pytrends = TrendReq(
                                    hl='en',
                                    tz=420,
                                    timeout=REQUEST_TIMEOUT,
                                    proxies=proxy_list,
                                    retries=0
                                )
                                # Use the new pytrends instance
                                pytrends = new_pytrends
                                logger.info("Successfully created new pytrends instance after rate limit")
                            except Exception as proxy_err:
                                logger.warning(f"Failed to create new pytrends with proxy: {str(proxy_err)}")
                                # Just update the session in the existing pytrends
                                pytrends.requests_session = session
                        else:
                            # Just create a new session with the existing proxy
                            session = create_retry_session(use_cache=False)
                            pytrends.requests_session = session
                    except Exception as sess_err:
                        logger.warning(f"Error refreshing session: {str(sess_err)}")
                else:
                    logger.error(f"Rate limit persists after {max_retries} attempts")
                    return {}
            else:
                logger.error(f"Error fetching related queries: {str(e)}")
                if attempt < max_retries - 1:
                    delay = backoff_with_jitter(attempt, base_delay=5, max_delay=40)  # Increased delays
                    logger.info(f"Retrying after {delay:.2f} seconds (attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                else:
                    return {}
    
    return {}  # Return empty dict if all retries fail

# Convert DataFrame to JSON
def dataframe_to_json(df, date_format='%Y-%m-%d %H:%M:%S'):
    """
    Convert pandas DataFrame to JSON format
    """
    import pandas as pd
    
    # Handle the case where df is already a list
    if isinstance(df, list):
        logger.info("Data is already in list format, returning as is")
        return df
        
    # Check if we have a DataFrame
    if df is None:
        logger.warning("Received None instead of DataFrame in dataframe_to_json")
        return []
        
    # Handle the empty DataFrame case
    if not hasattr(df, 'empty'):
        logger.warning(f"Input is not a DataFrame: {type(df)}")
        # Try to convert to a DataFrame if possible
        try:
            if isinstance(df, dict):
                df = pd.DataFrame.from_dict(df)
            else:
                # Return as is if we can't convert
                logger.error("Cannot convert input to DataFrame")
                return [] if df is None else df
        except Exception as convert_err:
            logger.error(f"Error converting to DataFrame: {str(convert_err)}")
            return [] if df is None else df
            
    # Now we should have a DataFrame
    if df.empty:
        logger.warning("DataFrame is empty")
        return []
    
    # Handle different DatetimeIndex formats
    if hasattr(df.index, 'strftime'):
        # If df.index is a DatetimeIndex or similar
        try:
            # Try to convert to string with the given format
            result = []
            for date, row in df.iterrows():
                try:
                    date_str = date.strftime(date_format)
                except Exception:
                    date_str = str(date)
                
                data_point = {"date": date_str}
                
                # Add values for each column
                for column in df.columns:
                    try:
                        value = row[column]
                        # Handle NaN/None values
                        if pd.isna(value):
                            data_point[column] = 0
                        else:
                            # Try to convert numpy values to Python native types
                            try:
                                if hasattr(value, 'item'):
                                    value = value.item()
                                data_point[column] = value
                            except Exception:
                                data_point[column] = float(value) if isinstance(value, (int, float)) else str(value)
                    except Exception as e:
                        logger.warning(f"Error processing column {column}: {str(e)}")
                        data_point[column] = 0
                
                result.append(data_point)
            return result
        except Exception as e:
            logger.error(f"Error converting datetime index: {str(e)}")
    
    # For non-datetime indices
    result = []
    try:
        for idx, row in df.iterrows():
            data_point = {"index": str(idx)}
            
            # Add values for each column
            for column in df.columns:
                try:
                    value = row[column]
                    # Handle NaN/None values
                    if pd.isna(value):
                        data_point[column] = 0
                    else:
                        # Try to convert numpy values to Python native types
                        try:
                            if hasattr(value, 'item'):
                                value = value.item()
                            data_point[column] = value
                        except Exception:
                            data_point[column] = float(value) if isinstance(value, (int, float)) else str(value)
                except Exception as e:
                    logger.warning(f"Error processing column {column}: {str(e)}")
                    data_point[column] = 0
            
            result.append(data_point)
    except Exception as e:
        logger.error(f"Error processing DataFrame: {str(e)}")
        # Try a simple conversion as last resort
        try:
            import json
            result = json.loads(df.to_json(orient='records', date_format='iso'))
            logger.info("Used simplified DataFrame conversion as fallback")
        except Exception as json_err:
            logger.error(f"Error in simplified conversion: {str(json_err)}")
            return []
    
    return result

# Helper function to process regions/cities data
def process_region_data(region_df):
    if region_df.empty:
        logger.warning("Empty DataFrame received for region data")
        return []
    
    # Debug information
    logger.info(f"Processing region data with shape: {region_df.shape}")
    logger.info(f"Region data columns: {region_df.columns.tolist()}")
    logger.info(f"First few regions: {region_df.index[:5].tolist() if len(region_df) > 5 else region_df.index.tolist()}")
    
    # Group data by region name instead of flattening it
    result = {}
    
    try:
        # First get all unique regions and keywords
        regions = region_df.index.tolist()
        keywords = [col for col in region_df.columns if col != 'isPartial' and col != 'geoCode']  # Exclude non-data columns
        
        logger.info(f"Found {len(regions)} regions and {len(keywords)} keywords")
        
        # Create a properly structured format for bar chart visualization
        for region in regions:
            result[region] = {}
            for keyword in keywords:
                try:
                    value = region_df.loc[region, keyword]
                    # Include any non-NaN values (even zeros might be meaningful)
                    if not pd.isna(value):
                        result[region][keyword] = float(value) if isinstance(value, (int, float)) else 0
                except Exception as e:
                    logger.warning(f"Error processing region data for {region}, {keyword}: {str(e)}")
        
        # Convert to list format with proper structure for visualization
        formatted_result = []
        for region, values in result.items():
            # Include all regions that have data, even if values are zero
            region_data = {
                "geoName": region,
                "values": values
            }
            formatted_result.append(region_data)
        
        # Sort by the highest value for any keyword
        formatted_result = sorted(
            formatted_result, 
            key=lambda x: max(x["values"].values()) if x["values"] else 0, 
            reverse=True
        )
        
        logger.info(f"Processed {len(formatted_result)} regions with data")
        return formatted_result
    except Exception as e:
        logger.error(f"Error processing region data: {str(e)}")
        return []

# Optimized function to fetch interest by region with rate limiting prevention
def get_interest_by_region(pytrends, keywords, timeframe, geo, resolution='REGION', max_retries=MAX_RETRIES):
    """
    Fetch interest by region data with retry logic and rate limiting prevention
    """
    enforce_rate_limit()
    
    # Add small delay to make the request pattern look more natural
    add_random_delay(0.5, 1.8)
    
    for attempt in range(max_retries):
        try:
            # Build the payload (if not already built)
            try:
                # Add small delay like a user selecting options
                add_random_delay(0.3, 1.2)
                
                pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
            except Exception as build_error:
                logger.warning(f"Error building payload, may be already built: {str(build_error)}")
                
                # If multiple retries, try with fresh session and different proxy
                if attempt > 0:
                    logger.info("Creating fresh session with new proxy for region data")
                    # Create a fresh session
                    session = create_retry_session(use_cache=False)
                    
                    # Try with a different proxy
                    current_proxy = PROXIES[attempt % len(PROXIES)] if PROXIES else None
                    if hasattr(pytrends.requests_session, 'proxies'):
                        current_proxy = pytrends.requests_session.proxies.get('http')
                    
                    # If current proxy failed, mark it as failed
                    if current_proxy:
                        mark_proxy_as_failed(current_proxy)
                    
                    new_proxy = get_random_proxy()
                    if new_proxy:
                        logger.info(f"Switching to different proxy for region data: {new_proxy}")
                        try:
                            # Create a new pytrends instance with our helper function
                            new_pytrends = create_pytrends_instance(
                                hl='en',
                                tz=420,
                                timeout=REQUEST_TIMEOUT,
                                proxy=new_proxy
                            )
                            pytrends = new_pytrends
                            logger.info("Created new pytrends instance for region data")
                        except Exception as proxy_err:
                            logger.warning(f"Failed to create new pytrends: {str(proxy_err)}")
                            mark_proxy_as_failed(new_proxy)
                    
                    pytrends.requests_session = session
                    add_random_delay(1.5, 3.5)
                    
                    # Try again
                    pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
            
            # Add delay like a user clicking on a region analysis tab
            add_random_delay(0.5, 1.5)
            
            # Get interest by region data
            # Use the appropriate resolution parameter based on the requested data type
            # COUNTRY: country level data
            # REGION: region/province level data (first administrative level)
            # DMA: state level data for US (Designated Market Area)
            # CITY: city level data
            logger.info(f"Fetching interest by region data with resolution: {resolution}")
            
            try:
                interest_by_region_df = pytrends.interest_by_region(resolution=resolution, inc_low_vol=True)
                
                # Log the result for debugging
                if interest_by_region_df.empty:
                    logger.warning(f"Empty result for interest_by_region with resolution={resolution}")
                else:
                    logger.info(f"Got interest_by_region data with {len(interest_by_region_df)} regions, columns: {interest_by_region_df.columns.tolist()}")
                
                # If we're looking for state data in the US and resolution is REGION, try DMA as well
                if resolution == 'REGION' and geo == 'US' and (interest_by_region_df.empty or len(interest_by_region_df) < 10):
                    logger.info("Trying DMA resolution for US state-level data")
                    add_random_delay(1.0, 2.0)  # Add delay between requests
                    interest_by_region_df = pytrends.interest_by_region(resolution='DMA', inc_low_vol=True)
                
                # For India, we might need to try different resolutions
                if resolution == 'REGION' and geo == 'IN' and (interest_by_region_df.empty or len(interest_by_region_df) < 10):
                    logger.info("Trying COUNTRY resolution for India data")
                    add_random_delay(1.0, 2.0)  # Add delay between requests
                    interest_by_region_df = pytrends.interest_by_region(resolution='COUNTRY', inc_low_vol=True)
                
                if interest_by_region_df.empty:
                    logger.warning(f"No {resolution.lower()} data available for {keywords} in {geo}")
                    return pd.DataFrame()
                    
                logger.info(f"Successfully fetched {len(interest_by_region_df)} regions for {resolution}")
                
                # Debug: print a few sample rows
                if len(interest_by_region_df) > 0:
                    sample_rows = min(5, len(interest_by_region_df))
                    logger.debug(f"Sample region data (first {sample_rows} rows):\n{interest_by_region_df.head(sample_rows)}")
            except Exception as e:
                logger.error(f"Error fetching interest by region with resolution {resolution}: {str(e)}")
                return pd.DataFrame()
            
            # Simulate a user interacting with results    
            if random.random() > 0.7:  # 30% chance to interact
                add_random_delay(0.8, 2.0)
                logger.debug("Simulating user examining region data")
                
            return interest_by_region_df
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Handle specific errors
            if "429" in error_msg or "too many requests" in error_msg:
                if attempt < max_retries - 1:
                    delay = backoff_with_jitter(attempt, base_delay=10, max_delay=60)  # Increased delays
                    logger.warning(f"Rate limit hit, retrying in {delay:.2f} seconds (attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                    
                    # If we hit a rate limit, refresh the session with new fingerprints and try direct connection
                    try:
                        logger.info("Refreshing session after rate limit")
                        
                        # Get current proxy and mark as failed if it exists
                        current_proxy = None
                        if hasattr(pytrends.requests_session, 'proxies'):
                            current_proxy = pytrends.requests_session.proxies.get('http')
                        
                        if current_proxy:
                            mark_proxy_as_failed(current_proxy)
                        
                        # Try direct connection first after rate limit
                        logger.info("Trying direct connection after rate limit")
                        session = create_retry_session(use_cache=False)
                        pytrends.requests_session = session
                        pytrends.requests_session.proxies = {}
                    except Exception as sess_err:
                        logger.warning(f"Error refreshing session: {str(sess_err)}")
                else:
                    logger.error(f"Rate limit persists after {max_retries} attempts")
                    return pd.DataFrame()
            else:
                logger.error(f"Error fetching interest by {resolution.lower()}: {str(e)}")
                
                # Check for proxy errors
                if "proxy" in error_msg or "connection" in error_msg:
                    # Get current proxy and mark as failed if it exists
                    current_proxy = None
                    if hasattr(pytrends.requests_session, 'proxies'):
                        current_proxy = pytrends.requests_session.proxies.get('http')
                    
                    if current_proxy:
                        mark_proxy_as_failed(current_proxy)
                
                if attempt < max_retries - 1:
                    delay = backoff_with_jitter(attempt, base_delay=5, max_delay=40)  # Increased delays
                    logger.info(f"Retrying after {delay:.2f} seconds (attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                else:
                    return pd.DataFrame()
    
    return pd.DataFrame()  # Return empty DataFrame if all retries fail

# Main function to fetch Google Trends data
def fetch_google_trends(keywords, timeframe='today 5-y', geo='IN', analysis_options=None):
    """
    Main function to fetch Google Trends data with rate limiting avoidance
    
    Parameters:
    - keywords: List of keywords or single keyword string
    - timeframe: Time period for analysis (default: 'today 5-y')
    - geo: Geographic region code (default: 'IN' for India)
    - analysis_options: Dictionary of options for different analysis types
    
    Returns:
    - Dictionary containing the trends data
    """
    # Normalize keywords to a list
    if isinstance(keywords, str):
        keywords = [keywords]
    
    # Limit keywords to 5 as per Google Trends limit
    if len(keywords) > 5:
        logger.warning(f"Too many keywords ({len(keywords)}), limiting to first 5")
        keywords = keywords[:5]
    
    # Set default analysis options if not provided
    if analysis_options is None:
        analysis_options = {
            "include_time_trends": True,
            "include_state_analysis": True,  # Changed from False to True
            "include_city_analysis": False,
            "include_related_queries": False,
            "state_only": False,
            "city_only": False
        }
    
    # Prepare response structure
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    response_data = {
        "status": "success",
        "metadata": {
            "keywords": keywords,
            "timeframe": timeframe,
            "region": geo,
            "timestamp": timestamp
        },
        "data": {}
    }
    
    # Try to get data from cache first
    analysis_type = 'full' if all(analysis_options.values()) else 'partial'
    # Create a more specific analysis_type string to distinguish between different types
    detailed_analysis_type = '_'.join([
        f"time_{int(analysis_options.get('include_time_trends', False))}",
        f"state_{int(analysis_options.get('include_state_analysis', False))}",
        f"city_{int(analysis_options.get('include_city_analysis', False))}",
        f"related_{int(analysis_options.get('include_related_queries', False))}",
        f"stateonly_{int(analysis_options.get('state_only', False))}",
        f"cityonly_{int(analysis_options.get('city_only', False))}"
    ])
    cached_data = get_cached_data(keywords, timeframe, geo, detailed_analysis_type)
    if cached_data:
        return cached_data
        
    # Initialize TrendReq with optimal settings for avoiding rate limits
    try:
        # Add human-like random delay before starting
        add_random_delay(1.5, 4)
        
        # Get pre-warmed cookies from a session that has browsed Google
        cookies = get_google_cookies()
        
        # Create a session with enhanced anti-bot protection
        session = create_retry_session(use_cache=False, use_proxy=True)
        
        # Simulate human browsing behavior with one of the keywords
        sample_keyword = keywords[0] if keywords else "trends"
        simulate_human_browsing(session, keyword=sample_keyword)
        
        # Add a realistic delay as if user is looking at the page
        add_random_delay(2, 6)
        
        # Multiple attempts to initialize pytrends with different proxies
        for attempt in range(3):
            try:
                # Create a custom session that always uses a proxy
                custom_session = create_retry_session(use_cache=False, use_proxy=True)
                
                # Add cookies
                if cookies:
                    for key, value in cookies.items():
                        custom_session.cookies.set(key, value)
                
                # Always use a proxy, just use a different one in each attempt
                if PROXIES and len(PROXIES) > attempt:
                    proxy = PROXIES[attempt % len(PROXIES)]
                else:
                    # Get a random proxy
                    proxy = get_random_proxy()
                
                if not proxy:
                    logger.error(f"Attempt {attempt+1}: No valid proxy available")
                    response_data["status"] = "error"
                    response_data["errors"] = ["No valid proxies available"]
                    return response_data
                    
                logger.info(f"Attempt {attempt+1}: Creating PyTrends with proxy: {proxy}")
                
                # Choose appropriate region-based timezone
                region_code = geo[:2].upper() if len(geo) >= 2 else 'IN'
                tz_options = TIMEZONES_BY_REGION.get(region_code, TIMEZONES_BY_REGION['IN'])
                timezone_offset = random.choice(tz_options)
                
                # Create PyTrends instance using our helper function - always with proxy
                pytrends = create_pytrends_instance(
                    hl='en',
                    tz=timezone_offset,
                    timeout=REQUEST_TIMEOUT,
                    proxy=proxy,
                    use_proxy=True
                )
                
                # Replace the default session with our custom one
                pytrends.requests_session = custom_session
                
                # Set proxy in the session as well
                pytrends.requests_session.proxies = {
                    'http': proxy,
                    'https': proxy
                }
                
                # Test if it works with a simple request
                logger.info("Testing PyTrends connection...")
                test_result = True
                
                # If a test request succeeds, we've found a working configuration
                if test_result:
                    logger.info(f"Found working PyTrends configuration on attempt {attempt+1}")
                    break
                    
            except Exception as init_err:
                logger.warning(f"PyTrends initialization attempt {attempt+1} failed: {str(init_err)}")
                
                # If proxy failed, mark it as bad
                if proxy:
                    mark_proxy_as_failed(proxy)
                
                if attempt == 2:
                    # Final fallback with a fresh proxy
                    logger.info("Using final fallback PyTrends configuration")
                    try:
                        new_proxy = get_random_proxy()
                        if not new_proxy:
                            logger.error("No valid proxies left for final fallback")
                            response_data["status"] = "error"
                            response_data["errors"] = ["No valid proxies available for fallback"]
                            return response_data
                            
                        logger.info(f"Final attempt with proxy: {new_proxy}")
                        
                        pytrends = create_pytrends_instance(
                            hl='en',
                            tz=420,
                            timeout=REQUEST_TIMEOUT,
                            proxy=new_proxy,
                            use_proxy=True
                        )
                        
                        # Always use proxy for the session
                        session = create_retry_session(use_cache=False, use_proxy=True)
                        session.proxies = {
                            'http': new_proxy,
                            'https': new_proxy
                        }
                        pytrends.requests_session = session
                    except Exception as final_err:
                        logger.error(f"Failed to create even the most basic PyTrends: {str(final_err)}")
                        response_data["status"] = "error"
                        response_data["errors"] = [f"Failed to initialize Google Trends API: {str(final_err)}"]
                        return response_data
        
        # Add a small delay before first request to appear more human-like
        add_random_delay(1, 3)
        
        # Use ThreadPoolExecutor for parallel fetching where possible
        with ThreadPoolExecutor(max_workers=2) as executor:  # Reduced from 3 to 2 for less aggressive fetching
            futures = {}
            
            # Time trends data
            if analysis_options.get("include_time_trends", True) and not analysis_options.get("state_only", False) and not analysis_options.get("city_only", False):
                # Add human-like delay between requests
                add_random_delay(1.5, 3.5)
                futures['time_trends'] = executor.submit(get_trends_data, pytrends, keywords, timeframe, geo)
            
            # Region and city data can be fetched in parallel
            if analysis_options.get("include_state_analysis", False) or analysis_options.get("state_only", False):
                # Add human-like delay between requests
                add_random_delay(2, 4)
                
                # For US, use DMA resolution to get state-level data
                if geo == 'US':
                    logger.info("Using DMA resolution for US state-level data")
                    futures['region_data'] = executor.submit(get_interest_by_region, pytrends, keywords, timeframe, geo, 'DMA')
                else:
                    # For other countries, use REGION resolution
                    futures['region_data'] = executor.submit(get_interest_by_region, pytrends, keywords, timeframe, geo, 'REGION')
            
            if analysis_options.get("include_city_analysis", False) or analysis_options.get("city_only", False):
                # Add human-like delay between requests
                add_random_delay(2.5, 5)
                futures['city_data'] = executor.submit(get_interest_by_region, pytrends, keywords, timeframe, geo, 'CITY')
            
            # Related queries must be fetched after payload is built
            if analysis_options.get("include_related_queries", False):
                # Add human-like delay between requests
                add_random_delay(1.8, 4.2)
                futures['related_queries'] = executor.submit(get_related_queries, pytrends, keywords, timeframe, geo)
            
            # Process results as they complete
            for name, future in futures.items():
                try:
                    # Add random delay between processing results to appear more human-like
                    add_random_delay(0.5, 1.5)
                    result = future.result()
                    
                    if name == 'time_trends':
                        if result is not None:
                            # Check if this is fallback data
                            if hasattr(result, 'is_fallback') and result.is_fallback is True:
                                logger.warning("Using fallback time trends data")
                                response_data['warning'] = "Using fallback data - Google Trends API may be blocked"
                            
                            # Convert to JSON if needed
                            if hasattr(result, 'empty'):
                                if not result.empty:
                                    logger.info(f"Converting DataFrame to JSON with {len(result)} rows")
                                    response_data['data']['time_trends'] = dataframe_to_json(result)
                                else:
                                    logger.warning("Time trends DataFrame is empty")
                                    response_data['data']['time_trends'] = []
                            elif isinstance(result, list):
                                logger.info(f"Using preformatted list result with {len(result)} items")
                                response_data['data']['time_trends'] = result
                            else:
                                logger.warning(f"Unexpected time_trends result type: {type(result)}")
                                try:
                                    # Try to convert using dataframe_to_json which has fallbacks
                                    response_data['data']['time_trends'] = dataframe_to_json(result)
                                except Exception as convert_err:
                                    logger.error(f"Failed to convert time_trends result: {str(convert_err)}")
                                    response_data['data']['time_trends'] = []
                        else:
                            logger.warning("Time trends result is None")
                            response_data['data']['time_trends'] = []
                            
                    elif name == 'region_data':
                        if result is not None:
                            # Handle DataFrame vs list
                            if hasattr(result, 'empty'):
                                if not result.empty:
                                    logger.info(f"Processing region DataFrame with {len(result)} rows")
                                    regions = process_region_data(result)
                                    response_data['data']['region_data'] = regions
                                else:
                                    logger.warning("Region DataFrame is empty")
                                    response_data['data']['region_data'] = []
                            elif isinstance(result, list):
                                logger.info(f"Using preformatted region list with {len(result)} items")
                                response_data['data']['region_data'] = result
                            else:
                                logger.warning(f"Unexpected region_data result type: {type(result)}")
                                response_data['data']['region_data'] = []
                        else:
                            logger.warning("Region data result is None")
                            response_data['data']['region_data'] = []
                            
                    elif name == 'city_data':
                        if result is not None:
                            # Handle DataFrame vs list
                            if hasattr(result, 'empty'):
                                if not result.empty:
                                    logger.info(f"Processing city DataFrame with {len(result)} rows")
                                    cities = process_region_data(result)
                                    response_data['data']['city_data'] = cities
                                else:
                                    logger.warning("City DataFrame is empty")
                                    response_data['data']['city_data'] = []
                            elif isinstance(result, list):
                                logger.info(f"Using preformatted city list with {len(result)} items")
                                response_data['data']['city_data'] = result
                            else:
                                logger.warning(f"Unexpected city_data result type: {type(result)}")
                                response_data['data']['city_data'] = []
                        else:
                            logger.warning("City data result is None")
                            response_data['data']['city_data'] = []
                            
                    elif name == 'related_queries':
                        if result and isinstance(result, dict) and any(result.get(kw) is not None for kw in result):
                            processed_queries = {}
                            
                            for kw in result:
                                if result[kw] is not None:
                                    processed_queries[kw] = {
                                        'top': result[kw]['top'].to_dict('records') if result[kw]['top'] is not None else [],
                                        'rising': result[kw]['rising'].to_dict('records') if result[kw]['rising'] is not None else []
                                    }
                            
                            response_data['data']['related_queries'] = processed_queries
                        else:
                            logger.warning("Related queries result is invalid or empty")
                            response_data['data']['related_queries'] = {}
                
                except Exception as e:
                    logger.error(f"Error processing {name} data: {str(e)}")
                    
                    # Set default empty values for failed fetches
                    if name == 'time_trends':
                        response_data['data']['time_trends'] = []
                    elif name == 'region_data':
                        response_data['data']['region_data'] = []
                    elif name == 'city_data':
                        response_data['data']['city_data'] = []
                    elif name == 'related_queries':
                        response_data['data']['related_queries'] = {}
        
        # If time_trends failed but we didn't try separate approach, do it now
        if not response_data['data'].get('time_trends') and 'time_trends' in futures:
            logger.info("Attempting direct fetch for time series data as fallback")
            try:
                # Get a fresh proxy for this attempt
                fallback_proxy = get_random_proxy()
                if not fallback_proxy:
                    logger.error("No valid proxies available for time trends fallback")
                    response_data["warning"] = "Could not fetch time trends data - no valid proxies available"
                    response_data['data']['time_trends'] = []
                else:
                    # Create a new pytrends instance with the proxy
                    direct_pytrends = create_pytrends_instance(
                        hl='en',
                        tz=420,
                        timeout=REQUEST_TIMEOUT * 2,  # Double timeout
                        proxy=fallback_proxy,
                        use_proxy=True
                    )
                    
                    # Use a shorter timeframe for better chance of success
                    short_tf = 'today 3-m'
                    logger.info(f"Trying with shorter timeframe: {short_tf} and proxy: {fallback_proxy}")
                    
                    # Add delay to avoid rate limit
                    add_random_delay(3, 6)
                    
                    # Try direct fetch with proxy
                    direct_pytrends.build_payload(keywords, timeframe=short_tf, geo=geo)
                    direct_result = direct_pytrends.interest_over_time()
                    
                    if not direct_result.empty:
                        logger.info("Successfully retrieved time series data with direct approach")
                        response_data['data']['time_trends'] = dataframe_to_json(direct_result)
                        response_data['metadata']['timeframe'] = short_tf
                    else:
                        logger.warning("Direct approach also failed to get time series data")
                        response_data["errors"] = ["Could not fetch time trends data - Google Trends returned empty data"]
                        response_data['data']['time_trends'] = []
            except Exception as direct_err:
                logger.error(f"Error with direct fetch approach: {str(direct_err)}")
                response_data["errors"] = [f"Could not fetch time trends data: {str(direct_err)}"]
                response_data['data']['time_trends'] = []

        # If region_data failed or is empty, try fallback approach
        if (analysis_options.get("include_state_analysis", False) or analysis_options.get("state_only", False)) and \
           (not response_data['data'].get('region_data') or len(response_data['data']['region_data']) == 0):
            logger.info("Attempting direct fetch for region data as fallback")
            try:
                # Get a fresh proxy for this attempt
                region_fallback_proxy = get_random_proxy()
                if not region_fallback_proxy:
                    logger.error("No valid proxies available for region data fallback")
                    response_data["warning"] = "Could not fetch region data - no valid proxies available"
                    response_data['data']['region_data'] = []
                else:
                    # Create a new pytrends instance with the proxy
                    direct_pytrends = create_pytrends_instance(
                        hl='en',
                        tz=420,
                        timeout=REQUEST_TIMEOUT * 2,  # Double timeout
                        proxy=region_fallback_proxy,
                        use_proxy=True
                    )
                    
                    # Use a shorter timeframe for better chance of success
                    short_tf = 'today 3-m'
                    logger.info(f"Trying region data with shorter timeframe: {short_tf} and proxy: {region_fallback_proxy}")
                    
                    # Add delay to avoid rate limit
                    add_random_delay(3, 6)
                    
                    # Try direct fetch with proxy
                    direct_pytrends.build_payload(keywords, timeframe=short_tf, geo=geo)
                    
                    # Try with different resolution
                    resolution = 'COUNTRY' if geo == '' else 'REGION'
                    direct_result = direct_pytrends.interest_by_region(resolution=resolution, inc_low_vol=True)
                    
                    if not direct_result.empty:
                        logger.info(f"Successfully retrieved region data with direct approach: {len(direct_result)} regions")
                        regions = process_region_data(direct_result)
                        response_data['data']['region_data'] = regions
                        logger.info(f"Processed {len(regions)} regions with direct approach")
                    else:
                        logger.warning("Direct approach failed to get region data, cannot proceed")
                        response_data["errors"] = ["Could not fetch region data - Google Trends returned empty data"]
                        response_data['data']['region_data'] = []
            except Exception as region_err:
                logger.error(f"Error with direct region fetch: {str(region_err)}")
                response_data["errors"] = [f"Could not fetch region data: {str(region_err)}"]
                response_data['data']['region_data'] = []
    
    except Exception as e:
        logger.error(f"Error in fetch_google_trends: {str(e)}")
        response_data["status"] = "error"
        response_data["errors"] = [str(e)]
    
    # Ensure all data sections exist even if not requested
    if "time_trends" not in response_data["data"]:
        response_data["data"]["time_trends"] = []
    if "region_data" not in response_data["data"]:
        response_data["data"]["region_data"] = []
    if "city_data" not in response_data["data"]:
        response_data["data"]["city_data"] = []
    if "related_queries" not in response_data["data"]:
        response_data["data"]["related_queries"] = {}
    
    # Check if we have any valid data
    has_valid_data = (
        response_data["data"]["time_trends"] or
        response_data["data"]["region_data"] or
        response_data["data"]["city_data"] or
        response_data["data"]["related_queries"]
    )
    
    if not has_valid_data:
        logger.warning("No valid data was retrieved from Google Trends")
        response_data["status"] = "error"
        if "errors" not in response_data:
            response_data["errors"] = ["No data retrieved from Google Trends"]
    
    # Cache successful responses
    if response_data["status"] == "success":
        save_to_cache(response_data, keywords, timeframe, geo, detailed_analysis_type)
    
    return response_data

# Main function to get trends JSON (primary function used by the application)
def get_trends_json(keywords, timeframe='today 5-y', geo='IN', analysis_options=None):
    """
    Fetch Google Trends data and return as JSON
    
    This is the main function used by the application to get trends data.
    Uses optimized fetching and caching to improve performance and avoid rate limiting.
    
    Parameters:
    - keywords: List of keywords or single keyword string
    - timeframe: Time period for analysis (default: 'today 5-y')
    - geo: Geographic region code (default: 'IN' for India)
    - analysis_options: Dictionary of options for different analysis types
    
    Returns:
    - Dictionary containing the trends data
    """
    # Store original timeframe for returning in response
    original_timeframe = timeframe
    
    try:
        logger.info(f"Fetching trends for keywords={keywords}, timeframe={timeframe}, geo={geo}")
        start_time = time.time()
        
        # Set default analysis options if not provided
        if analysis_options is None:
            analysis_options = {
                "include_time_trends": True,
                "include_state_analysis": True,  # Enable regional data by default
                "include_city_analysis": False,
                "include_related_queries": False,
                "state_only": False,
                "city_only": False
            }
        
        # Try first with proxy using the requested timeframe
        logger.info(f"Attempting to fetch trends with proxy using timeframe: {timeframe}")
        result = fetch_google_trends(keywords, timeframe, geo, analysis_options)
        
        
        # Check if we got valid data
        if result.get('status') == 'success' and result.get('data', {}).get('time_trends'):
            logger.info(f"Successfully fetched trends data with timeframe: {timeframe}")
            # Ensure the original timeframe is preserved
            result['metadata']['timeframe'] = original_timeframe
            
            # Log execution time
            execution_time = time.time() - start_time
            logger.info(f"Trends data fetched in {execution_time:.2f} seconds")
            
            # Log warning if it took too long
            if execution_time > 30:
                logger.warning(f"Trends fetch took {execution_time:.2f} seconds, which exceeds target of 30 seconds")
                
            return result
        
        logger.warning(f"Failed to get data with original timeframe: {timeframe}")
        
        # If original attempt failed, try direct connection without proxy but same timeframe
        logger.info(f"Trying direct connection with original timeframe: {timeframe}")
        
        # Try with the same timeframe but direct connection
        direct_result = None
        try:
            # Create a direct connection request with the original timeframe
            direct_result = fetch_google_trends_direct(keywords, timeframe, geo, analysis_options)
            
            # Check if we got valid data
            if direct_result.get('status') == 'success' and direct_result.get('data', {}).get('time_trends'):
                logger.info(f"Successfully fetched trends data with direct connection using timeframe: {timeframe}")
                
                # Ensure the original timeframe is preserved
                direct_result['metadata']['timeframe'] = original_timeframe
                direct_result['metadata']['connection'] = 'direct'
                
                # Log execution time
                execution_time = time.time() - start_time
                logger.info(f"Trends data fetched in {execution_time:.2f} seconds")
                
                # Log warning if it took too long
                if execution_time > 30:
                    logger.warning(f"Trends fetch took {execution_time:.2f} seconds, which exceeds target of 30 seconds")
                    
                return direct_result
        except Exception as direct_err:
            logger.error(f"Error with direct connection: {str(direct_err)}")
            # Continue to fallback approach
        
        # If all attempts failed, return error response
        logger.error("Failed to fetch trends data with both proxy and direct connection")
        
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        error_response = {
            "status": "error",
            "metadata": {
                "keywords": keywords if isinstance(keywords, list) else [keywords],
                "timeframe": original_timeframe,
                "region": geo,
                "timestamp": timestamp
            },
            "errors": ["Failed to fetch Google Trends data. All attempts were unsuccessful."],
            "data": {
                "time_trends": [],
                "region_data": [],
                "city_data": [],
                "related_queries": {}
            }
        }
        
        # Log execution time
        execution_time = time.time() - start_time
        logger.info(f"Trends data fetch attempt failed in {execution_time:.2f} seconds")
        
        # Log warning if it took too long
        if execution_time > 30:
            logger.warning(f"Trends fetch attempt took {execution_time:.2f} seconds, which exceeds target of 30 seconds")
        
        return error_response
    
    except Exception as e:
        logger.error(f"Error in get_trends_json: {str(e)}", exc_info=True)
        
        # Create an error response
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Return error response instead of generating fake data
        error_response = {
            "status": "error",
            "metadata": {
                "keywords": keywords if isinstance(keywords, list) else [keywords],
                "timeframe": original_timeframe,
                "region": geo,
                "timestamp": timestamp
            },
            "errors": [f"Failed to fetch Google Trends data: {str(e)}"],
            "data": {
                "time_trends": [],
                "region_data": [],
                "city_data": [],
                "related_queries": {}
            }
        }
        
        return error_response

# Direct connection version of fetch_google_trends
def fetch_google_trends_direct(keywords, timeframe='today 5-y', geo='IN', analysis_options=None):
    """
    A simplified version of fetch_google_trends that uses direct connection (no proxy)
    with more conservative parameters to avoid rate limiting
    """
    # Normalize keywords to a list
    if isinstance(keywords, str):
        keywords = [keywords]
    
    # Limit keywords to 5 as per Google Trends limit
    if len(keywords) > 5:
        logger.warning(f"Too many keywords ({len(keywords)}), limiting to first 5")
        keywords = keywords[:5]
    
    # Set default analysis options if not provided
    if analysis_options is None:
        analysis_options = {
            "include_time_trends": True,
            "include_state_analysis": False,  # Simplify request
            "include_city_analysis": False,
            "include_related_queries": False,
            "state_only": False,
            "city_only": False
        }
    
    # Prepare response structure
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    response_data = {
        "status": "success",
        "metadata": {
            "keywords": keywords,
            "timeframe": timeframe,
            "region": geo,
            "timestamp": timestamp,
            "connection": "direct"  # Flag that this was a direct connection
        },
        "data": {}
    }
    
    try:
        # Create a simple session without proxy
        session = requests.Session()
        
        # Apply some basic headers to look like a browser
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://trends.google.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
        
        # Create a pytrends instance without proxy - use explicit requests_args to avoid timeout conflicts
        try:
            pytrends = TrendReq(
                hl='en',
                tz=420,
                retries=3,
                backoff_factor=2.0,
                requests_args={
                    'verify': True,
                    'timeout': (30, 60)  # Longer timeout for direct connection
                }
            )
            logger.info("Successfully created TrendReq instance")
        except Exception as init_err:
            logger.error(f"Error initializing TrendReq: {str(init_err)}")
            # Try with a more basic construction
            pytrends = TrendReq(
                hl='en',
                tz=420
            )
            logger.info("Created TrendReq with minimal parameters")
        
        # Replace the default session
        pytrends.requests_session = session
        
        # Add a delay before starting
        time.sleep(3)
        
        # Build payload 
        logger.info(f"Building payload for direct connection: {keywords}, {timeframe}, {geo}")
        try:
            pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
            logger.info("Successfully built payload")
        except Exception as payload_err:
            logger.error(f"Error building payload: {str(payload_err)}")
            response_data["status"] = "error"
            response_data["errors"] = [f"Failed to build request payload: {str(payload_err)}"]
            return response_data
        
        # Get time trends data
        if analysis_options.get("include_time_trends", True):
            time.sleep(2)  # Add delay between requests
            logger.info("Fetching time trends data with direct connection")
            try:
                time_trends_df = pytrends.interest_over_time()
                
                if time_trends_df is not None and not time_trends_df.empty:
                    json_data = dataframe_to_json(time_trends_df)
                    response_data['data']['time_trends'] = json_data
                    logger.info(f"Successfully retrieved time trends data: {len(time_trends_df)} points")
                else:
                    logger.warning("Time trends result was empty or None")
                    response_data['data']['time_trends'] = []
            except Exception as time_err:
                logger.error(f"Error retrieving time trends data: {str(time_err)}")
                response_data['data']['time_trends'] = []
                response_data["errors"] = [f"Failed to retrieve time trends data: {str(time_err)}"]
        
        # Get region data if requested
        if analysis_options.get("include_state_analysis", False):
            time.sleep(3)  # Add longer delay for region data
            logger.info("Fetching region data with direct connection")
            try:
                region_df = pytrends.interest_by_region(resolution='REGION', inc_low_vol=True)
                
                if region_df is not None and not region_df.empty:
                    regions = process_region_data(region_df)
                    response_data['data']['region_data'] = regions
                    logger.info(f"Successfully retrieved region data: {len(regions)} regions")
                else:
                    logger.warning("Region data result was empty or None")
                    response_data['data']['region_data'] = []
            except Exception as region_err:
                logger.error(f"Error retrieving region data: {str(region_err)}")
                response_data['data']['region_data'] = []
        else:
            response_data['data']['region_data'] = []
        
        # Set other data fields to empty values
        response_data['data']['city_data'] = []
        response_data['data']['related_queries'] = {}
        
        # Check if we got any valid data
        if not response_data['data'].get('time_trends'):
            logger.warning("No time trends data retrieved with direct connection")
            # Only mark as error if we were supposed to get time trends data
            if analysis_options.get("include_time_trends", True):
                response_data["status"] = "error"
                if "errors" not in response_data:
                    response_data["errors"] = ["No time trends data retrieved from Google Trends with direct connection"]
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error in fetch_google_trends_direct: {str(e)}")
        response_data["status"] = "error"
        response_data["errors"] = [str(e)]
        
        # Set default empty values
        response_data["data"]["time_trends"] = []
        response_data["data"]["region_data"] = []
        response_data["data"]["city_data"] = []
        response_data["data"]["related_queries"] = {}
        
        return response_data

# Simple file-based caching implementation
class SimpleFileCache:
    def __init__(self, cache_dir):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def get(self, key):
        file_path = os.path.join(self.cache_dir, f"{key}.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading from cache: {str(e)}")
                return None
        return None
    
    def set(self, key, value, timeout=None):
        file_path = os.path.join(self.cache_dir, f"{key}.json")
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(value, f, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"Error writing to cache: {str(e)}")
            return False

# Create cache instance
cache = SimpleFileCache(CACHE_DIR)

# Fix the session's retry configuration
def fix_session_retry(session):
    """Fix a session's retry configuration based on urllib3 version and add robust error handling"""
    try:
        # Import urllib3 to check version
        import urllib3
        import importlib.metadata
        
        # Try to get version info
        try:
            urllib3_version = importlib.metadata.version('urllib3')
        except (ImportError, AttributeError):
            urllib3_version = getattr(urllib3, '__version__', '1.0.0')
        
        logger.debug(f"Fixing session retry with urllib3 version: {urllib3_version}")
        
        # Create appropriate retry strategy based on version
        if urllib3_version.startswith(('2.', '3.')):
            # For urllib3 >= 2.0, use allowed_methods
            retry_strategy = Retry(
                total=MAX_RETRIES,
                backoff_factor=BACKOFF_FACTOR,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["HEAD", "GET", "OPTIONS"]
                # Removed other_errors parameter that was causing issues
            )
            logger.debug("Using 'allowed_methods' parameter for Retry with urllib3 >= 2.0")
        else:
            # For urllib3 < 2.0, use method_whitelist
            retry_strategy = Retry(
                total=MAX_RETRIES,
                backoff_factor=BACKOFF_FACTOR,
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=["HEAD", "GET", "OPTIONS"],
                raise_on_status=False,
                raise_on_redirect=False
            )
            logger.debug("Using 'method_whitelist' parameter for Retry with urllib3 < 2.0")
        
        # Create adapter with retry strategy and improved connection pooling
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            # Increase connection pooling for better stability
            pool_connections=10,
            pool_maxsize=10, 
            pool_block=False
        )
        
        # Mount the adapter to both http and https
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        # Set a more robust default timeout for all requests (connect timeout, read timeout)
        # Store as attribute but don't set as default to avoid conflicts with other code
        session.request_timeout = (10, 30)  # 10 seconds for connect, 30 seconds for read
        
        # Configure keep-alive for better connection stability
        session.headers.update({'Connection': 'keep-alive'})
        
        return True
        
    except Exception as retry_error:
        # Fallback to basic adapter without custom retry strategy
        logger.warning(f"Error setting up retry strategy: {str(retry_error)}")
        logger.warning("Using basic adapter without custom retry strategy")
        adapter = HTTPAdapter(
            max_retries=3,  # Simpler retry mechanism
            pool_connections=5,
            pool_maxsize=5
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return False

# Direct function to get region data for testing
def get_region_interest(keywords, timeframe='today 5-y', geo='IN'):
    """
    Direct function to get region interest data for testing
    
    Parameters:
    - keywords: List of keywords or single keyword string
    - timeframe: Time period for analysis (default: 'today 5-y')
    - geo: Geographic region code (default: 'IN' for India)
    
    Returns:
    - List of regions with their interest values
    """
    try:
        logger.info(f"Directly fetching region interest for keywords={keywords}, timeframe={timeframe}, geo={geo}")
        
        # Normalize keywords to a list
        if isinstance(keywords, str):
            keywords = [keywords]
        
        # Limit keywords to 5 as per Google Trends limit
        if len(keywords) > 5:
            logger.warning(f"Too many keywords ({len(keywords)}), limiting to first 5")
            keywords = keywords[:5]
        
        # Create a PyTrends instance
        pytrends = create_pytrends_instance(hl='en', tz=420, timeout=REQUEST_TIMEOUT)
        
        # Build payload
        pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
        
        # Try different resolutions
        resolutions = ['REGION', 'COUNTRY', 'DMA']
        
        for resolution in resolutions:
            logger.info(f"Trying resolution: {resolution}")
            
            try:
                region_df = pytrends.interest_by_region(resolution=resolution, inc_low_vol=True)
                
                if not region_df.empty:
                    logger.info(f"Got data with resolution {resolution}: {len(region_df)} regions")
                    regions = process_region_data(region_df)
                    return {
                        "status": "success",
                        "data": regions,
                        "resolution": resolution,
                        "count": len(regions)
                    }
                else:
                    logger.warning(f"No data for resolution {resolution}")
            except Exception as e:
                logger.error(f"Error with resolution {resolution}: {str(e)}")
        
        # If we get here, all resolutions failed, use fallback
        logger.warning("All resolutions failed, using fallback data")
        fallback_df = generate_fallback_region_data(keywords, geo)
        regions = process_region_data(fallback_df)
        
        return {
            "status": "warning",
            "data": regions,
            "resolution": "fallback",
            "count": len(regions),
            "warning": "Using fallback data - all API requests failed"
        }
        
    except Exception as e:
        logger.error(f"Error in get_region_interest: {str(e)}")
        
        # Generate fallback data
        fallback_df = generate_fallback_region_data(keywords, geo)
        regions = process_region_data(fallback_df)
        
        return {
            "status": "error",
            "data": regions,
            "resolution": "fallback",
            "count": len(regions),
            "error": str(e)
        }

# Direct connection version of fetch_google_trends that doesn't require modifying the global PROXIES
def fetch_google_trends_no_proxy(keywords, timeframe='today 5-y', geo='IN', analysis_options=None):
    """
    A version of fetch_google_trends that uses direct connection (no proxy)
    """
    # Normalize keywords to a list
    if isinstance(keywords, str):
        keywords = [keywords]
    
    # Limit keywords to 5 as per Google Trends limit
    if len(keywords) > 5:
        logger.warning(f"Too many keywords ({len(keywords)}), limiting to first 5")
        keywords = keywords[:5]
    
    # Set default analysis options if not provided
    if analysis_options is None:
        analysis_options = {
            "include_time_trends": True,
            "include_state_analysis": False,  # Simplify request
            "include_city_analysis": False,
            "include_related_queries": False,
            "state_only": False,
            "city_only": False
        }
    
    # Prepare response structure
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    response_data = {
        "status": "success",
        "metadata": {
            "keywords": keywords,
            "timeframe": timeframe,
            "region": geo,
            "timestamp": timestamp,
            "connection": "direct"  # Flag that this was a direct connection
        },
        "data": {}
    }
    
    try:
        # Create a simple session without proxy
        session = requests.Session()
        
        # Apply some basic headers to look like a browser
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Referer": "https://trends.google.com/",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })
        
        # Create a pytrends instance without proxy - use minimally required parameters
        try:
            # Create with only the essential parameters to avoid conflicts
            pytrends = TrendReq(
                hl='en',
                tz=420,
                retries=3,
                backoff_factor=2.0
            )
            logger.info("Successfully created TrendReq instance with minimal parameters")
            
            # Configure the session with proper keep-alive settings
            session.headers.update({
                'Connection': 'keep-alive',
                'Keep-Alive': '300'  # Keep connection alive for 300 seconds
            })
            
            # Then manually set the timeout in the session
            session.request_timeout = (30, 60)  # (connect, read) timeout
            
            # Replace the requests_session with our custom session
            pytrends.requests_session = session
            
        except Exception as init_err:
            logger.error(f"Error initializing TrendReq: {str(init_err)}")
            # Try with absolute minimal parameters
            pytrends = TrendReq(
                hl='en',
                tz=420
            )
            logger.info("Created TrendReq with absolute minimal parameters")
            
            # Replace the requests_session with our custom session
            pytrends.requests_session = session
        
        # Add a delay before starting
        time.sleep(3)
        
        # Build payload 
        logger.info(f"Building payload for direct connection: {keywords}, {timeframe}, {geo}")
        try:
            pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
            logger.info("Successfully built payload")
        except Exception as payload_err:
            logger.error(f"Error building payload: {str(payload_err)}")
            response_data["status"] = "error"
            response_data["errors"] = [f"Failed to build request payload: {str(payload_err)}"]
            return response_data
        
        # Get time trends data
        if analysis_options.get("include_time_trends", True):
            time.sleep(2)  # Add delay between requests
            logger.info("Fetching time trends data with direct connection")
            try:
                time_trends_df = pytrends.interest_over_time()
                
                if time_trends_df is not None and not time_trends_df.empty:
                    json_data = dataframe_to_json(time_trends_df)
                    response_data['data']['time_trends'] = json_data
                    logger.info(f"Successfully retrieved time trends data: {len(time_trends_df)} points")
                else:
                    logger.warning("Time trends result was empty or None")
                    response_data['data']['time_trends'] = []
            except Exception as time_err:
                logger.error(f"Error retrieving time trends data: {str(time_err)}")
                response_data['data']['time_trends'] = []
                response_data["errors"] = [f"Failed to retrieve time trends data: {str(time_err)}"]
        
        # Get region data if requested
        if analysis_options.get("include_state_analysis", False):
            time.sleep(3)  # Add longer delay for region data
            logger.info("Fetching region data with direct connection")
            try:
                region_df = pytrends.interest_by_region(resolution='REGION', inc_low_vol=True)
                
                if region_df is not None and not region_df.empty:
                    regions = process_region_data(region_df)
                    response_data['data']['region_data'] = regions
                    logger.info(f"Successfully retrieved region data: {len(regions)} regions")
                else:
                    logger.warning("Region data result was empty or None")
                    response_data['data']['region_data'] = []
            except Exception as region_err:
                logger.error(f"Error retrieving region data: {str(region_err)}")
                response_data['data']['region_data'] = []
        else:
            response_data['data']['region_data'] = []
        
        # Set other data fields to empty values
        response_data['data']['city_data'] = []
        response_data['data']['related_queries'] = {}
        
        # Check if we got any valid data
        if not response_data['data'].get('time_trends'):
            logger.warning("No time trends data was retrieved")
            # Only mark as error if we were supposed to get time trends data
            if analysis_options.get("include_time_trends", True):
                response_data["status"] = "error"
                if "errors" not in response_data:
                    response_data["errors"] = ["No time trends data could be retrieved with direct connection"]
        
        return response_data
        
    except Exception as e:
        logger.error(f"Error in fetch_google_trends_no_proxy: {str(e)}")
        response_data["status"] = "error"
        response_data["errors"] = [str(e)]
        
        # Set default empty values
        response_data["data"]["time_trends"] = []
        response_data["data"]["region_data"] = []
        response_data["data"]["city_data"] = []
        response_data["data"]["related_queries"] = {}
        
        return response_data

# Constants
REQUEST_TIMEOUT = 30
SERP_API_KEY = "64e3a48333bbb33f4ce8ded91e5268cd453a80fb244104de63b7ad9af9cc2a58"

def fetch_serp_trends(keyword, timeframe='today 5-y', geo='IN', analysis_options=None):
    """
    Fetch trends data from SERP API as a fallback using serpapi package
    """
    if not SERP_API_KEY:
        logger.error("SERP API key not configured")
        return None

    if analysis_options is None:
        analysis_options = {
            "include_time_trends": True,
            "include_state_analysis": False,
            "include_city_analysis": False,
            "include_related_queries": False,
            "state_only": False,
            "city_only": False
        }

    serp_results = {}
    try:
        # Map analysis options to SERP API data_type
        serp_data_types = []
        if analysis_options.get("include_time_trends", False) and not analysis_options.get("state_only", False) and not analysis_options.get("city_only", False):
            serp_data_types.append("TIMESERIES")
        if analysis_options.get("include_state_analysis", False) or analysis_options.get("state_only", False):
            serp_data_types.append("GEO_MAP_0")
        if analysis_options.get("include_city_analysis", False) or analysis_options.get("city_only", False):
            serp_data_types.append("GEO_MAP_1")
        if analysis_options.get("include_related_queries", False):
            serp_data_types.append("RELATED_QUERIES")

        # If no data type is set, default to TIMESERIES
        if not serp_data_types:
            serp_data_types = ["TIMESERIES"]

        for data_type in serp_data_types:
            params = {
                "engine": "google_trends",
                "q": keyword,
                "geo": geo,
                "api_key": SERP_API_KEY,
                "data_type": data_type
            }
            # Always use 5 years data for TIMESERIES
            if data_type == "TIMESERIES":
                params["date"] = timeframe
            search = GoogleSearch(params)
            results = search.get_dict()
            serp_results[data_type] = results

        # Parse results into your app's format
        data = {}
        # Time trends
        if (
            "TIMESERIES" in serp_results and
            isinstance(serp_results["TIMESERIES"], dict) and
            "interest_over_time" in serp_results["TIMESERIES"] and
            "timeline_data" in serp_results["TIMESERIES"]["interest_over_time"] and
            isinstance(serp_results["TIMESERIES"]["interest_over_time"]["timeline_data"], list)
        ):
            # Format with timeline_data array
            data["time_trends"] = []
            for point in serp_results["TIMESERIES"]["interest_over_time"]["timeline_data"]:
                if not isinstance(point, dict):
                    continue
                
                if "values" not in point or not isinstance(point["values"], list) or not point["values"]:
                    continue
                    
                # Extract value from the values array
                value_obj = point["values"][0]  # Use the first value object
                extracted_value = value_obj.get("extracted_value", value_obj.get("value", 0))
                
                # Create a data point
                data_point = {
                    "date": point.get("date", ""),
                    "value": extracted_value
                }
                
                # Add timestamp if available
                if "timestamp" in point:
                    data_point["timestamp"] = point["timestamp"]
                    
                data["time_trends"].append(data_point)
                
        elif (
            "TIMESERIES" in serp_results and
            isinstance(serp_results["TIMESERIES"], dict) and
            "interest_over_time" in serp_results["TIMESERIES"] and
            isinstance(serp_results["TIMESERIES"]["interest_over_time"], list)
        ):
            # Format without timeline_data array
            data["time_trends"] = [
                {"date": point["date"], "value": point["value"]}
                for point in serp_results["TIMESERIES"]["interest_over_time"]
                if isinstance(point, dict) and "date" in point and "value" in point
            ]
        else:
            # If we can't parse the data, pass through the raw response
            logger.warning(f"SERP API data format not recognized, passing through raw data")
            # Just pass the raw data through to the frontend for client-side processing
            return {
                'status': 'success',
                'metadata': {
                    'keywords': [keyword],
                    'timeframe': 'today 5-y',
                    'region': geo,
                    'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'source': 'serp_api',
                    'raw_data': True
                },
                # Pass the TIMESERIES response as-is for client-side processing
                **serp_results.get("TIMESERIES", {})
            }
        # Region
        if (
            "GEO_MAP_0" in serp_results and
            isinstance(serp_results["GEO_MAP_0"], dict) and
            "interest_by_region" in serp_results["GEO_MAP_0"] and
            isinstance(serp_results["GEO_MAP_0"]["interest_by_region"], list)
        ):
            data["region_data"] = [
                {"geoName": region["name"], "values": {keyword: region["value"]}}
                for region in serp_results["GEO_MAP_0"]["interest_by_region"]
                if isinstance(region, dict) and "name" in region and "value" in region
            ]
        else:
            logger.error(f"SERP API GEO_MAP_0 response: {serp_results.get('GEO_MAP_0')}")
            data["region_data"] = []
        # City
        if (
            "GEO_MAP_1" in serp_results and
            isinstance(serp_results["GEO_MAP_1"], dict) and
            "interest_by_city" in serp_results["GEO_MAP_1"] and
            isinstance(serp_results["GEO_MAP_1"]["interest_by_city"], list)
        ):
            data["city_data"] = [
                {"geoName": city["name"], "values": {keyword: city["value"]}}
                for city in serp_results["GEO_MAP_1"]["interest_by_city"]
                if isinstance(city, dict) and "name" in city and "value" in city
            ]
        else:
            logger.error(f"SERP API GEO_MAP_1 response: {serp_results.get('GEO_MAP_1')}")
            data["city_data"] = []
        # Related queries
        if (
            "RELATED_QUERIES" in serp_results and
            isinstance(serp_results["RELATED_QUERIES"], dict) and
            "related_queries" in serp_results["RELATED_QUERIES"] and
            isinstance(serp_results["RELATED_QUERIES"]["related_queries"], dict)
        ):
            rq = serp_results["RELATED_QUERIES"]["related_queries"]
            data["related_queries"] = {keyword: rq}
        else:
            logger.error(f"SERP API RELATED_QUERIES response: {serp_results.get('RELATED_QUERIES')}")
            data["related_queries"] = {}

        return {
            'status': 'success',
            'metadata': {
                'keywords': [keyword],
                'timeframe': 'today 5-y',  # Always use 5 years timeframe
                'region': geo,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'serp_api'
            },
            'data': data
        }
    except Exception as e:
        logger.error(f"Error fetching data from SERP API: {str(e)}")
        return None
def get_trends_json(keywords, timeframe='today 5-y', geo='IN', analysis_options=None):
    """
    Fetch Google Trends data and return as JSON
    
    This is the main function used by the application to get trends data.
    Uses optimized fetching and caching to improve performance and avoid rate limiting.
    
    Parameters:
    - keywords: List of keywords or single keyword string
    - timeframe: Time period for analysis (default: 'today 5-y')
    - geo: Geographic region code (default: 'IN' for India)
    - analysis_options: Dictionary of options for different analysis types
    
    Returns:
    - Dictionary containing the trends data
    """
    # Store original timeframe for returning in response
    original_timeframe = timeframe
    
    try:
        logger.info(f"Fetching trends for keywords={keywords}, timeframe={timeframe}, geo={geo}")
        start_time = time.time()
        
        # Set default analysis options if not provided
        if analysis_options is None:
            analysis_options = {
                "include_time_trends": True,
                "include_state_analysis": True,
                "include_city_analysis": False,
                "include_related_queries": False,
                "state_only": False,
                "city_only": False
            }
        
        # Try first with proxy using the requested timeframe
        logger.info(f"Attempting to fetch trends with proxy using timeframe: {timeframe}")
        result = fetch_google_trends(keywords, timeframe, geo, analysis_options)
        
        # Check if we got valid data
        if result.get('status') == 'success' and result.get('data', {}).get('time_trends'):
            logger.info(f"Successfully fetched trends data with timeframe: {timeframe}")
            result['metadata']['timeframe'] = original_timeframe
            execution_time = time.time() - start_time
            logger.info(f"Trends data fetched in {execution_time:.2f} seconds")
            return result
        
        logger.warning(f"Failed to get data with original timeframe: {timeframe}")
        
        # Try direct connection without proxy
        logger.info(f"Trying direct connection with original timeframe: {timeframe}")
        direct_result = None
        try:
            direct_result = fetch_google_trends_direct(keywords, timeframe, geo, analysis_options)
            if direct_result.get('status') == 'success' and direct_result.get('data', {}).get('time_trends'):
                logger.info(f"Successfully fetched trends data with direct connection")
                direct_result['metadata']['timeframe'] = original_timeframe
                direct_result['metadata']['connection'] = 'direct'
                execution_time = time.time() - start_time
                logger.info(f"Trends data fetched in {execution_time:.2f} seconds")
                return direct_result
        except Exception as direct_err:
            logger.error(f"Error with direct connection: {str(direct_err)}")
        
        # If both Google Trends attempts failed, try SERP API as fallback
        logger.info("Attempting to fetch data from SERP API as fallback")
        if isinstance(keywords, list):
            keyword = keywords[0]  # SERP API only supports single keyword
        else:
            keyword = keywords
            
        serp_result = fetch_serp_trends(keyword, timeframe, geo)
        if serp_result:
            logger.info("Successfully fetched data from SERP API")
            serp_result['metadata']['timeframe'] = original_timeframe
            execution_time = time.time() - start_time
            logger.info(f"Trends data fetched in {execution_time:.2f} seconds")
            return serp_result
        
        # If all attempts failed, return error response
        logger.error("Failed to fetch trends data with all methods")
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return {
            "status": "error",
            "metadata": {
                "keywords": keywords if isinstance(keywords, list) else [keywords],
                "timeframe": original_timeframe,
                "region": geo,
                "timestamp": timestamp
            },
            "errors": ["Failed to fetch trends data - all methods failed"],
            "data": {
                "time_trends": [],
                "region_data": [],
                "city_data": [],
                "related_queries": {}
            }
        }
        
    except Exception as e:
        logger.error(f"Error in get_trends_json: {str(e)}")
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return {
            "status": "error",
            "metadata": {
                "keywords": keywords if isinstance(keywords, list) else [keywords],
                "timeframe": original_timeframe,
                "region": geo,
                "timestamp": timestamp
            },
            "errors": [str(e)],
            "data": {
                "time_trends": [],
                "region_data": [],
                "city_data": [],
                "related_queries": {}
            }
        }

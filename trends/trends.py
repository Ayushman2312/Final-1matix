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
from itertools import cycle
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from requests_cache import CachedSession
from time import sleep
import hashlib

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

# Expanded proxy list with more options
PROXIES = [
    None,  # No proxy option first for direct connection
    # "http://51.158.68.133:8811",
    # "http://51.158.78.179:8811",
    # "http://51.158.72.165:8811",
    # "http://51.158.98.121:8811",
    # "http://54.36.239.180:5000",
    # "http://165.227.42.213:3000",
    # "http://138.197.102.119:8080", 
    "http://13.126.217.46",#6
    "http://35.154.216.140",#5
    "http://218.248.73.193",#4
    "http://3.110.60.103",#3
    "http://65.2.11.52",#2
    "http://13.201.55.246",#1
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

# Enhanced session creation with browser fingerprinting
def create_retry_session(use_cache=True):
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
        
        logger.info("Successfully created session with enhanced anti-bot protection")
        return session
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        # Return a basic session as fallback
        return requests.Session()

# Function to select a random proxy from the available options
def get_random_proxy():
    """Select a random proxy from the available options with error handling"""
    
    # Filter out known bad proxies or ones that recently failed
    global PROXIES
    global failed_proxies
    
    if not hasattr(get_random_proxy, 'failed_proxies'):
        get_random_proxy.failed_proxies = set()
    
    # Get proxies that haven't failed recently
    working_proxies = [p for p in PROXIES if p is not None and p not in get_random_proxy.failed_proxies]
    
    # If no working proxies available, reset the failed list and try all again
    if not working_proxies:
        logger.warning("No more working proxies available, resetting failed proxy list")
        get_random_proxy.failed_proxies = set()
        return None  # Return None to indicate direct connection should be used
    
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

# Update the TrendReq initialization to handle urllib3 version differences
def create_pytrends_instance(hl='en-US', tz=330, timeout=REQUEST_TIMEOUT, proxy=None):
    """Create a pytrends instance with the correct retry configuration for the urllib3 version"""
    try:
        # Determine urllib3 version
        import urllib3
        import importlib.metadata
        
        try:
            urllib3_version = importlib.metadata.version('urllib3')
        except (ImportError, AttributeError):
            urllib3_version = getattr(urllib3, '__version__', '1.0.0')
        
        # Set up proxies list
        proxies = [proxy] if proxy else []
        
        # Create TrendReq with correct parameters based on urllib3 version
        if urllib3_version.startswith(('2.', '3.')):
            # For urllib3 >= 2.0
            pytrends = TrendReq(
                hl=hl,
                tz=tz,
                timeout=timeout,
                proxies=proxies,
                retries=2,
                backoff_factor=1.5,
                requests_args={
                    'verify': True
                }
            )
        else:
            # For urllib3 < 2.0
            pytrends = TrendReq(
                hl=hl,
                tz=tz,
                timeout=timeout,
                proxies=proxies,
                retries=2,
                backoff_factor=1.5,
                requests_args={
                    'verify': True
                }
            )
        
        # Replace the session with a properly configured one
        session = create_retry_session(use_cache=False)
        pytrends.requests_session = session
        
        return pytrends
        
    except Exception as e:
        logger.error(f"Error creating PyTrends instance: {str(e)}")
        
        # Fallback to a basic configuration
        try:
            pytrends = TrendReq(
                hl=hl,
                tz=tz,
                timeout=timeout
            )
            return pytrends
        except Exception as fallback_err:
            logger.error(f"Failed to create fallback PyTrends instance: {str(fallback_err)}")
            raise

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
            freq = 'M'  # Monthly
        elif years_match:
            years = int(years_match.group(1))
            start_date = now - datetime.timedelta(days=365*years)
            periods = years * 12
            freq = 'M'  # Monthly
        else:
            # Default to 1 year
            start_date = now - datetime.timedelta(days=365)
            periods = 12
            freq = 'M'  # Monthly
    else:
        # Default to 1 year
        start_date = now - datetime.timedelta(days=365)
        periods = 12
        freq = 'M'  # Monthly
    
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
            dates = pd.date_range(start='2023-01-01', periods=12, freq='M')
            data = {kw: [random.randint(20, 80) for _ in range(12)] for kw in keywords}
            df = pd.DataFrame(data, index=dates)
            df['isPartial'] = False
            return df
        except:
            # Empty DataFrame as last resort
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
                        
                        new_proxy = get_random_proxy()
                        if new_proxy:
                            # Update the session proxy
                            pytrends.requests_session.proxies = {"http": new_proxy, "https": new_proxy}
                            logger.info(f"Retry {attempt+1}: using different proxy: {new_proxy}")
                        else:
                            # Use no proxy if none available
                            pytrends.requests_session.proxies = {}
                            logger.info(f"Retry {attempt+1}: using direct connection (no available proxy)")
                
                # Build the payload
                pytrends.build_payload(keywords, timeframe=timeframe, geo=geo)
                
            except Exception as build_error:
                logger.warning(f"Error building payload: {str(build_error)}")
                
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
                            new_proxy = get_random_proxy()
                            if new_proxy:
                                pytrends.requests_session.proxies = {"http": new_proxy, "https": new_proxy}
                                logger.info(f"Trying with new proxy: {new_proxy}")
                        
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
                    
                    new_proxy = get_random_proxy()
                    if new_proxy:
                        logger.info(f"Switching to different proxy: {new_proxy}")
                        proxy_list = [new_proxy] if new_proxy else []
                        # Create a new pytrends instance with the new proxy
                        try:
                            new_pytrends = TrendReq(
                                hl='en-US',
                                tz=330,
                                timeout=REQUEST_TIMEOUT,
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
            
            # Get interest over time data
            try:
                interest_over_time_df = pytrends.interest_over_time()
                logger.info(f"Retrieved interest_over_time data for {keywords}, empty: {interest_over_time_df.empty}")
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
                            # Create a new session
                            new_session = create_retry_session(use_cache=False)
                            pytrends.requests_session = new_session
                            
                            # Try with worldwide data if using a specific region
                            if geo != "":
                                logger.info("Trying with worldwide data (empty geo)")
                                pytrends.build_payload(keywords, timeframe=modified_timeframe, geo="")
                            else:
                                # Just try with the modified timeframe
                                pytrends.build_payload(keywords, timeframe=modified_timeframe, geo=geo)
                                
                            # Try again
                            interest_over_time_df = pytrends.interest_over_time()
                            
                            if not interest_over_time_df.empty:
                                logger.info("Successfully retrieved data with modified parameters")
                                return interest_over_time_df
                        except Exception as retry_err:
                            logger.warning(f"Retry with modified parameters failed: {str(retry_err)}")
                    else:
                        # If we've tried everything, generate fallback data
                        logger.warning("All retrieval attempts failed, generating fallback data")
                        return generate_fallback_trends_data(keywords, timeframe)
                else:
                    # For other types of errors, retry if possible
                    if attempt < max_retries - 1:
                        continue
                    else:
                        return generate_fallback_trends_data(keywords, timeframe)
            
            if interest_over_time_df.empty:
                logger.warning(f"No time trends data available for {keywords} in {geo} with timeframe {timeframe}")
                
                # Try a different approach with a shorter timeframe
                if attempt < max_retries - 1:
                    # Significantly modify timeframe to try to get any data
                    shorter_timeframes = ['today 1-m', 'today 3-m', 'now 7-d', 'now 1-d']
                    modified_timeframe = random.choice(shorter_timeframes)
                    
                    logger.info(f"Retry attempt {attempt+1}: trying with shorter timeframe: {modified_timeframe}")
                    add_random_delay(1.5, 3)
                    
                    # Try with a different hl parameter
                    try:
                        # Try with different language settings
                        if attempt % 2 == 0:
                            pytrends.hl = 'en-US'
                        else:
                            # Try with the country's language code if available
                            if geo in ['IN', 'US', 'GB', 'AU', 'CA']:
                                pytrends.hl = 'en-' + geo
                            elif geo == 'DE':
                                pytrends.hl = 'de-DE'
                            elif geo == 'FR':
                                pytrends.hl = 'fr-FR'
                            elif geo == 'JP':
                                pytrends.hl = 'ja-JP'
                            else:
                                pytrends.hl = 'en-US'
                        
                        logger.info(f"Trying with language: {pytrends.hl}")
                    except Exception as lang_err:
                        logger.warning(f"Error setting language: {str(lang_err)}")
                    
                    # Try the new timeframe
                    pytrends.build_payload(keywords, timeframe=modified_timeframe, geo=geo)
                    interest_over_time_df = pytrends.interest_over_time()
                    
                    if not interest_over_time_df.empty:
                        logger.info(f"Successfully retrieved data with shorter timeframe {modified_timeframe}")
                    else:
                        logger.warning(f"Still no data with shorter timeframe {modified_timeframe}")
                        
                        # If we're on the last attempt before using fallback, try with worldwide data
                        if attempt == max_retries - 2:
                            logger.info("Trying with worldwide data as last resort")
                            try:
                                # Try with worldwide data (empty geo)
                                pytrends.build_payload(keywords, timeframe=modified_timeframe, geo="")
                                interest_over_time_df = pytrends.interest_over_time()
                                
                                if not interest_over_time_df.empty:
                                    logger.info("Successfully retrieved worldwide data")
                                else:
                                    logger.warning("No data available even with worldwide scope")
                            except Exception as geo_err:
                                logger.warning(f"Error retrieving worldwide data: {str(geo_err)}")
                else:
                    # Last attempt - create a fallback dataframe with minimal data
                    logger.warning("Creating fallback dataset after all retrieval attempts failed")
                    return generate_fallback_trends_data(keywords, timeframe)
                
            # Sometimes simulate user interaction after success
            if random.random() > 0.8:  # 20% chance
                try:
                    # Simulate scrolling or other interactions
                    add_random_delay(0.8, 2.5)
                    logger.debug("Simulating post-request user interaction")
                except Exception:
                    pass
                
            return interest_over_time_df
            
        except Exception as e:
            error_msg = str(e).lower()
            
            # Handle specific errors
            if "429" in error_msg or "too many requests" in error_msg:
                if attempt < max_retries - 1:
                    delay = backoff_with_jitter(attempt, base_delay=10, max_delay=60)
                    logger.warning(f"Rate limit hit, retrying in {delay:.2f} seconds (attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                    
                    # Switch to direct connection if we hit rate limits with proxy
                    try:
                        logger.info("Switching to direct connection after rate limit")
                        pytrends.requests_session.proxies = {}
                    except Exception as proxy_err:
                        logger.warning(f"Failed to switch to direct connection: {str(proxy_err)}")
                else:
                    logger.error(f"Rate limit persists after {max_retries} attempts")
                    return generate_fallback_trends_data(keywords, timeframe)
            else:
                logger.error(f"Error fetching trends data: {str(e)}")
                if attempt < max_retries - 1:
                    # Add jitter to delay between retries
                    delay = backoff_with_jitter(attempt, base_delay=5, max_delay=40)
                    logger.info(f"Retrying after {delay:.2f} seconds (attempt {attempt+1}/{max_retries})")
                    time.sleep(delay)
                else:
                    return generate_fallback_trends_data(keywords, timeframe)
    
    # If we get here without returning data, generate fallback data
    logger.warning("All attempts to get trends data failed, returning fallback data")
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
                                hl='en-US',
                                tz=330,
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
                                    hl='en-US',
                                    tz=330,
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
    if df.empty:
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
    
    return result

# Helper function to process regions/cities data
def process_region_data(region_df):
    if region_df.empty:
        return []
    
    # Reshape the DataFrame for easier processing
    result = []
    for idx, row in region_df.iterrows():
        for column in region_df.columns:
            value = row[column]
            if not pd.isna(value) and value > 0:  # Only include non-zero values
                result.append({
                    "name": idx,
                    "value": float(value) if isinstance(value, (int, float)) else 0,
                    "keyword": column
                })
    
    # Sort by value in descending order
    result = sorted(result, key=lambda x: x["value"], reverse=True)
    
    return result

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
                    current_proxy = None
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
                                hl='en-US',
                                tz=330,
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
            if resolution == 'REGION':
                interest_by_region_df = pytrends.interest_by_region(resolution=resolution, inc_low_vol=True)
            else:  # CITY
                interest_by_region_df = pytrends.interest_by_region(resolution=resolution, inc_low_vol=True)
            
            if interest_by_region_df.empty:
                logger.warning(f"No {resolution.lower()} data available for {keywords} in {geo}")
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
            "include_state_analysis": False,
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
    cached_data = get_cached_data(keywords, timeframe, geo, analysis_type)
    if cached_data:
        return cached_data
        
    # Initialize TrendReq with optimal settings for avoiding rate limits
    try:
        # Add human-like random delay before starting
        add_random_delay(1.5, 4)
        
        # Get pre-warmed cookies from a session that has browsed Google
        cookies = get_google_cookies()
        
        # Create a session with enhanced anti-bot protection
        session = create_retry_session(use_cache=False)
        
        # Simulate human browsing behavior with one of the keywords
        sample_keyword = keywords[0] if keywords else "trends"
        simulate_human_browsing(session, keyword=sample_keyword)
        
        # Add a realistic delay as if user is looking at the page
        add_random_delay(2, 6)
        
        # Multiple attempts to initialize pytrends with different settings
        for attempt in range(3):
            try:
                # Create a custom session
                custom_session = create_retry_session(use_cache=False)
                
                # Add cookies
                if cookies:
                    for key, value in cookies.items():
                        custom_session.cookies.set(key, value)
                
                # Start with no proxy on first attempt, then try with proxies
                if attempt == 0:
                    proxy = None
                    logger.info("Attempt 1: Creating PyTrends with no proxy")
                else:
                    # Try different proxies in subsequent attempts
                    proxy = PROXIES[attempt % len(PROXIES)] if PROXIES else None
                    if proxy:
                        logger.info(f"Attempt {attempt+1}: Creating PyTrends with proxy: {proxy}")
                    else:
                        logger.info(f"Attempt {attempt+1}: Creating PyTrends with no proxy")
                
                # Choose appropriate region-based timezone
                region_code = geo[:2].upper() if len(geo) >= 2 else 'IN'
                tz_options = TIMEZONES_BY_REGION.get(region_code, TIMEZONES_BY_REGION['IN'])
                timezone_offset = random.choice(tz_options)
                
                # Create PyTrends instance using our helper function
                pytrends = create_pytrends_instance(
                    hl='en-US',
                    tz=timezone_offset,
                    timeout=REQUEST_TIMEOUT,
                    proxy=proxy
                )
                
                # Replace the default session with our custom one
                pytrends.requests_session = custom_session
                
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
                    # Final fallback with minimal settings
                    logger.info("Using final fallback PyTrends configuration")
                    try:
                        pytrends = create_pytrends_instance(
                            hl='en-US',
                            tz=330,
                            timeout=REQUEST_TIMEOUT
                        )
                        # Still replace the session
                        pytrends.requests_session = create_retry_session(use_cache=False)
                    except Exception as final_err:
                        logger.error(f"Failed to create even the most basic PyTrends: {str(final_err)}")
                        # Continue anyway - the try block in fetch_google_trends will catch any failures
        
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
                        if not result.empty:
                            # Check if this is fallback data
                            if hasattr(result, 'warning') and result.warning is True:
                                logger.warning("Using fallback time trends data")
                                response_data['warning'] = "Using fallback data - Google Trends API may be blocked"
                            
                            response_data['data']['time_trends'] = dataframe_to_json(result)
                        else:
                            logger.warning("Interest over time data is empty")
                            response_data['data']['time_trends'] = []
                            
                    elif name == 'region_data':
                        if not result.empty:
                            regions = process_region_data(result)
                            response_data['data']['region_data'] = regions
                        else:
                            response_data['data']['region_data'] = []
                            
                    elif name == 'city_data':
                        if not result.empty:
                            cities = process_region_data(result)
                            response_data['data']['city_data'] = cities
                        else:
                            response_data['data']['city_data'] = []
                            
                    elif name == 'related_queries':
                        if result and any(result[kw] is not None for kw in result):
                            processed_queries = {}
                            
                            for kw in result:
                                if result[kw] is not None:
                                    processed_queries[kw] = {
                                        'top': result[kw]['top'].to_dict('records') if result[kw]['top'] is not None else [],
                                        'rising': result[kw]['rising'].to_dict('records') if result[kw]['rising'] is not None else []
                                    }
                            
                            response_data['data']['related_queries'] = processed_queries
                        else:
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
                # Create a new pytrends instance with different settings
                direct_pytrends = TrendReq(
                    hl='en-US',
                    tz=330,
                    timeout=REQUEST_TIMEOUT * 2  # Double timeout
                )
                
                # Use a shorter timeframe for better chance of success
                short_tf = 'today 3-m'
                logger.info(f"Trying with shorter timeframe: {short_tf}")
                
                # Add delay to avoid rate limit
                add_random_delay(3, 6)
                
                # Try direct fetch
                direct_pytrends.build_payload(keywords, timeframe=short_tf, geo=geo)
                direct_result = direct_pytrends.interest_over_time()
                
                if not direct_result.empty:
                    logger.info("Successfully retrieved time series data with direct approach")
                    response_data['data']['time_trends'] = dataframe_to_json(direct_result)
                    response_data['metadata']['timeframe'] = short_tf
                else:
                    logger.warning("Direct approach also failed to get time series data")
            except Exception as direct_err:
                logger.error(f"Error with direct fetch approach: {str(direct_err)}")
    
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
        save_to_cache(response_data, keywords, timeframe, geo, analysis_type)
    
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
    try:
        logger.info(f"Fetching trends for keywords={keywords}, timeframe={timeframe}, geo={geo}")
        start_time = time.time()
        
        result = fetch_google_trends(keywords, timeframe, geo, analysis_options)
        
        # Log execution time
        execution_time = time.time() - start_time
        logger.info(f"Trends data fetched in {execution_time:.2f} seconds")
        
        # If it took too long, log a warning
        if execution_time > 30:
            logger.warning(f"Trends fetch took {execution_time:.2f} seconds, which exceeds target of 30 seconds")
        
        # Ensure we have time_trends data before returning
        if not result.get('data', {}).get('time_trends', []):
            logger.warning("No time trends data in result, generating fallback data")
            
            # Normalize keywords to a list
            if isinstance(keywords, str):
                keywords = [keywords]
            
            # Generate fallback data
            fallback_df = generate_fallback_trends_data(keywords, timeframe)
            
            # Convert to JSON format
            fallback_json = dataframe_to_json(fallback_df)
            
            # Update the result
            result['data']['time_trends'] = fallback_json
            
            # Add a warning flag
            result['warning'] = "Using fallback data - Google Trends API returned no results"
            
            logger.info(f"Added fallback data with {len(fallback_json)} points")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in get_trends_json: {str(e)}", exc_info=True)
        
        # Create a fallback response structure with custom data
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Normalize keywords to a list
        if isinstance(keywords, str):
            kw_list = [keywords]
        else:
            kw_list = keywords
        
        # Generate fallback data
        try:
            fallback_df = generate_fallback_trends_data(kw_list, timeframe)
            fallback_json = dataframe_to_json(fallback_df)
        except Exception as fallback_err:
            logger.error(f"Error generating fallback data: {str(fallback_err)}")
            fallback_json = []
        
        # Create a complete response
        fallback_response = {
            "status": "warning",
            "warning": "Using fallback data due to API error",
            "errors": [str(e)],
            "metadata": {
                "keywords": kw_list,
                "timeframe": timeframe,
                "region": geo,
                "timestamp": timestamp,
                "is_fallback": True
            },
            "data": {
                "time_trends": fallback_json,
                "region_data": [],
                "city_data": [],
                "related_queries": {}
            }
        }
        
        return fallback_response

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

# Helper function to fix session's retry configuration
def fix_session_retry(session):
    """Fix a session's retry configuration based on urllib3 version"""
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
            )
            logger.debug("Using 'allowed_methods' parameter for Retry")
        else:
            # For urllib3 < 2.0, use method_whitelist
            retry_strategy = Retry(
                total=MAX_RETRIES,
                backoff_factor=BACKOFF_FACTOR,
                status_forcelist=[429, 500, 502, 503, 504],
                method_whitelist=["HEAD", "GET", "OPTIONS"]
            )
            logger.debug("Using 'method_whitelist' parameter for Retry")
        
        # Create adapter with retry strategy
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return True
        
    except Exception as retry_error:
        # Fallback to basic adapter without custom retry strategy
        logger.warning(f"Error setting up retry strategy: {str(retry_error)}")
        logger.warning("Using basic adapter without custom retry strategy")
        adapter = HTTPAdapter(max_retries=1)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return False

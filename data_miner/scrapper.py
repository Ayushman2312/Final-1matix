"""
Advanced AI-powered web scraper with proxy rotation and anti-detection capabilities.
Extracts validated mobile numbers and email addresses from websites based on keywords.
"""

import os
import re
import json
import time
import random
import logging
import traceback
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, List, Set, Tuple, Union, Optional, Any
from wsgiref import headers
import base64
import tempfile
import zipfile
import io
import requests
from PIL import Image
import pytesseract

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, WebDriverException, NoSuchElementException
)
from selenium_stealth import stealth
from fake_useragent import UserAgent
from seleniumwire import webdriver as wire_webdriver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("AdvancedScraper")

# Try to configure Tesseract path for OCR CAPTCHA recognition
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Change this on different systems
if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

# Anti-CAPTCHA API key - Replace with your actual key
ANTI_CAPTCHA_API_KEY = ""  # No API key - using alternative CAPTCHA handling

class AdvancedWebScraper:
    """Advanced web scraper with anti-detection features and proxy rotation."""
    
    # Blocked domains that should be avoided
    BLOCKED_DOMAINS = [
        'justdial.com', 'yellowpages.com', 'whitepages.com',
        'facebook.com', 'instagram.com', 'twitter.com', 'linkedin.com'
    ]
    
    # Disposable email domains to filter out
    DISPOSABLE_EMAIL_DOMAINS = [
        'mailinator.com', 'tempmail.com', 'temp-mail.org', 'guerrillamail.com',
        'yopmail.com', 'sharklasers.com', 'trashmail.com', 'throwawaymail.com'
    ]
    
    # Spam TLDs to filter out
    SPAM_TLDS = ['xyz', 'top', 'club', 'live', 'stream', 'racing']
    
    # Contact page keywords for URL prioritization
    CONTACT_KEYWORDS = [
        'contact', 'reach', 'connect', 'touch', 'support', 'help',
        'about', 'company', 'team', 'get-in-touch', 'getintouch'
    ]
    
    def __init__(
        self,
        proxies: Optional[List[Dict[str, str]]] = None,
        user_agents: Optional[List[str]] = None,
        captcha_service_api: Optional[str] = None,
        headless: bool = True,
        max_concurrent_threads: int = 5,
        timeout: int = 30,
        max_retries: int = 3,
        request_delay: Tuple[float, float] = (1.0, 5.0),
        debug: bool = False,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize the web scraper with the given configuration.
        
        Args:
            proxies: List of proxy configurations (each with format {"http": "http://user:pass@host:port"})
            user_agents: List of user agent strings
            captcha_service_api: API key for CAPTCHA solving service
            headless: Whether to run browsers in headless mode (always True now)
            max_concurrent_threads: Maximum number of concurrent threads
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
            request_delay: Tuple of (min_delay, max_delay) in seconds
            debug: Enable debug mode
            cache_dir: Directory to cache results
        """

        # Define default proxy if none provided
        proxy = 'geo.iproyal.com:11200'
        proxy_auth = 'vnkl9BGvMRlmvWfO:EjFoKHcjcchVYwZ9'
        proxies = {
        'http': f'socks5://{proxy_auth}@{proxy}',
        'https': f'socks5://{proxy_auth}@{proxy}'
        }
        
        # Use provided proxies or default
        self.proxies = proxies if proxies is not None else [proxies]
        
        # Ensure proxies is a list
        if isinstance(self.proxies, dict):
            self.proxies = [self.proxies]
            
        self.captcha_service_api = captcha_service_api
        self.headless = True  # Always force headless mode regardless of parameter
        self.max_concurrent_threads = max_concurrent_threads
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_delay, self.max_delay = request_delay
        self.debug = debug
        self.cache_dir = cache_dir
        
        # Create cache directory if specified
        if self.cache_dir and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
        
        # Initialize user agents
        self.user_agent_generator = UserAgent()
        self.user_agents = user_agents or []
        
        # Track the current proxy and user agent index
        self.current_proxy_index = 0
        self.current_ua_index = 0
        
        # Initialize regex patterns for different countries and formats
        self.init_regex_patterns()
        
        # Reusable session with retry and backoff
        self.session = self._create_session()
        
        # Initialize results container with counters
        self.results = {
            'emails': set(),
            'phones': set(),
            'processed_urls': set(),
            'failed_urls': set(),
            'counters': {
                'emails_found': 0,
                'phones_found': 0,
                'urls_processed': 0,
                'urls_failed': 0,
                'captchas_encountered': 0,
                'captchas_solved': 0,
                'proxy_errors': 0
            }
        }
        
        if self.debug:
            logger.setLevel(logging.DEBUG)
    
    def init_regex_patterns(self):
        """Initialize regex patterns for contact info extraction."""
        # Enhanced email pattern with better validation
        self.email_pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
        
        # Additional email pattern for obfuscated emails (e.g., "email at domain dot com")
        self.obfuscated_email_pattern = r'([a-zA-Z0-9._%+\-]+)\s+(?:@|at|\[at\]|\(at\))\s+([a-zA-Z0-9.\-]+)(?:\.|\s+(?:dot|\[dot\]|\(dot\)))\s+([a-zA-Z]{2,})'
        
        # Pattern to find email addresses in HTML attributes
        self.email_attr_pattern = r'(?:mailto:|email=|mail=|contact=|to=)([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})'
        
        # Phone patterns for different countries and formats
        # International format
        intl_pattern = r'(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        
        # US/Canada pattern
        us_pattern = r'(?:(?:\+?1[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?))?\d{3}[-.\s]?\d{4}'
        
        # UK pattern
        uk_pattern = r'(?:\+?44[-.\s]?)?(?:\(?\d{1,5}\)?[-.\s]?)?\d{4,10}'
        
        # India pattern - improved to focus on valid Indian mobile numbers
        # Must start with +91 or 91, followed by a space/dash, then a digit 6-9, followed by 9 more digits
        india_pattern = r'(?:\+91|91)[-.\s]?[6789]\d{9}'
        
        # Additional India pattern for numbers without country code
        india_no_cc_pattern = r'[6789]\d{9}'
        
        # Generic international
        generic_pattern = r'(?:\+?\d{1,4}[-.\s]?)?\d{5,15}'
        
        # Combined pattern
        self.phone_patterns = [
            india_pattern, india_no_cc_pattern, intl_pattern, us_pattern, uk_pattern, generic_pattern
        ]
    
    def _create_session(self) -> requests.Session:
        """Create and configure requests session with retry logic."""
        session = requests.Session()
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD", "POST"],
            raise_on_status=False,  # Don't raise exceptions on status
            respect_retry_after_header=True
        )
        
        # Create connection pool with increased max size
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=20,
            pool_block=False
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set default headers to mimic Chrome browser
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'DNT': '1',  # Do Not Track
            'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        })
        
        # Disable SSL verification
        session.verify = False
        
        # Suppress SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        return session
    
    def _get_random_user_agent(self) -> str:
        """Get a random user agent string."""
        if self.user_agents:
            return random.choice(self.user_agents)
        return self.user_agent_generator.random
    
    def _get_next_proxy(self) -> Optional[Dict[str, str]]:
        """Get the next proxy from the rotation with improved reliability."""
        # Always use our specified proxy for reliability
        proxy = 'geo.iproyal.com:12321'
        proxy_auth = 'vnkl9BGvMRlmvWfO:EjFoKHcjcchVYwZ9_country-in'
        default_proxy = {
            'http': f'http://{proxy_auth}@{proxy}',
            'https': f'http://{proxy_auth}@{proxy}'
        }
        
        # Log proxy usage (masked password)
        logger.debug(f"Using proxy: geo.iproyal.com:12321 (authenticated)")
        
        return default_proxy
    
    def _initialize_selenium(self, proxy: Optional[Dict[str, str]] = None) -> Optional[webdriver.Chrome]:
        """Initialize a Selenium WebDriver with stealth and anti-detection capabilities."""
        max_retries = 3
        retry_delay = 2
        
        for retry in range(max_retries):
            try:
                options = Options()
                
                # Enhanced headless setup with improved anti-detection
                options.add_argument("--headless=new")
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                
                # Common options for stability and performance
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-notifications")
                options.add_argument("--disable-infobars")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-automation")
                
                # Performance optimizations
                options.add_argument("--disable-3d-apis")
                options.add_argument("--disable-canvas-aa")
                options.add_argument("--disable-accelerated-2d-canvas")
                options.add_argument("--disable-bundled-ppapi-flash")
                options.add_argument("--disable-logging")
                options.add_argument("--disable-web-security")
                options.add_argument("--ignore-certificate-errors")
                options.add_argument("--allow-running-insecure-content")
                
                # Set a high-quality user agent
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                options.add_argument(f"--user-agent={user_agent}")
                
                # Set window size to mimic real browser
                options.add_argument("--window-size=1920,1080")
                
                # Set language
                options.add_argument("--lang=en-US,en;q=0.9")
                
                # Additional preference settings
                prefs = {
                    "profile.default_content_setting_values.notifications": 2,
                    "profile.default_content_settings.popups": 0,
                    "download.default_directory": "/dev/null",
                    "download.prompt_for_download": False,
                    "credentials_enable_service": False,
                    "profile.password_manager_enabled": False,
                    # Disable images and CSS for faster loading
                    "profile.managed_default_content_settings.images": 2,
                    "profile.default_content_setting_values.css": 2
                }
                options.add_experimental_option("prefs", prefs)
                
                # Always use our reliable proxy
                proxy = self._get_next_proxy()
                
                # Extract proxy details
                proxy_url = None
                username = None
                password = None
                
                if 'http' in proxy:
                    proxy_url = proxy['http']
                elif 'https' in proxy:
                    proxy_url = proxy['https']
                
                if proxy_url:
                    # Remove protocol prefix
                    proxy_url = proxy_url.replace('http://', '').replace('https://', '')
                    
                    # Handle authentication
                    if '@' in proxy_url:
                        auth, host_port = proxy_url.split('@')
                        username, password = auth.split(':')
                        
                        # For ChromeDriver, use plugin approach for authenticated proxies
                        manifest_json = """
                        {
                            "version": "1.0.0",
                            "manifest_version": 2,
                            "name": "Chrome Proxy",
                            "permissions": [
                                "proxy",
                                "tabs",
                                "unlimitedStorage",
                                "storage",
                                "<all_urls>",
                                "webRequest",
                                "webRequestBlocking"
                            ],
                            "background": {
                                "scripts": ["background.js"]
                            },
                            "minimum_chrome_version":"22.0.0"
                        }
                        """
                        
                        background_js = """
                        var config = {
                                mode: "fixed_servers",
                                rules: {
                                  singleProxy: {
                                    scheme: "http",
                                    host: "%s",
                                    port: parseInt(%s)
                                  },
                                  bypassList: ["localhost"]
                                }
                              };

                        chrome.proxy.settings.set({value: config, scope: "regular"}, function() {});

                        function callbackFn(details) {
                            return {
                                authCredentials: {
                                    username: "%s",
                                    password: "%s"
                                }
                            };
                        }

                        chrome.webRequest.onAuthRequired.addListener(
                                    callbackFn,
                                    {urls: ["<all_urls>"]},
                                    ['blocking']
                        );
                        """ % (host_port.split(':')[0], host_port.split(':')[1], username, password)
                        
                        # Create a temporary directory for the extension
                        plugin_dir = tempfile.mkdtemp()
                        manifest_file = os.path.join(plugin_dir, 'manifest.json')
                        background_file = os.path.join(plugin_dir, 'background.js')
                        
                        with open(manifest_file, 'w') as f:
                            f.write(manifest_json)
                        with open(background_file, 'w') as f:
                            f.write(background_js)
                        
                        # Pack the extension
                        plugin_file = os.path.join(plugin_dir, 'proxy_auth_plugin.zip')
                        with zipfile.ZipFile(plugin_file, 'w') as zp:
                            zp.write(manifest_file, 'manifest.json')
                            zp.write(background_file, 'background.js')
                        
                        options.add_extension(plugin_file)
                        logger.debug(f"Added proxy authentication plugin for {host_port}")
                    else:
                        # No authentication needed, just set the proxy
                        options.add_argument(f'--proxy-server={proxy_url}')
                        logger.debug(f"Set proxy server to {proxy_url}")
                
                # Initialize WebDriver with additional arguments for stability
                # Use ChromeDriverManager to ensure the driver is available and compatible
                from webdriver_manager.chrome import ChromeDriverManager
                
                try:
                    # Try to use ChromeDriverManager to get the appropriate driver
                    service = Service(ChromeDriverManager().install())
                    logger.info("Using ChromeDriverManager to initialize driver")
                    driver = webdriver.Chrome(service=service, options=options)
                except Exception as e:
                    logger.warning(f"ChromeDriverManager initialization failed: {e}")
                    # Fall back to default Service
                    service = Service()
                    driver = webdriver.Chrome(service=service, options=options)
                
                # Apply enhanced stealth mode settings
                try:
                    stealth(
                        driver,
                        languages=["en-US", "en"],
                        vendor="Google Inc.",
                        platform="Win32",
                        webgl_vendor="Intel Inc.",
                        renderer="Intel Iris OpenGL Engine",
                        fix_hairline=True,
                    )
                except Exception as e:
                    logger.warning(f"Could not apply stealth mode: {e}")
                
                # Additional scripts to evade detection
                try:
                    evasion_js = """
                    // Overwrite the 'webdriver' property to prevent detection
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => false,
                    });
                    
                    // Add missing Chrome functions
                    if (!window.chrome) {
                        window.chrome = {};
                    }
                    if (!window.chrome.runtime) {
                        window.chrome.runtime = {};
                    }
                    
                    // Overwrite permissions.query
                    const originalQuery = window.navigator.permissions.query;
                    window.navigator.permissions.query = (parameters) => (
                        parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                    );
                    
                    // Add plugins array
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    
                    // Add language consistency
                    Object.defineProperty(navigator, 'language', {
                        get: () => 'en-US',
                    });
                    
                    // Add platform consistency
                    Object.defineProperty(navigator, 'platform', {
                        get: () => 'Win32',
                    });
                    """
                    driver.execute_script(evasion_js)
                except Exception as e:
                    logger.warning(f"Could not apply evasion script: {e}")
                
                # Set page load timeout to avoid hanging
                driver.set_page_load_timeout(self.timeout)
                
                # Wait a bit to ensure all evasion techniques are in place
                time.sleep(1)
                
                return driver
            
            except Exception as e:
                logger.error(f"Error initializing Selenium (attempt {retry+1}/{max_retries}): {e}")
                
                if retry < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("All retries failed for initializing Selenium")
                    if self.debug:
                        traceback.print_exc()
        
        return None
    
    def _detect_captcha(self, driver) -> bool:
        """
        Enhanced detection of CAPTCHAs on the page.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            bool: True if CAPTCHA is detected, False otherwise
        """
        try:
            # Visual indicators
            captcha_indicators = [
                "//iframe[contains(@src, 'recaptcha')]",
                "//iframe[contains(@src, 'captcha')]",
                "//*[contains(text(), 'captcha')]",
                "//*[contains(@class, 'captcha')]",
                "//*[contains(@id, 'captcha')]",
                "//div[@class='g-recaptcha']",
                "//div[contains(@class, 'h-captcha')]",
                "//div[contains(@data-sitekey, 'recaptcha')]",
                "//div[contains(@data-sitekey, 'hcaptcha')]",
                "//div[contains(@class, 'antigate_solver')]",
                "//input[contains(@id, 'captcha')]",
                "//img[contains(@src, 'captcha')]"
            ]
            
            for indicator in captcha_indicators:
                elements = driver.find_elements(By.XPATH, indicator)
                if elements:
                    logger.debug(f"CAPTCHA detected with selector: {indicator}")
                    self.results['counters']['captchas_encountered'] += 1
                    return True
            
            # Check for text indicators
            captcha_text_indicators = [
                'captcha', 'robot', 'verify you are human', 'security check', 
                'prove you\'re not a robot', 'bot check', 'verification'
            ]
            
            page_text = driver.page_source.lower()
            for text in captcha_text_indicators:
                if text in page_text:
                    logger.debug(f"CAPTCHA detected with text indicator: {text}")
                    self.results['counters']['captchas_encountered'] += 1
                    return True
            
            # Check URL for CAPTCHA indicators
            current_url = driver.current_url.lower()
            if 'captcha' in current_url or 'challenge' in current_url:
                logger.debug(f"CAPTCHA detected in URL: {current_url}")
                self.results['counters']['captchas_encountered'] += 1
                return True
            
            # Check for Google reCAPTCHA API calls
            try:
                recaptcha_present = driver.execute_script(
                    "return typeof(___grecaptcha_cfg) !== 'undefined' || "
                    "document.querySelector('iframe[src*=\"recaptcha\"]') !== null || "
                    "document.querySelector('div.g-recaptcha') !== null"
                )
                if recaptcha_present:
                    logger.debug("reCAPTCHA detected via JavaScript check")
                    self.results['counters']['captchas_encountered'] += 1
                    return True
            except Exception:
                pass
                
            # Check for unusual redirects or security pages
            security_domains = ['captcha', 'challenge', 'security', 'verify', 'check']
            current_domain = urllib.parse.urlparse(driver.current_url).netloc
            for domain in security_domains:
                if domain in current_domain:
                    logger.debug(f"Security/CAPTCHA domain detected: {current_domain}")
                    self.results['counters']['captchas_encountered'] += 1
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting CAPTCHA: {e}")
            return False
    
    def _solve_captcha(self, driver) -> bool:
        """
        Enhanced CAPTCHA handling without using external API services.
        
        Args:
            driver: Selenium WebDriver instance
            
        Returns:
            bool: True if CAPTCHA is bypassed, False otherwise
        """
        try:
            logger.info("Attempting to handle CAPTCHA without external services")
            
            # First, try to find if there's a simple checkbox CAPTCHA
            try:
                # Look for common reCAPTCHA checkbox elements
                checkboxes = driver.find_elements(By.CSS_SELECTOR, ".recaptcha-checkbox, .g-recaptcha-response, input[type='checkbox']")
                for checkbox in checkboxes:
                    if checkbox.is_displayed() and checkbox.is_enabled():
                        logger.info("Found CAPTCHA checkbox, attempting to click")
                        checkbox.click()
                        time.sleep(2)
                        # Check if CAPTCHA is still present
                        if not self._detect_captcha(driver):
                            self.results['counters']['captchas_solved'] += 1
                            return True
            except Exception as e:
                logger.debug(f"No clickable CAPTCHA checkbox found: {e}")
            
            # Try to find and click on "I'm not a robot" text or button
            try:
                robot_elements = driver.find_elements(By.XPATH, 
                    "//*[contains(text(), 'not a robot') or contains(text(), 'Not a Robot') or contains(@alt, 'CAPTCHA')]")
                for elem in robot_elements:
                    if elem.is_displayed() and elem.is_enabled():
                        logger.info("Found 'not a robot' element, attempting to click")
                        elem.click()
                        time.sleep(2)
                        # Check if CAPTCHA is still present
                        if not self._detect_captcha(driver):
                            self.results['counters']['captchas_solved'] += 1
                            return True
            except Exception as e:
                logger.debug(f"No clickable 'not a robot' element found: {e}")
            
            # Try to find and interact with CAPTCHA iframe
            try:
                iframes = driver.find_elements(By.TAG_NAME, "iframe")
                for iframe in iframes:
                    if "recaptcha" in iframe.get_attribute("src").lower():
                        logger.info("Found reCAPTCHA iframe, attempting to interact")
                        driver.switch_to.frame(iframe)
                        
                        # Look for checkbox inside iframe
                        checkbox = driver.find_element(By.CSS_SELECTOR, ".recaptcha-checkbox")
                        if checkbox.is_displayed() and checkbox.is_enabled():
                            checkbox.click()
                            time.sleep(2)
                            driver.switch_to.default_content()
                            # Check if CAPTCHA is still present
                            if not self._detect_captcha(driver):
                                self.results['counters']['captchas_solved'] += 1
                                return True
                            
                        driver.switch_to.default_content()
            except Exception as e:
                logger.debug(f"No interactable CAPTCHA iframe found: {e}")
                driver.switch_to.default_content()
            
            # If we can't solve the CAPTCHA, try to bypass by refreshing the page
            logger.info("Attempting to bypass CAPTCHA by refreshing the page")
            driver.refresh()
            time.sleep(3)
            
            # Check if CAPTCHA is still present
            if not self._detect_captcha(driver):
                logger.info("CAPTCHA appears to be gone after refresh")
                self.results['counters']['captchas_solved'] += 1
                return True
            
            # Try waiting a bit longer - some CAPTCHAs expire
            logger.info("Waiting to see if CAPTCHA expires")
            time.sleep(5)
            if not self._detect_captcha(driver):
                logger.info("CAPTCHA appears to have expired")
                self.results['counters']['captchas_solved'] += 1
                return True
            
            # As a last resort, try to submit the form anyway
            try:
                submit_buttons = driver.find_elements(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
                if submit_buttons:
                    logger.info("Attempting to submit form despite CAPTCHA")
                    submit_buttons[0].click()
                    time.sleep(2)
                    # Check if CAPTCHA is still present
                    if not self._detect_captcha(driver):
                        logger.info("Form submission bypassed CAPTCHA")
                        self.results['counters']['captchas_solved'] += 1
                        return True
            except Exception as e:
                logger.debug(f"Could not submit form: {e}")
            
            logger.warning("Could not bypass CAPTCHA without API key")
            return False
            
        except Exception as e:
            logger.error(f"Error in CAPTCHA handling: {e}")
            return False
    
    def _solve_recaptcha_v2(self, driver) -> bool:
        """Attempt to handle Google reCAPTCHA v2 without API."""
        logger.warning("Cannot solve reCAPTCHA v2 without API key - attempting bypass")
        
        try:
            # Try to find and click the checkbox
            try:
                driver.switch_to.default_content()
                frames = driver.find_elements(By.TAG_NAME, "iframe")
                for frame in frames:
                    if "recaptcha" in frame.get_attribute("src").lower():
                        driver.switch_to.frame(frame)
                        checkbox = driver.find_element(By.CSS_SELECTOR, ".recaptcha-checkbox")
                        if checkbox.is_displayed():
                            checkbox.click()
                            time.sleep(2)
                            driver.switch_to.default_content()
                            break
            except Exception:
                driver.switch_to.default_content()
            
            # Try to submit the form anyway
            submit_buttons = driver.find_elements(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
            if submit_buttons:
                submit_buttons[0].click()
                time.sleep(2)
            
            # Try to refresh and see if CAPTCHA disappears
            driver.refresh()
            time.sleep(3)
            
            return not self._detect_captcha(driver)
            
        except Exception as e:
            logger.error(f"Error in reCAPTCHA v2 bypass attempt: {e}")
            return False
    
    def _solve_recaptcha_v3(self, driver) -> bool:
        """Attempt to handle Google reCAPTCHA v3 without API."""
        logger.warning("Cannot solve reCAPTCHA v3 without API key - attempting bypass")
        
        try:
            # reCAPTCHA v3 is invisible and score-based
            # Try to submit the form anyway and hope for the best
            submit_buttons = driver.find_elements(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
            if submit_buttons:
                submit_buttons[0].click()
                time.sleep(2)
            
            # Try to refresh and see if we can proceed
            driver.refresh()
            time.sleep(3)
            
            return not self._detect_captcha(driver)
            
        except Exception as e:
            logger.error(f"Error in reCAPTCHA v3 bypass attempt: {e}")
            return False
    
    def _solve_image_captcha(self, driver, img_element) -> bool:
        """Attempt to handle image CAPTCHA without API."""
        logger.warning("Cannot solve image CAPTCHA without API key - attempting bypass")
        
        try:
            # Try to find the input field
            input_fields = driver.find_elements(By.CSS_SELECTOR, "input[name*='captcha'], input[id*='captcha']")
            if not input_fields:
                return False
                
            # Try some common CAPTCHA answers as a desperate measure
            common_answers = ["captcha", "human", "person", "robot", "12345", "abcde"]
            input_field = input_fields[0]
            
            for answer in common_answers:
                input_field.clear()
                input_field.send_keys(answer)
                
                # Try to submit
                submit_buttons = driver.find_elements(By.XPATH, "//button[@type='submit'] | //input[@type='submit']")
                if submit_buttons:
                    submit_buttons[0].click()
                    time.sleep(2)
                    
                    # Check if CAPTCHA is still present
                    if not self._detect_captcha(driver):
                        return True
            
            # If all fails, try to refresh
            driver.refresh()
            time.sleep(3)
            
            return not self._detect_captcha(driver)
            
        except Exception as e:
            logger.error(f"Error in image CAPTCHA bypass attempt: {e}")
            return False
    
    def _extract_contact_info(self, text: str) -> Dict[str, Set[str]]:
        """
        Extract contact information from text.
        
        Args:
            text: Text to extract contact information from
            
        Returns:
            Dict with 'emails' and 'phones' fields containing sets of extracted contacts
        """
        results = {'emails': set(), 'phones': set()}
        
        # Extract standard emails
        emails = re.findall(self.email_pattern, text)
        
        # Extract emails from HTML attributes (like mailto: links)
        attr_emails = re.findall(self.email_attr_pattern, text)
        emails.extend(attr_emails)
        
        # Extract obfuscated emails (like "name at domain dot com")
        obfuscated_matches = re.findall(self.obfuscated_email_pattern, text)
        for match in obfuscated_matches:
            if len(match) == 3:  # name, domain, tld
                reconstructed_email = f"{match[0]}@{match[1]}.{match[2]}"
                emails.append(reconstructed_email)
        
        # Extract emails from JavaScript and JSON
        script_emails = self._extract_emails_from_scripts(text)
        emails.extend(script_emails)
        
        # Look for contact forms with hidden email fields
        hidden_email_pattern = r'<input[^>]*type=[\'"]hidden[\'"][^>]*name=[\'"](?:email|recipient)[\'"][^>]*value=[\'"]([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})[\'"]'
        hidden_emails = re.findall(hidden_email_pattern, text)
        emails.extend(hidden_emails)
        
        # Look for email addresses in meta tags
        meta_pattern = r'<meta[^>]*content=[\'"][^\'"]*([\w._%+\-]+@[\w.\-]+\.[a-zA-Z]{2,})[^\'""]*[\'"]'
        meta_emails = re.findall(meta_pattern, text)
        emails.extend(meta_emails)
        
        # Look for emails in comments
        comment_pattern = r'<!--.*?([\w._%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}).*?-->'
        comment_emails = re.findall(comment_pattern, text, re.DOTALL)
        emails.extend(comment_emails)
        
        # Look for contact information sections
        contact_section_pattern = r'<(?:div|section|article)[^>]*(?:id|class)=[\'"][^\'"]*contact[^\'"]*[\'"][^>]*>(.+?)</(?:div|section|article)>'
        contact_sections = re.findall(contact_section_pattern, text, re.DOTALL | re.IGNORECASE)
        
        for section in contact_sections:
            # Look for emails in contact sections
            section_emails = re.findall(self.email_pattern, section)
            emails.extend(section_emails)
        
        # Validate and filter emails
        validated_emails = set()
        for email in emails:
            if self._validate_email(email):
                validated_emails.add(email.lower())
                # Update counter
                self.results['counters']['emails_found'] += 1
        
        results['emails'] = validated_emails
        
        # Extract phones using multiple patterns
        phones = set()
        for pattern in self.phone_patterns:
            phone_matches = re.findall(pattern, text)
            for phone in phone_matches:
                # For Indian patterns, use specific validation
                if pattern in [self.phone_patterns[0], self.phone_patterns[1]]:  # Indian patterns
                    if self._validate_indian_phone(phone):
                        normalized_phone = self._normalize_phone(phone)
                        if normalized_phone:
                            phones.add(normalized_phone)
                # For other patterns, use general validation
                elif self._validate_phone(phone):
                    normalized_phone = self._normalize_phone(phone)
                    if normalized_phone:
                        phones.add(normalized_phone)
        
        # Look for phones in contact sections specifically
        for section in contact_sections:
            for pattern in self.phone_patterns:
                section_phones = re.findall(pattern, section)
                for phone in section_phones:
                    # For Indian patterns, use specific validation
                    if pattern in [self.phone_patterns[0], self.phone_patterns[1]]:  # Indian patterns
                        if self._validate_indian_phone(phone):
                            normalized_phone = self._normalize_phone(phone)
                            if normalized_phone:
                                phones.add(normalized_phone)
                    # For other patterns, use general validation
                    elif self._validate_phone(phone):
                        normalized_phone = self._normalize_phone(phone)
                        if normalized_phone:
                            phones.add(normalized_phone)
        
        # Final filtering for Indian numbers
        if phones:
            filtered_phones = set()
            for phone in phones:
                # Check if it's an Indian number
                if phone.startswith('+91'):
                    # Apply strict Indian validation
                    if self._validate_indian_phone(phone):
                        filtered_phones.add(phone)
                        self.results['counters']['phones_found'] += 1
                else:
                    # Keep non-Indian numbers
                    filtered_phones.add(phone)
                    self.results['counters']['phones_found'] += 1
            
            results['phones'] = filtered_phones
        
        return results
    
    def _validate_email(self, email: str) -> bool:
        """
        Validate an email address with enhanced checks.
        
        Args:
            email: Email address to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not email or '@' not in email:
            return False
        
        email = email.lower().strip()
        
        # Basic format validation
        if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', email):
            return False
        
        # Check for disposable email domains
        domain = email.split('@')[1]
        if any(disposable in domain for disposable in self.DISPOSABLE_EMAIL_DOMAINS):
            return False
        
        # Check for spam TLDs
        tld = domain.split('.')[-1].lower()
        if tld in self.SPAM_TLDS:
            return False
        
        # Check for common non-business domains (typically personal emails)
        common_personal_domains = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'aol.com',
            'icloud.com', 'mail.com', 'protonmail.com', 'zoho.com'
        ]
        
        # Only exclude personal domains if they don't contain business identifiers
        if domain in common_personal_domains:
            username = email.split('@')[0]
            business_identifiers = ['contact', 'info', 'sales', 'support', 'admin', 'hr', 
                                   'marketing', 'help', 'service', 'inquiry', 'business',
                                   'office', 'mail', 'team', 'careers']
            
            # If it's a personal domain but has a business username, it might be valid
            if not any(identifier in username for identifier in business_identifiers):
                # Lower confidence in personal emails, but don't exclude completely
                pass
        
        # Check for very short usernames (likely to be invalid)
        username = email.split('@')[0]
        if len(username) <= 2:
            return False
        
        # Check for excessive special characters (likely to be invalid)
        special_chars = sum(1 for c in username if c in '._-%+')
        if special_chars > len(username) / 2:
            return False
            
        return True
    
    def _validate_phone(self, phone: str) -> bool:
        """
        Validate a phone number with enhanced checks.
        
        Args:
            phone: Phone number to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not phone:
            return False
        
        # Extract digits only
        digits = re.sub(r'\D', '', phone)
        
        # Check length - too short or too long is invalid
        if len(digits) < 7 or len(digits) > 15:
            return False
        
        # For Indian numbers, enforce the 6-9 starting digit rule for mobile numbers
        if digits.startswith('91') and len(digits) >= 12:
            # Check if the number after country code starts with 6-9
            if digits[2] not in '6789':
                return False
        elif len(digits) == 10 and digits[0] not in '6789':
            # For 10-digit numbers that might be Indian, check first digit
            return False
            
        # Reject numbers with too many repeating digits (likely fake)
        for digit in '0123456789':
            if digit * 4 in digits:  # 4 or more of the same digit in a row
                return False
                
        # Reject numbers with sequential digits (likely fake)
        sequences = ['0123456', '1234567', '2345678', '3456789', '9876543', '8765432', '7654321', '6543210']
        for seq in sequences:
            if seq in digits:
                return False
                
        return True
    
    def _normalize_phone(self, phone: str) -> Optional[str]:
        """
        Normalize a phone number to E.164 format if possible.
        Enhanced to handle Indian numbers correctly.
        
        Args:
            phone: Phone number to normalize
            
        Returns:
            str: Normalized phone number or None if invalid
        """
        if not phone:
            return None
        
        # Extract digits only
        digits = re.sub(r'\D', '', phone)
        
        # Remove leading zeros
        digits = digits.lstrip('0')
        
        # If it's an Indian number
        if digits.startswith('91') and len(digits) >= 12:
            # Ensure it starts with valid Indian mobile prefix (6-9)
            if digits[2] in '6789':
                return f"+{digits[:2]} {digits[2:7]} {digits[7:12]}"
            return None
        elif len(digits) == 10 and digits[0] in '6789':
            # Likely an Indian mobile without country code
            return f"+91 {digits[:5]} {digits[5:]}"
        # If it's an international format (starts with country code)
        elif digits.startswith('1') and len(digits) == 11:  # US/Canada
            return f"+{digits[0]} ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
        elif digits.startswith('44') and len(digits) >= 10:  # UK
            return f"+{digits[:2]} {digits[2:6]} {digits[6:11]}"
        elif len(digits) == 10:
            # For 10-digit numbers, check the first digit
            if digits[0] in '6789':
                # Format as Indian number if it starts with 6-9
                return f"+91 {digits[:5]} {digits[5:]}"
            elif digits[0] in '23':  # Some countries use these prefixes
                # Format as generic international
                return f"+{digits}"
            else:
                # Don't format numbers with invalid prefixes
                return None
        else:
            # Just return with + prefix if it's reasonable length
            if 8 <= len(digits) <= 15:
                return f"+{digits}"
            return digits
    
    def _score_url(self, url: str) -> int:
        """
        Score a URL based on relevance to contact information.
        
        Args:
            url: URL to score
            
        Returns:
            int: Score (higher is more relevant)
        """
        url_lower = url.lower()
        score = 0
        
        # Check for contact-related keywords in URL
        for keyword in self.CONTACT_KEYWORDS:
            if keyword in url_lower:
                score += 5
        
        # Check for blocked domains
        for domain in self.BLOCKED_DOMAINS:
            if domain in url_lower:
                return -100  # Very negative score to avoid processing
        
        # Prioritize shorter URLs (often more important pages)
        parts = url.split('/')
        score -= len(parts) * 0.5
        
        # Prioritize URLs with fewer query parameters
        if '?' in url:
            query_params = url.split('?')[1].split('&')
            score -= len(query_params) * 0.5
        
        return score
    
    def _normalize_url(self, base_url: str, url: str) -> Optional[str]:
        """
        Normalize a URL relative to the base URL.
        
        Args:
            base_url: Base URL for relative URL resolution
            url: URL to normalize
            
        Returns:
            str: Normalized URL or None if invalid
        """
        try:
            if not url:
                return None
            
            # Clean the URL
            url = url.strip()
            
            # Remove anchors
            if '#' in url:
                url = url.split('#')[0]
            
            # Handle javascript links
            if url.startswith('javascript:'):
                return None
            
            # Handle mailto links
            if url.startswith('mailto:'):
                # Extract email from mailto
                email_match = re.search(r'mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', url)
                if email_match:
                    email = email_match.group(1)
                    if self._validate_email(email):
                        self.results['emails'].add(email.lower())
                return None
            
            # Handle tel links
            if url.startswith('tel:'):
                # Extract phone from tel
                phone_match = re.search(r'tel:([\+\d\s\-\(\)]+)', url)
                if phone_match:
                    phone = phone_match.group(1)
                    if self._validate_phone(phone):
                        normalized = self._normalize_phone(phone)
                        if normalized:
                            self.results['phones'].add(normalized)
                return None
            
            # Convert relative URL to absolute
            absolute_url = urllib.parse.urljoin(base_url, url)
            
            # Ensure same domain as base URL
            base_domain = urllib.parse.urlparse(base_url).netloc
            url_domain = urllib.parse.urlparse(absolute_url).netloc
            
            if not url_domain:
                return None
            
            # Check if the domain matches the base domain or is a subdomain
            if not (url_domain == base_domain or url_domain.endswith('.' + base_domain)):
                return None
            
            return absolute_url
        
        except Exception as e:
            logger.error(f"Error normalizing URL {url}: {e}")
            return None
    
    def _find_links(self, soup: BeautifulSoup, base_url: str) -> List[Tuple[str, int]]:
        """
        Find and score links in a page.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for relative URL resolution
            
        Returns:
            List of (url, score) tuples, sorted by score in descending order
        """
        links = []
        
        # Find all anchor tags
        for a_tag in soup.find_all('a', href=True):
            url = a_tag.get('href', '')
            
            # Skip empty URLs
            if not url:
                continue
            
            # Normalize URL
            normalized_url = self._normalize_url(base_url, url)
            if not normalized_url:
                continue
            
            # Score URL
            score = self._score_url(normalized_url)
            
            # Skip URLs with negative score
            if score < 0:
                continue
            
            # Add to list of links
            links.append((normalized_url, score))
        
        # Sort by score in descending order
        links.sort(key=lambda x: x[1], reverse=True)
        
        return links
    
    def _random_delay(self):
        """Implement a random delay between requests to avoid detection."""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)
    
    def _simulate_human_behavior(self, driver):
        """Simulate human-like behavior in the browser to avoid detection."""
        try:
            # Scroll behavior
            scroll_amount = random.randint(1, 5)
            for _ in range(scroll_amount):
                driver.execute_script(f"window.scrollBy(0, {random.randint(300, 700)});")
                time.sleep(random.uniform(0.5, 2.0))
            
            # Random mouse movements using CDP
            driver.execute_cdp_cmd("Input.dispatchMouseEvent", {
                "type": "mouseMoved",
                "x": random.randint(100, 700),
                "y": random.randint(100, 500),
            })
            
            # Random pauses
            time.sleep(random.uniform(1.0, 3.0))
            
            # Click on random non-link element occasionally
            if random.random() < 0.3:
                try:
                    elements = driver.find_elements(By.TAG_NAME, "div")
                    if elements:
                        random_element = random.choice(elements[:10])  # Pick from first 10 to avoid clicking offscreen
                        random_element.click()
                except Exception:
                    pass
            
            # Wait a bit more
            time.sleep(random.uniform(0.5, 1.5))
            
        except Exception as e:
            logger.debug(f"Error in simulate_human_behavior: {e}")
    
    def _requests_fetch(self, url: str) -> Optional[str]:
        """
        Fetch a URL using requests library with proxy rotation and retries.
        
        Args:
            url: URL to fetch
            
        Returns:
            str: HTML content or None if failed
        """
        # Initialize retry strategy with exponential backoff
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD", "POST"],
            respect_retry_after_header=True
        )
        
        # Create connection adapters with the retry strategy
        http_adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=20,
            pool_maxsize=20,
            pool_block=False
        )
        
        # Apply adapters to session
        self.session.mount('http://', http_adapter)
        self.session.mount('https://', http_adapter)
        
        for attempt in range(self.max_retries):
            try:
                # Always use our reliable proxy
                proxy = self._get_next_proxy()
                
                # Update user agent to a reliable one
                user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                self.session.headers.update({'User-Agent': user_agent})
                
                # Log the request
                logger.debug(f"Fetching URL: {url} (attempt {attempt+1}/{self.max_retries})")
                
                # Add additional headers to appear more like a real browser
                headers = {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                    'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"',
                    'Sec-Ch-Ua-Mobile': '?0',
                    'Sec-Ch-Ua-Platform': '"Windows"',
                    'Sec-Fetch-Dest': 'document',
                    'Sec-Fetch-Mode': 'navigate',
                    'Sec-Fetch-Site': 'none',
                    'Sec-Fetch-User': '?1'
                }
                
                # Make the request with timeout
                response = self.session.get(
                    url, 
                    proxies=proxy, 
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                    verify=False  # Disable SSL verification to avoid some connection issues
                )
                
                # Check if response is successful
                if response.status_code == 200:
                    # Update counter
                    self.results['counters']['urls_processed'] += 1
                    
                    # Check content type
                    content_type = response.headers.get('Content-Type', '')
                    if 'text/html' not in content_type and 'application/xhtml+xml' not in content_type:
                        logger.debug(f"Skipping non-HTML content: {content_type} for {url}")
                        return None
                    
                    # Check for CAPTCHA indicators in content
                    if 'captcha' in response.text.lower():
                        logger.warning(f"CAPTCHA detected in requests mode for {url}")
                        self.results['counters']['captchas_encountered'] += 1
                        return None
                    
                    return response.text
                else:
                    logger.debug(f"Request failed with status code {response.status_code} for {url}")
            
            except requests.exceptions.ConnectionError as e:
                # Handle connection errors specifically
                logger.warning(f"Connection error on attempt {attempt+1}/{self.max_retries} for {url}: {e}")
                self.results['counters']['proxy_errors'] += 1
                
                if "Connection refused" in str(e) or "No connection could be made" in str(e):
                    logger.warning(f"Connection refused error. The target server may be down or blocking requests.")
                    
                    # Try with a different proxy on next attempt
                    if attempt < self.max_retries - 1:
                        delay = 2 ** attempt  # Exponential backoff
                        logger.info(f"Waiting {delay} seconds before retry with a different proxy...")
                        time.sleep(delay)
                
            except requests.exceptions.Timeout as e:
                # Handle timeout errors
                logger.warning(f"Timeout error on attempt {attempt+1}/{self.max_retries} for {url}: {e}")
                if attempt < self.max_retries - 1:
                    delay = 2 ** attempt  # Exponential backoff
                    logger.info(f"Waiting {delay} seconds before retry...")
                    time.sleep(delay)
            
            except requests.exceptions.RequestException as e:
                # Handle other request errors
                self.results['counters']['proxy_errors'] += 1
                logger.debug(f"Request error on attempt {attempt+1}/{self.max_retries} for {url}: {e}")
                if attempt < self.max_retries - 1:
                    delay = random.uniform(1, 3)
                    time.sleep(delay)
        
        # Update failed URLs counter
        self.results['counters']['urls_failed'] += 1
        logger.warning(f"All retries failed for {url}")
        return None
    
    def _selenium_fetch(self, url: str, proxy: Optional[Dict[str, str]] = None) -> Optional[Tuple[str, List[Tuple[str, int]]]]:
        """
        Fetch a URL using Selenium with stealth mode and proxy rotation.
        
        Args:
            url: URL to fetch
            proxy: Proxy configuration
            
        Returns:
            Tuple of (HTML content, list of links) or None if failed
        """
        driver = None
        try:
            # Initialize Selenium with a proxy
            driver = self._initialize_selenium(proxy)
            
            if not driver:
                logger.error("Failed to initialize Selenium")
                return None
            
            # Set page load timeout
            driver.set_page_load_timeout(self.timeout)
            
            # Load the URL
            driver.get(url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Check for CAPTCHA
            if self._detect_captcha(driver):
                logger.warning(f"CAPTCHA detected for {url}")
                
                # Try to solve CAPTCHA
                if not self._solve_captcha(driver):
                    logger.warning("Failed to solve CAPTCHA, skipping URL")
                    return None
                
                # Wait for page to load after solving CAPTCHA
                time.sleep(5)
            
            # Simulate human behavior
            self._simulate_human_behavior(driver)
            
            # Get the page source
            html_content = driver.page_source
            
            # Parse the page with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Find links
            links = self._find_links(soup, url)
            
            return html_content, links
        
        except TimeoutException:
            logger.warning(f"Timeout while loading {url}")
            return None
        
        except WebDriverException as e:
            logger.warning(f"WebDriver error for {url}: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Selenium fetch error for {url}: {e}")
            if self.debug:
                traceback.print_exc()
            return None
        
        finally:
            # Close the driver
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass
    
    def _get_contact_urls(self, domain: str) -> List[str]:
        """
        Generate contact page URLs for a domain.
        
        Args:
            domain: Domain to generate contact URLs for
            
        Returns:
            List of potential contact page URLs
        """
        urls = []
        
        # Main domain URL
        main_url = f"https://{domain}"
        urls.append(main_url)
        
        # Common contact page paths
        contact_paths = [
            "/contact", "/contact-us", "/contactus", "/get-in-touch", "/about",
            "/about-us", "/aboutus", "/support", "/help", "/team", "/company/contact"
        ]
        
        for path in contact_paths:
            urls.append(f"https://{domain}{path}")
            urls.append(f"https://{domain}{path}.html")
            urls.append(f"https://{domain}{path}.php")
        
        return urls
    
    def scrape_by_domain(self, domain: str, max_depth: int = 2) -> Dict[str, List[str]]:
        """
        Scrape contact information from a domain.
        
        Args:
            domain: Domain to scrape
            max_depth: Maximum crawl depth
            
        Returns:
            Dict with 'emails' and 'phones' fields containing lists of contacts
        """
        # Reset results
        self.results = {
            'emails': set(),
            'phones': set(),
            'processed_urls': set(),
            'failed_urls': set(),
            'counters': {
                'emails_found': 0,
                'phones_found': 0,
                'urls_processed': 0,
                'urls_failed': 0,
                'captchas_encountered': 0,
                'captchas_solved': 0,
                'proxy_errors': 0
            }
        }
        
        # Generate potential contact URLs
        contact_urls = self._get_contact_urls(domain)
        
        # Try with different proxies if needed
        successful_urls = 0
        failed_urls = 0
        
        # Add error handling for the entire process
        try:
            # Process each URL with a timeout to prevent hanging
            with ThreadPoolExecutor(max_workers=min(self.max_concurrent_threads, len(contact_urls))) as executor:
                futures = []
                for url in contact_urls:
                    futures.append(executor.submit(self._process_url_with_retry, url, 0, max_depth))
                
                # Wait for all tasks to complete with timeout
                for future in futures:
                    try:
                        # Get the result (will re-raise any exception from the thread)
                        # Add a timeout to prevent hanging
                        result = future.result(timeout=60)
                        if result:
                            successful_urls += 1
                        else:
                            failed_urls += 1
                    except TimeoutError:
                        logger.error(f"Timeout processing URL for domain {domain}")
                        failed_urls += 1
                    except Exception as e:
                        logger.error(f"Error in URL processing thread: {e}")
                        failed_urls += 1
        
        except Exception as e:
            logger.error(f"Error during domain scraping for {domain}: {e}")
            if self.debug:
                traceback.print_exc()
        
        logger.info(f"Completed scraping {domain}: {successful_urls} successful URLs, {failed_urls} failed")
        
        # Format results
        return {
            'emails': list(self.results['emails']),
            'phones': list(self.results['phones'])
        }
    
    def _process_url_with_retry(self, url: str, depth: int = 0, max_depth: int = 2) -> bool:
        """
        Process a URL with retry logic for proxy failures.
        
        Args:
            url: URL to process
            depth: Current depth level
            max_depth: Maximum crawl depth
            
        Returns:
            bool: True if processing was successful, False otherwise
        """
        # Skip if URL already processed
        if url in self.results['processed_urls'] or url in self.results['failed_urls']:
            return True
        
        # Try multiple proxies if needed
        max_proxy_attempts = min(3, len(self.proxies) or 1)
        for attempt in range(max_proxy_attempts):
            try:
                # Log the URL being processed
                if attempt == 0:
                    logger.debug(f"Processing URL: {url} (depth {depth})")
                else:
                    logger.debug(f"Retrying URL: {url} (attempt {attempt+1}/{max_proxy_attempts})")
                
                # Add URL to processed list
                self.results['processed_urls'].add(url)
                self.results['counters']['urls_processed'] += 1
                
                # First try with simple requests
                html_content = self._requests_fetch(url)
                
                if html_content:
                    # Parse with BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Extract contact information from page content
                    contacts = self._extract_contact_info(html_content)
                    self.results['emails'].update(contacts['emails'])
                    self.results['phones'].update(contacts['phones'])
                    
                    # Find links for further crawling
                    links = self._find_links(soup, url)
                    
                    # Stop if we've reached max depth
                    if depth >= max_depth:
                        return True
                    
                    # Process top-scored links
                    for link_url, score in links[:3]:  # Limit to top 3 links to prevent overloading
                        if link_url not in self.results['processed_urls'] and link_url not in self.results['failed_urls']:
                            # Process the URL recursively
                            self._process_url_with_retry(link_url, depth + 1, max_depth)
                    
                    # Random delay between requests
                    self._random_delay()
                    
                    return True
                
                else:
                    # Fall back to Selenium for more complex pages
                    # Get a fresh proxy for selenium
                    proxy = self._get_next_proxy()
                    
                    # Add retry logic for Selenium initialization
                    selenium_result = None
                    for selenium_attempt in range(2):  # Try 2 times
                        try:
                            selenium_result = self._selenium_fetch(url, proxy)
                            if selenium_result:
                                break
                        except Exception as e:
                            logger.debug(f"Selenium attempt {selenium_attempt+1} failed: {e}")
                            time.sleep(1)  # Short delay before retry
                    
                    if selenium_result:
                        html_content, links = selenium_result
                        
                        # Extract contact information from page content
                        contacts = self._extract_contact_info(html_content)
                        self.results['emails'].update(contacts['emails'])
                        self.results['phones'].update(contacts['phones'])
                        
                        # Stop if we've reached max depth
                        if depth >= max_depth:
                            return True
                        
                        # Process top-scored links
                        for link_url, score in links[:3]:  # Limit to top 3 links
                            if link_url not in self.results['processed_urls'] and link_url not in self.results['failed_urls']:
                                # Process the URL recursively
                                self._process_url_with_retry(link_url, depth + 1, max_depth)
                        
                        # Random delay between requests
                        self._random_delay()
                        
                        return True
                    
                    # If neither method worked, try with another proxy
                    if attempt < max_proxy_attempts - 1:
                        logger.debug(f"Failed with current proxy, trying another for {url}")
                        continue
            
            except Exception as e:
                logger.debug(f"Error processing URL (attempt {attempt+1}): {url}, {str(e)}")
                if attempt < max_proxy_attempts - 1:
                    logger.debug(f"Retrying with another proxy for {url}")
                    continue
        
        # Mark as failed after all attempts
        self.results['failed_urls'].add(url)
        self.results['counters']['urls_failed'] += 1
        logger.warning(f"Failed to process URL after {max_proxy_attempts} attempts: {url}")
        return False
    
    def search_and_scrape(self, keyword: str, max_results: int = 5, max_depth: int = 2) -> Dict[str, Any]:
        """
        Search for websites based on keyword and scrape contact information.
        
        Args:
            keyword: Keyword to search for
            max_results: Maximum number of domains to scrape
            max_depth: Maximum crawl depth per domain
            
        Returns:
            Dict with search results and contact information
        """
        # Reset results
        self.results = {
            'emails': set(),
            'phones': set(),
            'processed_urls': set(),
            'failed_urls': set(),
            'counters': {
                'emails_found': 0,
                'phones_found': 0,
                'urls_processed': 0,
                'urls_failed': 0,
                'captchas_encountered': 0,
                'captchas_solved': 0,
                'proxy_errors': 0
            }
        }
        
        # Use Selenium to perform a search
        query = f"{keyword} contact"
        
        driver = None
        domains = []
        
        # Define multiple search engines to try - order from least restrictive to most restrictive
        search_engines = [
            {
                "name": "DuckDuckGo",
                "url": f"https://duckduckgo.com/?q={urllib.parse.quote(query)}",
                "result_selector": "article",
                "link_selector": "a.result__a",
                "wait_time": 10
            },
            {
                "name": "Bing",
                "url": f"https://www.bing.com/search?q={urllib.parse.quote(query)}",
                "result_selector": "li.b_algo",
                "link_selector": "a",
                "wait_time": 10
            },
            {
                "name": "Google",
                "url": f"https://www.google.com/search?q={urllib.parse.quote(query)}",
                "result_selector": "div.g",
                "link_selector": "a",
                "wait_time": 15
            },
            # Alternative search engines
            {
                "name": "Yahoo",
                "url": f"https://search.yahoo.com/search?p={urllib.parse.quote(query)}",
                "result_selector": "div.algo",
                "link_selector": "a",
                "wait_time": 10
            },
            {
                "name": "Ecosia",
                "url": f"https://www.ecosia.org/search?q={urllib.parse.quote(query)}",
                "result_selector": "div.result",
                "link_selector": "a.result-url",
                "wait_time": 10
            }
        ]
        
        # Try multiple proxies if needed
        max_proxy_attempts = min(3, len(self.proxies) or 1)
        
        # Track which search engines have been tried
        tried_engines = set()
        
        # Keep trying search engines until we have enough domains or have tried all engines
        while len(domains) < max_results and len(tried_engines) < len(search_engines):
            # Select a search engine we haven't tried yet
            available_engines = [engine for engine in search_engines if engine["name"] not in tried_engines]
            if not available_engines:
                break
                
            search_engine = available_engines[0]
            tried_engines.add(search_engine["name"])
            
            logger.info(f"Trying search engine: {search_engine['name']}")
            
            for attempt in range(max_proxy_attempts):
                try:
                    # Get a new proxy for each attempt
                    proxy = self._get_next_proxy()
                    logger.info(f"Search attempt {attempt+1}/{max_proxy_attempts} with proxy on {search_engine['name']}")
                    
                    # Initialize Selenium with specific proxy
                    driver = self._initialize_selenium(proxy)
                    
                    if not driver:
                        logger.error(f"Failed to initialize Selenium for search (attempt {attempt+1})")
                        self.results['counters']['proxy_errors'] += 1
                        continue
                    
                    # Add a random delay before accessing the search engine to avoid detection
                    time.sleep(random.uniform(2.0, 5.0))
                    
                    # Load search page
                    search_url = search_engine["url"]
                    logger.debug(f"Loading search URL: {search_url}")
                    driver.get(search_url)
                    
                    # Add another delay after page load
                    time.sleep(random.uniform(3.0, 7.0))
                    
                    # Wait for results to load
                    try:
                        WebDriverWait(driver, search_engine["wait_time"]).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, search_engine["result_selector"]))
                        )
                    except TimeoutException:
                        logger.warning(f"Timeout waiting for search results on {search_engine['name']}")
                        if driver:
                            driver.quit()
                        driver = None
                        continue
                    
                    # Check for CAPTCHA
                    if self._detect_captcha(driver):
                        logger.warning(f"CAPTCHA detected during search on {search_engine['name']} (attempt {attempt+1})")
                        
                        # Try to bypass CAPTCHA
                        if not self._solve_captcha(driver):
                            logger.warning(f"Failed to bypass CAPTCHA on {search_engine['name']}, trying another proxy or search engine")
                            driver.quit()
                            driver = None
                            continue
                        
                        # Wait for results to load after solving CAPTCHA
                        try:
                            WebDriverWait(driver, search_engine["wait_time"]).until(
                                EC.presence_of_element_located((By.CSS_SELECTOR, search_engine["result_selector"]))
                            )
                        except TimeoutException:
                            logger.warning(f"Timeout waiting for search results after CAPTCHA on {search_engine['name']}")
                            if driver:
                                driver.quit()
                            driver = None
                            continue
                    
                    # Try to extract search results
                    try:
                        # Extract search results
                        results = driver.find_elements(By.CSS_SELECTOR, search_engine["result_selector"])
                        
                        if not results:
                            logger.warning(f"No search results found on {search_engine['name']} (attempt {attempt+1})")
                            if driver:
                                driver.quit()
                            driver = None
                            continue
                        
                        logger.info(f"Found {len(results)} search results on {search_engine['name']}")
                        
                        # Extract domains from search results
                        for result in results:
                            try:
                                # Try different strategies to find links
                                link_elements = result.find_elements(By.CSS_SELECTOR, search_engine["link_selector"])
                                
                                if not link_elements and search_engine["link_selector"] != "a":
                                    # Fallback to any anchor tag
                                    link_elements = result.find_elements(By.TAG_NAME, "a")
                                
                                for link_element in link_elements:
                                    href = link_element.get_attribute("href")
                                    
                                    if href and "http" in href:
                                        parsed_url = urllib.parse.urlparse(href)
                                        domain = parsed_url.netloc
                                        
                                        # Skip if domain is empty or contains blocked domain
                                        if not domain or any(blocked in domain for blocked in self.BLOCKED_DOMAINS):
                                            continue
                                        
                                        # Skip common non-business domains
                                        if any(common in domain for common in ['wikipedia.org', 'youtube.com', 'amazon.com', 'facebook.com']):
                                            continue
                                        
                                        # Add domain if not already added
                                        if domain not in domains:
                                            domains.append(domain)
                            except Exception as e:
                                logger.debug(f"Error extracting domain from search result: {e}")
                        
                        # If we have enough domains, we succeeded
                        if len(domains) >= max_results:
                            logger.info(f"Found {len(domains)} domains on {search_engine['name']}, which is enough")
                            break
                            
                    except Exception as e:
                        logger.error(f"Error extracting search results from {search_engine['name']}: {e}")
                    
                except Exception as e:
                    logger.error(f"Error during search on {search_engine['name']} (attempt {attempt+1}): {e}")
                    self.results['counters']['proxy_errors'] += 1
                    if self.debug:
                        traceback.print_exc()
                
                finally:
                    # Close the driver
                    if driver:
                        try:
                            driver.quit()
                        except Exception:
                            pass
                        driver = None
            
            # If we have enough domains from this search engine, break the loop
            if len(domains) >= max_results:
                logger.info(f"Successfully found enough domains ({len(domains)}) using {search_engine['name']}")
                break
            else:
                logger.info(f"Moving to next search engine after finding {len(domains)} domains on {search_engine['name']}")
        
        # Limit number of domains
        domains = domains[:max_results]
        
        if not domains:
            return {'error': 'No domains found after trying all search engines'}
        
        # Scrape each domain
        domain_results = {}
        
        for domain in domains:
            # Scrape domain
            logger.info(f"Scraping domain: {domain}")
            try:
                domain_contacts = self.scrape_by_domain(domain, max_depth)
                # Add to results
                domain_results[domain] = domain_contacts
            except Exception as e:
                logger.error(f"Error scraping domain {domain}: {e}")
                domain_results[domain] = {'emails': [], 'phones': []}
        
        # Combine all results
        all_emails = set()
        all_phones = set()
        
        for domain, contacts in domain_results.items():
            all_emails.update(contacts['emails'])
            all_phones.update(contacts['phones'])
        
        # Return results
        return {
            'query': keyword,
            'domains': domains,
            'domain_results': domain_results,
            'emails': list(all_emails),
            'phones': list(all_phones),
            'timestamp': datetime.now().isoformat(),
            'stats': {
                'emails_found': self.results['counters']['emails_found'],
                'phones_found': self.results['counters']['phones_found'],
                'urls_processed': self.results['counters']['urls_processed'],
                'urls_failed': self.results['counters']['urls_failed'],
                'captchas_encountered': self.results['counters']['captchas_encountered'],
                'captchas_solved': self.results['counters']['captchas_solved'],
                'proxy_errors': self.results['counters']['proxy_errors']
            }
        }
    
    def save_results(self, results: Dict[str, Any], filename: Optional[str] = None) -> str:
        """
        Save results to a JSON file.
        
        Args:
            results: Results to save
            filename: Filename to save to (optional)
            
        Returns:
            str: Path to saved file
        """
        if not filename:
            # Generate filename based on query and timestamp
            query = results.get('query', 'search').replace(' ', '_')
            timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
            filename = f"contact_results_{query}_{timestamp}.json"
        
        # Convert sets to lists for JSON serialization
        serializable_results = {}
        
        for key, value in results.items():
            if isinstance(value, set):
                serializable_results[key] = list(value)
            elif isinstance(value, dict):
                serializable_results[key] = {
                    k: list(v) if isinstance(v, set) else v
                    for k, v in value.items()
                }
            else:
                serializable_results[key] = value
        
        # Save to file
        path = os.path.join(self.cache_dir or '.', filename)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(serializable_results, f, indent=2)
        
        return path
    
    def _extract_emails_from_scripts(self, html_content: str) -> Set[str]:
        """
        Extract emails from JavaScript and JSON in web pages.
        
        Args:
            html_content: HTML content to extract emails from
            
        Returns:
            Set of extracted emails
        """
        emails = set()
        
        # Find all script tags
        script_pattern = r'<script[^>]*>(.*?)</script>'
        scripts = re.findall(script_pattern, html_content, re.DOTALL)
        
        # Patterns to find emails in JavaScript
        js_patterns = [
            # Variable assignments
            r'var\s+[a-zA-Z_]\w*\s*=\s*[\'"]([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})[\'"]',
            # Object properties
            r'[\'"]e?mail[\'"]:\s*[\'"]([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})[\'"]',
            # Contact info objects
            r'contact\w*[\'"]?\s*:\s*{[^}]*[\'"]e?mail[\'"]?\s*:\s*[\'"]([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})[\'"]',
            # Array items
            r'[\'"]emails?[\'"]\s*:\s*\[\s*[\'"]([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})[\'"]',
            # Email protection scripts
            r'data-cfemail=[\'"]([a-f0-9]+)[\'"]',  # Cloudflare email protection
            # Obfuscated emails
            r'(?:[\'"]\s*\+\s*[\'"]\s*)?([a-zA-Z0-9._%+\-]+)\s*[\'"]\s*\+\s*[\'"]\s*@\s*[\'"]\s*\+\s*[\'"]\s*([a-zA-Z0-9.\-]+)\s*[\'"]\s*\+\s*[\'"]\s*\.\s*[\'"]\s*\+\s*[\'"]\s*([a-zA-Z]{2,})'
        ]
        
        # Process each script
        for script in scripts:
            for pattern in js_patterns:
                matches = re.findall(pattern, script)
                for match in matches:
                    if isinstance(match, tuple):
                        # Handle tuple results from regex groups
                        if len(match) == 3:  # Obfuscated email parts
                            email = f"{match[0]}@{match[1]}.{match[2]}"
                            if self._validate_email(email):
                                emails.add(email.lower())
                    elif pattern == r'data-cfemail=[\'"]([a-f0-9]+)[\'"]':
                        # Decode Cloudflare protected email
                        try:
                            decoded = self._decode_cloudflare_email(match)
                            if decoded and self._validate_email(decoded):
                                emails.add(decoded.lower())
                        except:
                            pass
                    else:
                        # Regular email match
                        if self._validate_email(match):
                            emails.add(match.lower())
        
        # Look for emails in JSON-LD structured data
        json_ld_pattern = r'<script[^>]*type=[\'"]application/ld\+json[\'"][^>]*>(.*?)</script>'
        json_ld_blocks = re.findall(json_ld_pattern, html_content, re.DOTALL)
        
        for json_block in json_ld_blocks:
            try:
                # Try to parse as JSON
                data = json.loads(json_block)
                # Extract emails from JSON
                self._extract_emails_from_json(data, emails)
            except:
                # If JSON parsing fails, try regex
                email_matches = re.findall(r'[\'"]email[\'"]\s*:\s*[\'"]([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})[\'"]', json_block)
                for email in email_matches:
                    if self._validate_email(email):
                        emails.add(email.lower())
        
        return emails
    
    def _extract_emails_from_json(self, data, emails_set):
        """
        Recursively extract emails from JSON data.
        
        Args:
            data: JSON data to extract emails from
            emails_set: Set to add found emails to
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(key, str) and key.lower() in ['email', 'mail', 'e-mail', 'emailaddress']:
                    if isinstance(value, str) and '@' in value:
                        if self._validate_email(value):
                            emails_set.add(value.lower())
                elif isinstance(value, (dict, list)):
                    self._extract_emails_from_json(value, emails_set)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._extract_emails_from_json(item, emails_set)
                elif isinstance(item, str) and '@' in item:
                    if self._validate_email(item):
                        emails_set.add(item.lower())
    
    def _decode_cloudflare_email(self, encoded):
        """
        Decode a Cloudflare-protected email.
        
        Args:
            encoded: Hex-encoded email
            
        Returns:
            Decoded email string
        """
        try:
            hex_encoded = encoded
            key = int(hex_encoded[0:2], 16)
            decoded = ''
            
            for i in range(2, len(hex_encoded), 2):
                hex_char = hex_encoded[i:i+2]
                int_char = int(hex_char, 16) ^ key
                decoded += chr(int_char)
                
            return decoded
        except:
            return None

class EnhancedContactScraper(AdvancedWebScraper):
    """Enhanced scraper specifically for contact information extraction."""
    
    def __init__(self, **kwargs):
        """Initialize the enhanced contact scraper with default settings."""
        # Set defaults appropriate for contact scraping
        kwargs['headless'] = True  # Always force headless mode
        if 'max_concurrent_threads' not in kwargs:
            kwargs['max_concurrent_threads'] = 3
        if 'timeout' not in kwargs:
            kwargs['timeout'] = 20
        
        # Initialize with multiple search engines
        self.search_engines_to_try = [
            "DuckDuckGo",  # Less likely to show CAPTCHAs
            "Bing",        # Moderate CAPTCHA frequency
            "Yahoo",       # Alternative option
            "Ecosia",      # Alternative option
            "Google"       # Most restrictive, try last
        ]
        
        super().__init__(**kwargs)
        self.browsers = []  # Track browser instances for cleanup
    
    def _initialize_selenium(self, proxy: Optional[Dict[str, str]] = None) -> Optional[webdriver.Chrome]:
        """Initialize a Selenium WebDriver with stealth and anti-detection capabilities."""
        try:
            # Call parent method to initialize browser
            driver = super()._initialize_selenium(proxy)
            
            # Track this browser for cleanup
            if driver:
                self.browsers.append(driver)
            
            return driver
        except Exception as e:
            logger.error(f"Error in EnhancedContactScraper._initialize_selenium: {e}")
            return None
    
    def _selenium_fetch(self, url: str, proxy: Optional[Dict[str, str]] = None) -> Optional[Tuple[str, List[Tuple[str, int]]]]:
        """Enhanced selenium fetch that tracks browser instances."""
        try:
            # Get result from parent method
            result = super()._selenium_fetch(url, proxy)
            return result
        except Exception as e:
            logger.error(f"Error in EnhancedContactScraper._selenium_fetch: {e}")
            return None
    
    def search_and_extract(self, target: str, country: str = 'IN', max_results: int = 30, 
                          exact_count: bool = False, max_pages: int = 5) -> Dict[str, Any]:
        """
        Optimized search for a keyword and extract contact information.
        
        Args:
            target: Search keyword or domain
            country: Country code for phone number validation
            max_results: Maximum number of results to return
            exact_count: Whether to try to get exactly max_results
            max_pages: Maximum number of search result pages to process
            
        Returns:
            Dictionary containing 'emails' and 'phones' lists
        """
        try:
            logger.info(f"Starting optimized search for '{target}', country: {country}")
            
            # Reset counters
            self.results = {
                'emails': set(),
                'phones': set(),
                'processed_urls': set(),
                'failed_urls': set(),
                'counters': {
                    'emails_found': 0,
                    'phones_found': 0,
                    'urls_processed': 0,
                    'urls_failed': 0,
                    'captchas_encountered': 0,
                    'captchas_solved': 0,
                    'proxy_errors': 0
                }
            }
            
            # Track start time for performance monitoring
            start_time = time.time()
            
            # Determine if input is a domain or search term
            is_domain = '.' in target and ' ' not in target and not target.startswith('http')
            
            # Results containers
            emails = set()
            phones = set()
            
            # Set a shorter timeout for faster results
            original_timeout = self.timeout
            self.timeout = min(15, self.timeout)  # Use at most 15 seconds timeout
            
            try:
                if is_domain:
                    # Direct domain scraping - faster approach
                    logger.info(f"Direct scraping of domain: {target}")
                    
                    # Generate contact URLs
                    contact_urls = self._get_contact_urls(target)
                    
                    # Process most promising URLs first (contact pages)
                    contact_urls.sort(key=lambda url: sum(1 for kw in self.CONTACT_KEYWORDS if kw in url.lower()), reverse=True)
                    
                    # Process URLs concurrently for speed
                    with ThreadPoolExecutor(max_workers=3) as executor:
                        futures = []
                        for url in contact_urls[:5]:  # Try top 5 URLs
                            futures.append(executor.submit(self._process_single_url, url))
                        
                        # Collect results
                        for future in futures:
                            try:
                                result = future.result(timeout=20)
                                if result:
                                    emails_found, phones_found = result
                                    emails.update(emails_found)
                                    phones.update(phones_found)
                            except Exception as e:
                                logger.debug(f"Error in concurrent URL processing: {e}")
                else:
                    # Search term - use search engines
                    logger.info(f"Searching for term: {target}")
                    
                    # Prioritize Google for faster results if possible
                    engine_order = ["Google", "Bing", "DuckDuckGo", "Yahoo"]
                    
                    # Try each search engine in order
                    for engine_name in engine_order:
                        # Skip if we already have enough results
                        if len(emails) >= max_results and len(phones) >= max_results:
                            break
                            
                        # Find the search engine config
                        engine = None
                        if engine_name == "Google":
                            engine = {
                                "name": "Google",
                                "url": f"https://www.google.com/search?q={urllib.parse.quote(target)}+contact+email+phone+{country}",
                                "result_selector": "div.g",
                                "link_selector": "a",
                                "wait_time": 10
                            }
                        elif engine_name == "Bing":
                            engine = {
                                "name": "Bing",
                                "url": f"https://www.bing.com/search?q={urllib.parse.quote(target)}+contact+email+phone+{country}",
                                "result_selector": "li.b_algo",
                                "link_selector": "a",
                                "wait_time": 8
                            }
                        elif engine_name == "DuckDuckGo":
                            engine = {
                                "name": "DuckDuckGo",
                                "url": f"https://duckduckgo.com/?q={urllib.parse.quote(target)}+contact+email+phone+{country}",
                                "result_selector": "article",
                                "link_selector": "a.result__a",
                                "wait_time": 8
                            }
                        elif engine_name == "Yahoo":
                            engine = {
                                "name": "Yahoo",
                                "url": f"https://search.yahoo.com/search?p={urllib.parse.quote(target)}+contact+email+phone+{country}",
                                "result_selector": "div.algo",
                                "link_selector": "a",
                                "wait_time": 8
                            }
                        
                        if not engine:
                            continue
                            
                        logger.info(f"Trying search engine: {engine['name']}")
                        
                        # Initialize driver with our reliable proxy
                        driver = self._initialize_selenium(self._get_next_proxy())
                        if not driver:
                            self.results['counters']['proxy_errors'] += 1
                            continue
                            
                        try:
                            # Load search page with delay to avoid detection
                            driver.get(engine["url"])
                            time.sleep(random.uniform(1.0, 2.0))  # Shorter delay for speed
                            
                            # Wait for results
                            try:
                                WebDriverWait(driver, engine["wait_time"]).until(
                                    EC.presence_of_element_located((By.CSS_SELECTOR, engine["result_selector"]))
                                )
                            except TimeoutException:
                                logger.warning(f"Timeout waiting for search results on {engine['name']}")
                                driver.quit()
                                self.results['counters']['urls_failed'] += 1
                                continue
                                
                            # Check for CAPTCHA
                            if self._detect_captcha(driver):
                                if not self._solve_captcha(driver):
                                    logger.warning(f"Failed to bypass CAPTCHA on {engine['name']}")
                                    driver.quit()
                                    continue
                                    
                                # Wait for results again after CAPTCHA
                                try:
                                    WebDriverWait(driver, engine["wait_time"]).until(
                                        EC.presence_of_element_located((By.CSS_SELECTOR, engine["result_selector"]))
                                    )
                                except TimeoutException:
                                    driver.quit()
                                    self.results['counters']['urls_failed'] += 1
                                    continue
                            
                            # Extract domains from search results
                            domains = []
                            results = driver.find_elements(By.CSS_SELECTOR, engine["result_selector"])
                            
                            for result in results[:max_pages]:  # Limit to max_pages results
                                try:
                                    link_elements = result.find_elements(By.CSS_SELECTOR, engine["link_selector"])
                                    if not link_elements and engine["link_selector"] != "a":
                                        link_elements = result.find_elements(By.TAG_NAME, "a")
                                        
                                    for link_element in link_elements:
                                        href = link_element.get_attribute("href")
                                        if href and "http" in href:
                                            parsed_url = urllib.parse.urlparse(href)
                                            domain = parsed_url.netloc
                                            
                                            # Skip if domain is empty or blocked
                                            if not domain or any(blocked in domain for blocked in self.BLOCKED_DOMAINS):
                                                continue
                                                
                                            # Skip common non-business domains
                                            if any(common in domain for common in ['wikipedia.org', 'youtube.com', 'amazon.com', 'facebook.com']):
                                                continue
                                                
                                            # Add domain if not already added
                                            if domain not in domains:
                                                domains.append(domain)
                                except Exception:
                                    continue
                            
                            driver.quit()
                            
                            # Process domains concurrently for speed
                            with ThreadPoolExecutor(max_workers=5) as executor:
                                futures = []
                                for domain in domains[:8]:  # Process up to 8 domains concurrently
                                    # Generate contact URLs for this domain
                                    contact_urls = self._get_contact_urls(domain)[:2]  # Just try top 2 URLs per domain
                                    for url in contact_urls:
                                        futures.append(executor.submit(self._process_single_url, url))
                                
                                # Collect results with timeout
                                for future in futures:
                                    try:
                                        result = future.result(timeout=15)
                                        if result:
                                            emails_found, phones_found = result
                                            emails.update(emails_found)
                                            phones.update(phones_found)
                                            
                                            # Break early if we have enough results
                                            if len(emails) >= max_results and len(phones) >= max_results:
                                                break
                                    except Exception as e:
                                        logger.debug(f"Error in concurrent domain processing: {e}")
                                        
                        except Exception as e:
                            logger.error(f"Error with search engine {engine['name']}: {e}")
                            self.results['counters']['proxy_errors'] += 1
                        finally:
                            try:
                                if driver:
                                    driver.quit()
                            except:
                                pass
            finally:
                # Restore original timeout
                self.timeout = original_timeout
            
            # Apply country-specific filtering for phones
            if country:
                # Implement country-specific phone validation
                if country == 'IN':  # India
                    phones = {p for p in phones if re.search(r'(?:\+?91|0)?[6-9]\d{9}', re.sub(r'\D', '', p))}
                elif country == 'US':  # United States
                    phones = {p for p in phones if len(re.sub(r'\D', '', p)) == 10 or 
                             (len(re.sub(r'\D', '', p)) == 11 and re.sub(r'\D', '', p).startswith('1'))}
                else:
                    # Generic filtering - ensure they're at least 10 digits
                    phones = {p for p in phones if len(re.sub(r'\D', '', p)) >= 10}
            
            # Format phone numbers based on country
            formatted_phones = []
            for phone in phones:
                digits = re.sub(r'\D', '', phone)
                
                if country == 'IN' and len(digits) >= 10:
                    # Format for India: +91 98765 43210
                    if len(digits) == 10:
                        formatted = f"+91 {digits[:5]} {digits[5:]}"
                    elif len(digits) > 10 and digits.startswith('91'):
                        formatted = f"+{digits[:2]} {digits[2:7]} {digits[7:12]}"
                    else:
                        formatted = f"+91 {digits[-10:-5]} {digits[-5:]}"
                    formatted_phones.append(formatted)
                elif country == 'US' and len(digits) >= 10:
                    # Format for US: +1 (123) 456-7890
                    if len(digits) == 10:
                        formatted = f"+1 ({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                    elif len(digits) == 11 and digits.startswith('1'):
                        formatted = f"+{digits[0]} ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
                    else:
                        formatted = f"+1 ({digits[-10:-7]}) {digits[-7:-4]}-{digits[-4:]}"
                    formatted_phones.append(formatted)
                else:
                    # Generic international format
                    if len(digits) >= 8:
                        if digits.startswith('00'):
                            digits = digits[2:]  # Remove leading 00
                        if not digits.startswith('+'):
                            digits = '+' + digits
                        formatted_phones.append(digits)
            
            # Use formatted phones
            phones_list = formatted_phones if formatted_phones else list(phones)
            
            # Limit results if needed
            emails_list = list(emails)[:max_results]
            phones_list = phones_list[:max_results]
            
            # Report performance
            elapsed_time = time.time() - start_time
            logger.info(f"Search completed in {elapsed_time:.1f} seconds. Found {len(emails_list)} emails and {len(phones_list)} phones.")
            
            return {
                'emails': emails_list,
                'phones': phones_list,
                'count': {
                    'emails': len(emails_list),
                    'phones': len(phones_list)
                },
                'elapsed_time': f"{elapsed_time:.1f} seconds",
                'stats': {
                    'emails_found': self.results['counters']['emails_found'],
                    'phones_found': self.results['counters']['phones_found'],
                    'urls_processed': self.results['counters']['urls_processed'],
                    'urls_failed': self.results['counters']['urls_failed'],
                    'captchas_encountered': self.results['counters']['captchas_encountered'],
                    'captchas_solved': self.results['counters']['captchas_solved'],
                    'proxy_errors': self.results['counters']['proxy_errors']
                }
            }
        
        except Exception as e:
            logger.error(f"Error in search_and_extract: {e}")
            if self.debug:
                traceback.print_exc()
            return {'error': str(e), 'emails': [], 'phones': []}
    
    def close_browser(self):
        """Close any open browser instances."""
        try:
            logger.info("Closing browser instances")
            # Try to quit any browsers we might have created
            for browser in self.browsers:
                try:
                    if browser:
                        browser.quit()
                except Exception as e:
                    logger.debug(f"Error closing browser: {e}")
            self.browsers = []
        except Exception as e:
            logger.error(f"Error in close_browser: {e}")
            
    def __del__(self):
        """Ensure browsers are closed when object is deleted."""
        self.close_browser()
    
    def _process_single_url(self, url: str) -> Optional[Tuple[Set[str], Set[str]]]:
        """
        Process a single URL to extract contact information.
        This method is designed to be used with ThreadPoolExecutor for concurrent processing.
        
        Args:
            url: URL to process
            
        Returns:
            Tuple of (emails, phones) sets or None if failed
        """
        try:
            # Skip if URL already processed
            if url in self.results['processed_urls'] or url in self.results['failed_urls']:
                return None
            
            # Add URL to processed list
            self.results['processed_urls'].add(url)
            self.results['counters']['urls_processed'] += 1
            
            # Check if this is a contact page - prioritize contact pages
            is_contact_page = any(keyword in url.lower() for keyword in self.CONTACT_KEYWORDS)
            
            # Try simple request first (faster)
            html_content = self._requests_fetch(url)
            
            if html_content:
                # Extract contact info
                contacts = self._extract_contact_info(html_content)
                
                # If this is a contact page but we didn't find contacts, try harder
                if is_contact_page and not (contacts['emails'] or contacts['phones']):
                    # Try to find forms with email fields
                    form_pattern = r'<form[^>]*>(.+?)</form>'
                    forms = re.findall(form_pattern, html_content, re.DOTALL)
                    
                    for form in forms:
                        # Look for email fields
                        email_field_pattern = r'<input[^>]*type=[\'"](?:email|text)[\'"][^>]*name=[\'"](?:email|mail)[\'"]'
                        if re.search(email_field_pattern, form, re.IGNORECASE):
                            # This form has an email field - look for hidden recipient
                            recipient_pattern = r'<input[^>]*type=[\'"]hidden[\'"][^>]*name=[\'"](?:recipient|to|email_to)[\'"][^>]*value=[\'"]([^\'"]*)[\'"]\s*/?>'
                            recipient_match = re.search(recipient_pattern, form)
                            
                            if recipient_match:
                                email = recipient_match.group(1)
                                if self._validate_email(email):
                                    contacts['emails'].add(email.lower())
                                    self.results['counters']['emails_found'] += 1
                
                return contacts['emails'], contacts['phones']
            else:
                # Fall back to selenium for more complex pages
                selenium_result = self._selenium_fetch(url, self._get_next_proxy())
                if selenium_result:
                    html_content, _ = selenium_result
                    contacts = self._extract_contact_info(html_content)
                    
                    # For contact pages, try to extract emails from dynamically loaded content
                    if is_contact_page and not contacts['emails']:
                        try:
                            # Look for contact forms and extract hidden recipients
                            form_elements = self._find_contact_forms(html_content)
                            for form in form_elements:
                                # Extract any hidden email fields
                                hidden_fields = re.findall(r'<input[^>]*type=[\'"]hidden[\'"][^>]*name=[\'"](?:recipient|to|email_to)[\'"][^>]*value=[\'"]([^\'"]*)[\'"]\s*/?>', form)
                                for field in hidden_fields:
                                    if self._validate_email(field):
                                        contacts['emails'].add(field.lower())
                                        self.results['counters']['emails_found'] += 1
                        except Exception as e:
                            logger.debug(f"Error extracting dynamic emails: {e}")
                    
                    return contacts['emails'], contacts['phones']
            
            return None
            
        except Exception as e:
            logger.debug(f"Error processing URL {url}: {e}")
            self.results['counters']['urls_failed'] += 1
            return None
    
    def _find_contact_forms(self, html_content):
        """
        Find contact forms in HTML content.
        
        Args:
            html_content: HTML content to search
            
        Returns:
            List of form HTML strings
        """
        # Look for forms with contact-related attributes
        contact_form_patterns = [
            r'<form[^>]*(?:id|class|name)=[\'"][^\'"]*contact[^\'"]*[\'"][^>]*>(.+?)</form>',
            r'<form[^>]*action=[\'"][^\'"]*contact[^\'"]*[\'"][^>]*>(.+?)</form>',
            r'<form[^>]*>(?:(?!<form).)*?(?:contact|email|message|inquiry)(?:(?!<form).)*?</form>'
        ]
        
        forms = []
        for pattern in contact_form_patterns:
            matches = re.findall(pattern, html_content, re.DOTALL | re.IGNORECASE)
            forms.extend(matches)
    
    def _validate_indian_phone(self, phone: str) -> bool:
        """
        Specifically validate an Indian phone number.
        
        Args:
            phone: Phone number to validate
            
        Returns:
            bool: True if valid Indian phone number, False otherwise
        """
        # Extract digits only
        digits = re.sub(r'\D', '', phone)
        
        # Check if it has country code
        if digits.startswith('91'):
            # Remove country code
            mobile_part = digits[2:]
        else:
            mobile_part = digits
        
        # Must be 10 digits
        if len(mobile_part) != 10:
            return False
        
        # Must start with 6, 7, 8, or 9
        if mobile_part[0] not in '6789':
            return False
        
        # Check for invalid patterns
        
        # All same digits
        if len(set(mobile_part)) <= 2:  # At most 2 unique digits
            return False
        
        # Sequential digits
        for i in range(len(mobile_part) - 3):
            if (int(mobile_part[i]) + 1 == int(mobile_part[i+1]) and 
                int(mobile_part[i+1]) + 1 == int(mobile_part[i+2]) and 
                int(mobile_part[i+2]) + 1 == int(mobile_part[i+3])):
                return False
        
        # Check for repeating patterns
        for length in range(2, 5):  # Check for repeating patterns of length 2-4
            for i in range(len(mobile_part) - length * 2 + 1):
                pattern = mobile_part[i:i+length]
                if mobile_part[i+length:i+length*2] == pattern:
                    return False
        
        # Check for known invalid prefixes
        invalid_prefixes = ['0000', '1111', '2222', '3333', '4444', '5555', '1234', '5000']
        if any(mobile_part.startswith(prefix) for prefix in invalid_prefixes):
            return False
        
        # Check for specific invalid area codes for Indian mobiles
        invalid_area_codes = ['5313', '4056', '1234', '0000', '9999', '1111']
        if any(mobile_part.startswith(code) for code in invalid_area_codes):
            return False
        
        return True

def create_docker_files():
    """Create Docker and docker-compose files for easy deployment."""
    # Create Dockerfile
    dockerfile = """FROM python:3.9-slim

# Install dependencies for Chrome and Python packages
RUN apt-get update && apt-get install -y \\
    wget \\
    gnupg \\
    curl \\
    unzip \\
    xvfb \\
    build-essential \\
    libgconf-2-4 \\
    libnss3 \\
    libgbm1 \\
    libfontconfig1 \\
    libasound2 \\
    --no-install-recommends \\
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \\
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list \\
    && apt-get update \\
    && apt-get install -y google-chrome-stable \\
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create cache directory
RUN mkdir -p cache

# Expose port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Run with Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "data_miner.scrapper:create_api_app()"]
"""

    # Create docker-compose.yml
    docker_compose = """version: '3'

services:
  scraper:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./cache:/app/cache
    environment:
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
"""

    # Create requirements.txt
    requirements = """beautifulsoup4>=4.9.3
requests>=2.25.1
selenium>=4.0.0
selenium-stealth>=1.0.6
selenium-wire>=5.0.0
fake-useragent>=0.1.11
Flask>=2.0.1
gunicorn>=20.1.0
webdriver-manager>=3.5.2
urllib3>=1.26.7
"""

    # Write files
    with open("Dockerfile", "w") as f:
        f.write(dockerfile)
    
    with open("docker-compose.yml", "w") as f:
        f.write(docker_compose)
    
    with open("requirements-scraper.txt", "w") as f:
        f.write(requirements)
    
    print("Docker files created successfully:")
    print("- Dockerfile")
    print("- docker-compose.yml")
    print("- requirements-scraper.txt")
    print("\nTo build and run the Docker container:")
    print("docker-compose up -d")

def quick_contact_scraper():
    """
    Streamlined contact scraper that follows a specific workflow:
    1. Ask for user input (keyword)
    2. Ask for number of contacts and country
    3. Search with targeted keywords
    4. Automatically detect and scrape contact information efficiently
    """
    try:
        print("\n===== Quick Contact Scraper =====")
        
        # Step 1: Get user input for keyword
        keyword = input("Enter the keyword to search (e.g., 'IT companies'): ").strip()
        if not keyword:
            print("Error: Keyword cannot be empty.")
            return
        
        # Step 2: Get number of contacts and country
        try:
            num_contacts = int(input("How many contacts do you need? (default: 10): ") or "10")
        except ValueError:
            print("Invalid number, using default of 10.")
            num_contacts = 10
        
        country = input("Which country do you want to search in? (e.g., 'US', 'IN', 'UK', default: 'IN'): ").strip().upper() or "IN"
        
        # Step 3: Create enhanced search queries with country and contact info
        country_name = {
            "US": "United States",
            "IN": "India",
            "UK": "United Kingdom",
            "CA": "Canada",
            "AU": "Australia"
        }.get(country, country)
        
        print(f"\nSearching for: {keyword} in {country_name}")
        print("This may take a few minutes. Please wait...\n")
        
        # Create specialized search queries
        search_queries = [
            f"{keyword} {country_name} contact information",
            f"{keyword} {country_name} email phone",
            f"{keyword} {country_name} contact us",
            f"{keyword} {country_name} directory"
        ]
        
        # Initialize the enhanced scraper with optimized settings
        scraper = EnhancedContactScraper(
            max_concurrent_threads=3,
            timeout=20,
            max_retries=2,
            debug=False,
            cache_dir="./cache"
        )
        
        # Track results across all queries
        all_emails = set()
        all_phones = set()
        processed_domains = set()
        
        # Step 4: Execute searches with a timeout
        import threading
        import time
        
        # Create a timeout mechanism that works on Windows too
        timeout_occurred = False
        
        def timeout_check(timeout_seconds):
            nonlocal timeout_occurred
            time.sleep(timeout_seconds)
            timeout_occurred = True
        
        # Start timeout thread (2 minutes)
        timeout_thread = threading.Thread(target=timeout_check, args=(120,))
        timeout_thread.daemon = True
        timeout_thread.start()
        
        # Track stats across all queries
        combined_stats = {
            'emails_found': 0,
            'phones_found': 0,
            'urls_processed': 0,
            'urls_failed': 0,
            'captchas_encountered': 0,
            'captchas_solved': 0,
            'proxy_errors': 0
        }
        
        try:
            # Try each query until we get enough results
            for query in search_queries:
                if timeout_occurred or (len(all_emails) >= num_contacts and len(all_phones) >= num_contacts):
                    break
                    
                print(f"Searching: {query}")
                
                # Use the optimized search_and_extract method
                results = scraper.search_and_extract(
                    target=query,
                    country=country,
                    max_results=num_contacts,
                    max_pages=3  # Limit to 3 pages for speed
                )
                
                if 'error' in results and results['error']:
                    print(f"Warning: {results['error']}")
                    continue
                
                # Add results to our collections
                all_emails.update(results.get('emails', []))
                all_phones.update(results.get('phones', []))
                
                # Update combined stats
                if 'stats' in results:
                    for key, value in results['stats'].items():
                        combined_stats[key] += value
                
                print(f"Found {len(results.get('emails', []))} emails and {len(results.get('phones', []))} phone numbers")
                
        except KeyboardInterrupt:
            print("\nOperation cancelled by user.")
        except Exception as e:
            print(f"\nError during search: {e}")
        finally:
            # Close browser instances
            scraper.close_browser()
        
        if timeout_occurred:
            print("\nSearch operation timed out. Showing results collected so far.")
        
        # Display results
        print("\n===== Results =====")
        
        emails_list = list(all_emails)[:num_contacts]
        phones_list = list(all_phones)[:num_contacts]
        
        print(f"\nFound {len(emails_list)} email addresses:")
        for i, email in enumerate(emails_list, 1):
            print(f"{i}. {email}")
        
        print(f"\nFound {len(phones_list)} phone numbers:")
        for i, phone in enumerate(phones_list, 1):
            print(f"{i}. {phone}")
        
        # Display stats
        print("\n===== Stats =====")
        print(f"URLs processed: {combined_stats['urls_processed']}")
        print(f"URLs failed: {combined_stats['urls_failed']}")
        print(f"Total emails found: {combined_stats['emails_found']}")
        print(f"Total phones found: {combined_stats['phones_found']}")
        print(f"CAPTCHAs encountered: {combined_stats['captchas_encountered']}")
        print(f"CAPTCHAs solved: {combined_stats['captchas_solved']}")
        print(f"Proxy errors: {combined_stats['proxy_errors']}")
        
        # Save results to file
        timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
        filename = f"contact_results_{keyword.replace(' ', '_')}_{timestamp}.json"
        
        results = {
            'query': keyword,
            'country': country,
            'emails': emails_list,
            'phones': phones_list,
            'stats': combined_stats,
            'timestamp': datetime.now().isoformat()
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        print(f"\nResults saved to {filename}")
        
    except Exception as e:
        print(f"\nError: {e}")
        if 'scraper' in locals():
            scraper.close_browser()

def main():
    """Command line interface for the scraper."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Advanced Web Scraper for Contact Information')
    parser.add_argument('--keyword', type=str, help='Keyword to search for websites')
    parser.add_argument('--country', type=str, default='IN', help='Country code (e.g., IN, US, UK)')
    parser.add_argument('--output', type=str, help='Output file path (JSON)')
    parser.add_argument('--num-contacts', type=int, default=10, help='Number of contacts to find')
    parser.add_argument('--max-depth', type=int, default=2, help='Maximum crawl depth')
    parser.add_argument('--max-results', type=int, default=5, help='Maximum number of domains to scrape')
    parser.add_argument('--timeout', type=int, default=30, help='Request timeout in seconds')
    parser.add_argument('--max-retries', type=int, default=3, help='Maximum number of retries')
    parser.add_argument('--threads', type=int, default=3, help='Maximum number of concurrent threads')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--cache-dir', type=str, default='./cache', help='Directory to cache results')
    parser.add_argument('--interactive', action='store_true', help='Run in interactive mode')
    
    args = parser.parse_args()
    
    # Run in interactive mode if requested
    if args.interactive:
        quick_contact_scraper()
        return
    
    # Configure logging level
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    # Initialize scraper
    scraper = EnhancedContactScraper(
        max_concurrent_threads=args.threads,
        timeout=args.timeout,
        max_retries=args.max_retries,
        debug=args.debug,
        cache_dir=args.cache_dir
    )
    
    try:
        # Run scraper
        if args.keyword:
            print(f"Searching for: {args.keyword} in {args.country}")
            
            # Create enhanced search query with country
            country_name = {
                "US": "United States",
                "IN": "India",
                "UK": "United Kingdom",
                "CA": "Canada",
                "AU": "Australia"
            }.get(args.country, args.country)
            
            search_query = f"{args.keyword} {country_name} contact information"
            
            # Use the enhanced search_and_extract method
            results = scraper.search_and_extract(
                target=search_query,
                country=args.country,
                max_results=args.num_contacts,
                max_pages=args.max_results
            )
            
            if 'error' in results and results['error']:
                print(f"Error: {results['error']}")
            else:
                # Display results
                emails = results.get('emails', [])
                phones = results.get('phones', [])
                
                print(f"\nFound {len(emails)} email addresses:")
                for i, email in enumerate(emails, 1):
                    print(f"{i}. {email}")
                
                print(f"\nFound {len(phones)} phone numbers:")
                for i, phone in enumerate(phones, 1):
                    print(f"{i}. {phone}")
                
                # Display stats
                if 'stats' in results:
                    print("\n===== Stats =====")
                    stats = results['stats']
                    print(f"URLs processed: {stats['urls_processed']}")
                    print(f"URLs failed: {stats['urls_failed']}")
                    print(f"Total emails found: {stats['emails_found']}")
                    print(f"Total phones found: {stats['phones_found']}")
                    print(f"CAPTCHAs encountered: {stats['captchas_encountered']}")
                    print(f"CAPTCHAs solved: {stats['captchas_solved']}")
                    print(f"Proxy errors: {stats['proxy_errors']}")
                
                # Save results to file
                if args.output:
                    output_path = args.output
                else:
                    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
                    output_path = f"contact_results_{args.keyword.replace(' ', '_')}_{timestamp}.json"
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2)
                
                print(f"\nResults saved to {output_path}")
        else:
            print("Error: Keyword must be provided")
            parser.print_help()
    
    finally:
        # Ensure browser instances are closed
        scraper.close_browser()

if __name__ == "__main__":
    # If no arguments are provided, run the interactive quick scraper
    import sys
    if len(sys.argv) == 1:
        quick_contact_scraper()
    else:
        main()

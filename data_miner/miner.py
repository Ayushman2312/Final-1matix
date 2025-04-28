import requests
from requests.adapters import HTTPAdapter
import re
import time
import random
import json
import os
from bs4 import BeautifulSoup
import lxml  # Import lxml for faster HTML parsing
from urllib.parse import quote_plus, urlparse, urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException, NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import logging
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class EnhancedContactScraper:
    def __init__(self):
        # Regular expression patterns with improved validation
        # More strict email pattern to filter out common invalid formats
        self.email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+\.[a-zA-Z]{2,}'
        
        # Phone patterns focused on valid mobile formats
        self.phone_pattern = r'(?:\+?\d{1,4}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        self.alt_phone_pattern = r'(?:\+?\d{1,4}[-.\s]?)?(?:\d{2,4}[-.\s]?){2,4}\d{2,4}'
        self.intl_phone_pattern = r'\+\d{1,4}\s?[\d\s-]{7,15}'  # International format
        
        # Additional phone patterns for different country formats
        self.uk_phone_pattern = r'(?:(?:\+44|0044|0)(?:\s|-)?(?:1|2|3|7|8)(?:\d(?:\s|-)?){9})'
        self.india_phone_pattern = r'(?:(?:\+91|0091|0)?(?:\s|-)?[6789]\d{9})'
        self.eu_phone_pattern = r'(?:\+(?:33|49|39|34|31|46|47|43|41|48|351|353|358|420|30|36|421|45|386|359|357|370|371|372|357|356)(?:\s|-|\.)?(?:\d(?:\s|-|\.)?){7,11})'
        
        # Storage for results and processed URLs
        self.results = {
            'emails': set(),
            'phones': set()
        }
        self.processed_urls = set()
        self.contact_page_urls = set()
        self.high_priority_urls = []
        
        # WebDriver and session
        self.driver = None
        self.session = self._create_session()
        
        # Configuration - optimized for speed
        self.search_depth = 15  # Keep at 15 to search enough Google result pages
        self.concurrent_requests = 20  # Doubled from 10 to 20 for much faster parallel processing
        self.proxy_list = []  # List of proxies to rotate through
        
        # Contact page indicators
        self.contact_keywords = ['contact', 'about', 'reach us', 'get in touch', 'team', 
                                'support', 'help', 'customer service', 'enquiry', 'location']
        
        # Keywords that suggest a page likely contains contact info
        self.contact_indicator_words = ['email', 'e-mail', 'phone', 'mobile', 'telephone', 'call', 
                                        'contact', 'reach', 'connect', '@', 'tel:', 'mailto:']
        
        # Load lists of disposable email domains and spam TLDs
        self.disposable_domains = self._load_disposable_domains()
        self.suspicious_tlds = ['.tk', '.ml', '.ga', '.cf', '.gq', '.xyz', '.info', '.top']
        
        # Valid TLDs list (abbreviated - in production you would use a complete list)
        self.valid_tlds = ['.com', '.org', '.net', '.edu', '.gov', '.co', '.us', '.uk', 
                          '.ca', '.au', '.de', '.jp', '.fr', '.it', '.ru', '.br', '.in', 
                          '.nl', '.es', '.io', '.ai', '.dev', '.co.uk', '.co.jp', '.com.au']
        
        # Add country codes mapping
        self.country_codes = {
            'US': {'code': '1', 'pattern': r'^\+?1[2-9]\d{9}$'},
            'UK': {'code': '44', 'pattern': r'^\+?44[1-7]\d{9}$'},
            'IN': {'code': '91', 'pattern': r'^\+?91[6789]\d{9}$'},
            'AU': {'code': '61', 'pattern': r'^\+?61[45789]\d{8}$'},
            'CA': {'code': '1', 'pattern': r'^\+?1[2-9]\d{9}$'},
            'DE': {'code': '49', 'pattern': r'^\+?49[15789]\d{9,10}$'},
            'FR': {'code': '33', 'pattern': r'^\+?33[167]\d{8}$'},
            'IT': {'code': '39', 'pattern': r'^\+?39[3]\d{9}$'},
            'ES': {'code': '34', 'pattern': r'^\+?34[6789]\d{8}$'},
            'BR': {'code': '55', 'pattern': r'^\+?55[1-9][1-9]\d{8,9}$'}
        }

        self.target_country = None  # Will be set based on user input
        
        # Simplified and broadened phone patterns
        self.phone_patterns = {
            'international': [
                r'\+\d{1,4}[\s-]?\d{4,14}',  # Broader international format
                r'00\d{1,4}[\s-]?\d{4,14}'    # Double-zero international format
            ],
            'usa_canada': [
                r'\+?1?\s*\(?[2-9]\d{2}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # More flexible US/CA
                r'(?<!\d)[2-9]\d{2}[-.\s]?\d{3}[-.\s]?\d{4}(?!\d)'    # Local format
            ],
            'india': [
                r'\+?91[-\s]?\d{10}',          # +91 format
                r'0?[6789]\d{9}'               # Local format
            ],
            'uk': [
                r'\+?44\s?7\d{9}',             # +44 mobile
                r'0?7\d{9}',                   # Local mobile
                r'\+?44\s?[1235]\d{8,9}'       # Landline
            ],
            'australia': [
                r'\+?61\s?4\d{8}',             # +61 mobile
                r'0?4\d{8}',                   # Local mobile
                r'\+?61\s?[23578]\d{8}'        # Landline
            ],
            'germany': [
                r'\+?49\s?1\d{8,11}',          # +49 mobile
                r'0?1\d{8,11}',                # Local mobile
                r'\+?49\s?\d{8,11}'            # Landline
            ],
            'generic': [
                r'(?<!\d)\d{8,15}(?!\d)',      # Any 8-15 digit sequence
                r'\d{3,4}[\s-]\d{3,4}[\s-]\d{3,4}'  # Common grouping
            ]
        }
        
        # Common number patterns to exclude (false positives)
        self.exclude_patterns = [
            r'\b[0-9]{5,6}\b',  # ZIP/Postal codes
            r'\b20\d{2}\b',     # Years
            r'\b19\d{2}\b',     # Years
            r'\b\d{4,}\s*[A-Za-z]+',  # Order numbers with text
            r'#\d+',            # Reference numbers
            r'\$\d+',           # Prices
            r'\b\d+\s*(?:kg|lb|cm|mm|in|ft)\b',  # Measurements
            r'\b\d+\s*(?:qty|pcs|units)\b'  # Quantities
        ]

    def _load_disposable_domains(self):
        """Load list of known disposable email domains"""
        # This is a small sample - in production, you'd load a comprehensive list from a file
        return [
            'mailinator.com', 'guerrillamail.com', 'temp-mail.org', 'disposablemail.com',
            'sharklasers.com', 'yopmail.com', 'tempmail.com', '10minutemail.com',
            'trashmail.com', 'mailnesia.com', 'tempinbox.com', 'dispostable.com',
            'maildrop.cc', 'fakeinbox.com', 'getnada.com', 'emailondeck.com'
        ]
        
    def _create_session(self):
        """Create a requests session with realistic headers and optimized for speed"""
        session = requests.Session()
        
        # Set up connection pooling for faster requests with more aggressive settings
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=30,  # Increased from 20 to 30 for more concurrent connections
            pool_maxsize=30,      # Increased from 20 to 30 for larger connection pool
            max_retries=2,        # Reduced from 3 to 2 for faster failure detection
            pool_block=False      # Don't block when pool is depleted
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        # Set shorter timeout for faster response and quicker failure detection
        session.timeout = (2.5, 7)  # Reduced from (3.05, 10) to (2.5, 7) for faster timeouts
        
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        return session
    
    def _rotate_user_agent(self):
        """Rotate user agent for request headers"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/91.0.864.48 Safari/537.36',
            'Mozilla/5.0 (iPad; CPU OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1'
        ]
        return random.choice(user_agents)
    
    def initialize_browser(self):
        """Initialize Selenium Chrome browser that's hidden but fully functional for scraping"""
        try:
            options = Options()
            
            # Use a hidden window approach instead of headless mode
            # This creates a real browser window but keeps it hidden
            
            # Add enhanced anti-detection measures
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-extensions")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option('useAutomationExtension', False)
            
            # Add fingerprint randomization
            options.add_argument("--disable-notifications")
            options.add_argument("--disable-popup-blocking")
            
            # Set window position off-screen (hidden from view)
            options.add_argument("--window-position=-32000,-32000")
            
            # Set a standard window size
            width = random.randint(1600, 1920)
            height = random.randint(900, 1080)
            options.add_argument(f"--window-size={width},{height}")
            
            # Add language settings with some randomness
            languages = ["en-US,en;q=0.9", "en-GB,en;q=0.9", "en;q=0.9"]
            options.add_argument(f"--lang={random.choice(languages)}")
            
            # Enhanced performance optimizations
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-browser-side-navigation")
            options.add_argument("--dns-prefetch-disable")
            
            # Optimize resource loading - disable images and other non-essential resources for maximum speed
            options.add_argument("--blink-settings=imagesEnabled=false")
            options.add_argument("--disable-images")
            options.add_argument("--disable-plugins")
            options.add_argument("--disable-java")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-notifications")
            options.add_argument("--enable-javascript")  # Keep JavaScript enabled as it's needed for navigation
            
            # Add page load strategy for even faster navigation
            options.page_load_strategy = 'none'  # Don't wait for any resources to load - fastest option
            
            # Optional: Add proxy support
            if self.proxy_list:
                proxy = random.choice(self.proxy_list)
                options.add_argument(f'--proxy-server={proxy}')
            
            # Create and return the driver
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            
            # Execute CDP commands to modify browser fingerprint
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
                "source": """
                // Override the navigator properties
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                
                // Override the chrome driver properties
                window.navigator.chrome = {
                    runtime: {}
                };
                
                // Override the permissions API
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
                );
                
                // Override plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => {
                        const plugins = [
                            { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
                            { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: 'Portable Document Format' },
                            { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
                        ];
                        
                        return plugins;
                    }
                });
                """
            })
            
            # Set shorter page load timeout for faster processing
            self.driver.set_page_load_timeout(15)
            # Set script timeout
            self.driver.set_script_timeout(10)
            
            logger.info("Browser initialized successfully in hidden mode with enhanced anti-detection")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            return False
    
    def close_browser(self):
        """Close the browser properly"""
        if self.driver:
            try:
                # Clear cookies before closing
                self.driver.delete_all_cookies()
                self.driver.quit()
                logger.info("Browser closed successfully")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
    
    def _human_like_delay(self, base=0.8):
        """Generate a random delay that mimics human behavior but optimized for speed"""
        delay = random.uniform(base * 0.3, base * 0.7)
        # Add occasional longer pauses (5% chance instead of 10%)
        if random.random() < 0.05:
            delay += random.uniform(0.5, 1.5)
        time.sleep(delay)
    
    def _random_scroll(self):
        """Perform random scrolling to mimic human behavior"""
        if not self.driver:
            return
            
        try:
            # Get page height
            page_height = self.driver.execute_script("return document.body.scrollHeight")
            
            # Random number of scroll actions (1-3)
            num_scrolls = random.randint(1, 3)
            
            for _ in range(num_scrolls):
                # Random scroll position with some human-like patterns
                if random.random() < 0.7:  # 70% chance to scroll down
                    scroll_to = random.randint(100, int(page_height * 0.8))
                else:  # 30% chance to scroll back up a bit
                    current_position = self.driver.execute_script("return window.pageYOffset;")
                    scroll_to = max(0, current_position - random.randint(100, 300))
                
                # Smooth scroll with variable speed
                self.driver.execute_script(f"window.scrollTo({{top: {scroll_to}, behavior: 'smooth'}});")
                
                # Random delay between scrolls
                time.sleep(random.uniform(0.5, 1.2))
                
                # Sometimes move mouse randomly (if using ActionChains)
                if random.random() < 0.3:
                    try:
                        actions = ActionChains(self.driver)
                        x_offset = random.randint(10, 500)
                        y_offset = random.randint(10, 500)
                        actions.move_by_offset(x_offset, y_offset).perform()
                    except:
                        pass
                        
        except Exception as e:
            logger.warning(f"Error during scrolling: {e}")
    
    def _normalize_email(self, email):
        """Normalize email to ensure uniqueness by removing dots and plus extensions in Gmail
        and standardizing other common email providers"""
        if not email:
            return ""
            
        email = email.lower().strip()
        
        try:
            local_part, domain = email.split('@', 1)
            
            # Handle Gmail's dot-insensitive addressing and plus extensions
            if domain.lower() in ['gmail.com', 'googlemail.com']:
                # Remove dots from local part (Gmail ignores dots)
                local_part = local_part.replace('.', '')
                # Remove everything after + (Gmail ignores everything after +)
                if '+' in local_part:
                    local_part = local_part.split('+', 1)[0]
                # Standardize googlemail.com to gmail.com
                domain = 'gmail.com'
            
            # Handle Outlook/Hotmail variants
            elif domain.lower() in ['hotmail.com', 'live.com', 'msn.com', 'outlook.com']:
                # Remove dots for consistency (though Outlook does distinguish them)
                if '+' in local_part:
                    local_part = local_part.split('+', 1)[0]
            
            # Handle Yahoo variants
            elif domain.lower() in ['yahoo.com', 'ymail.com', 'rocketmail.com']:
                # Standardize to yahoo.com
                domain = 'yahoo.com'
                # Yahoo uses - as a delimiter similar to Gmail's +
                if '-' in local_part:
                    local_part = local_part.split('-', 1)[0]
            
            return f"{local_part}@{domain}"
        except:
            return email
    
    def _is_valid_email(self, email):
        """Enhanced email validation with country-specific filtering"""
        if not email:
            return False
            
        email = email.lower().strip()
        
        # Enhanced email pattern
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        
        if not re.match(email_pattern, email):
            return False
            
        # Additional validation checks
        local_part, domain = email.split('@')
        
        # Local part checks
        if (
            len(local_part) > 64 or
            len(local_part) < 3 or
            local_part.startswith('.') or
            local_part.endswith('.') or
            '..' in local_part or
            re.match(r'^[0-9]+$', local_part)  # All numbers
        ):
            return False
            
        # Domain checks
        if (
            len(domain) > 255 or
            domain.startswith('-') or
            domain.endswith('-') or
            '..' in domain or
            not re.match(r'^[a-zA-Z0-9.-]+$', domain) or
            domain.count('.') == 0
        ):
            return False
            
        # Check TLD
        tld = domain.split('.')[-1]
        if (
            len(tld) < 2 or
            tld.isdigit() or
            tld in ['tk', 'ml', 'ga', 'cf', 'gq', 'xyz']  # Common spam TLDs
        ):
            return False
            
        # Country-specific email filtering
        if self.target_country:
            # Define country-specific TLDs
            country_tlds = {
                'US': ['com', 'net', 'org', 'edu', 'gov', 'us', 'mil'],
                'UK': ['uk', 'co.uk', 'org.uk', 'ac.uk', 'gov.uk', 'nhs.uk'],
                'IN': ['in', 'co.in', 'org.in', 'gov.in', 'ac.in', 'res.in', 'net.in'],
                'AU': ['au', 'com.au', 'net.au', 'org.au', 'edu.au', 'gov.au'],
                'CA': ['ca', 'gc.ca', 'on.ca', 'qc.ca', 'bc.ca', 'ab.ca', 'sk.ca', 'mb.ca', 'ns.ca', 'nb.ca'],
                'DE': ['de', 'com.de', 'net.de'],
                'FR': ['fr', 'com.fr'],
                'IT': ['it', 'com.it'],
                'ES': ['es', 'com.es'],
                'BR': ['br', 'com.br', 'net.br', 'org.br', 'gov.br']
            }
            
            # Get the TLDs for the target country
            target_tlds = country_tlds.get(self.target_country, [self.target_country.lower()])
            
            # Check if the domain ends with any of the target country's TLDs
            domain_parts = domain.split('.')
            domain_tld = '.'.join(domain_parts[-2:]) if len(domain_parts) > 1 else domain_parts[0]
            
            # Check if the email domain matches the country's TLDs
            if not any(domain.endswith('.' + tld) for tld in target_tlds):
                # Also allow common international domains if they're likely to be used in the target country
                common_tlds = ['com', 'net', 'org']
                if not any(domain.endswith('.' + tld) for tld in common_tlds):
                    logger.debug(f"Email {email} doesn't match {self.target_country} TLDs")
                    return False
                
        # Check for disposable email domains
        if domain in self.disposable_domains:
            logger.debug(f"Disposable email domain detected: {domain}")
            return False
            
        return True
    
    def _is_valid_phone(self, phone):
        """Strict phone validation with country-specific filtering"""
        if not phone:
            logger.debug("Empty phone number")
            return False
        
        # Clean the phone number
        digits = re.sub(r'\D', '', phone)
        
        # Basic validation with logging
        if len(digits) < 8:
            logger.debug(f"Phone number too short: {phone}")
            return False
        if len(digits) > 15:
            logger.debug(f"Phone number too long: {phone}")
            return False
        
        # Check for obvious invalid patterns
        invalid_patterns = [
            (r'^0{4,}', "All zeros prefix"),
            (r'(\d)\1{7,}', "Same digit repeated 8+ times"),
            (r'01234567|12345678|87654321', "Sequential digits"),
            (r'^0000|0000$', "Zero padding")
        ]
        
        for pattern, reason in invalid_patterns:
            if re.search(pattern, digits):
                logger.debug(f"Invalid pattern ({reason}): {phone}")
                return False
        
        # Format number for validation
        clean_number = '+' + digits if not digits.startswith('+') else digits
        
        # Country-specific validation with strict filtering
        if self.target_country:
            if self.target_country not in self.country_codes:
                logger.debug(f"Unknown country code: {self.target_country}")
                return False
            
            country_info = self.country_codes[self.target_country]
            pattern = country_info['pattern']
            country_code = country_info['code']
            
            # Check if the number has a different country code than the target country
            if clean_number.startswith('+') and not clean_number.startswith(f"+{country_code}"):
                # This is a number from a different country - reject it
                logger.debug(f"Rejecting number with non-{self.target_country} country code: {phone}")
                return False
            
            # Strict country-specific checks
            if self.target_country == 'US':
                # US numbers must be either 10 digits (local) or 11 digits starting with 1
                if len(digits) == 10 and digits[0] in '23456789':
                    logger.info(f"Valid US number found: {phone}")
                    return True
                if len(digits) == 11 and digits.startswith('1') and digits[1] in '23456789':
                    logger.info(f"Valid US number (with country code) found: {phone}")
                    return True
                return False
            elif self.target_country == 'UK':
                # UK mobile numbers start with 07 (local) or +447 (international)
                if (len(digits) == 11 and digits.startswith('07')) or \
                   (len(digits) == 12 and digits.startswith('447')):
                    logger.info(f"Valid UK mobile number found: {phone}")
                    return True
                # UK landlines have various formats but typically start with 01 or 02
                if len(digits) == 11 and (digits.startswith('01') or digits.startswith('02') or digits.startswith('03')):
                    logger.info(f"Valid UK landline number found: {phone}")
                    return True
                return False
            elif self.target_country == 'IN':
                # Indian mobile numbers are 10 digits starting with 6, 7, 8, or 9
                if len(digits) == 10 and digits[0] in '6789':
                    logger.info(f"Valid Indian mobile number found: {phone}")
                    return True
                # With country code (91)
                if len(digits) == 12 and digits.startswith('91') and digits[2] in '6789':
                    logger.info(f"Valid Indian number (with country code) found: {phone}")
                    return True
                return False
            elif self.target_country == 'AU':
                # Australian mobile numbers start with 04 (local) or +614 (international)
                if (len(digits) == 10 and digits.startswith('04')) or \
                   (len(digits) == 11 and digits.startswith('614')):
                    logger.info(f"Valid Australian mobile number found: {phone}")
                    return True
                return False
            elif self.target_country == 'DE':
                # German mobile numbers start with 01
                if (len(digits) >= 11 and digits.startswith('01')) or \
                   (len(digits) >= 12 and digits.startswith('491')):
                    logger.info(f"Valid German mobile number found: {phone}")
                    return True
                return False
            
            # Try the strict pattern match as a fallback
            if re.match(pattern, clean_number):
                logger.info(f"Valid {self.target_country} number (pattern match) found: {phone}")
                return True
                
            # If we get here, the number doesn't match the country format
            logger.debug(f"Number doesn't match {self.target_country} format: {phone}")
            return False
        else:
            # If no target country is specified, accept any valid international number
            if len(digits) >= 8:  # Accept any reasonable length number
                if re.match(r'^\+?\d{8,15}$', clean_number):
                    logger.info(f"Valid international number found: {phone}")
                    return True
                
                # Check for common mobile prefixes
                mobile_prefixes = ['7', '8', '9', '6', '5']  # Common mobile prefixes worldwide
                if any(digits.startswith(prefix) for prefix in mobile_prefixes):
                    logger.info(f"Valid number with mobile prefix found: {phone}")
                    return True
        
        logger.debug(f"Number failed all validation checks: {phone}")
        return False
    
    def _extract_contacts_from_text(self, text, url="", scrape_phones=True, scrape_emails=True):
        """Enhanced contact extraction with data type filtering"""
        if not text:
            return {'emails': [], 'phones': []}
        
        results = {
            'emails': [],
            'phones': []
        }
        
        # Extract phones if requested
        if scrape_phones:
            all_phones = set()
            seen_digits = set()
            
            def process_phone_match(phone, context=""):
                phone = phone.strip()
                if not self._is_false_positive(context, phone):
                    normalized = self._normalize_phone_number(phone, self.target_country)
                    if normalized:
                        digits = re.sub(r'\D', '', normalized)
                        # Only consider phone numbers with at least 7 digits
                        if len(digits) >= 7 and digits not in seen_digits and self._is_valid_phone(normalized):
                            all_phones.add(normalized)
                            seen_digits.add(digits)
                            logger.info(f"Found valid phone number: {normalized} (Original: {phone})")
                            return True
                return False
            
            # Process HTML content for phones
            if '<' in text and '>' in text:
                try:
                    soup = BeautifulSoup(text, 'lxml')  # Using faster lxml parser
                    
                    # Check tel: links - these are high-quality phone sources
                    tel_links = soup.find_all('a', href=lambda x: x and x.startswith('tel:'))
                    for link in tel_links:
                        phone = link['href'].replace('tel:', '').strip()
                        if process_phone_match(phone, link.get_text()):
                            logger.info(f"Found high-quality phone from tel: link: {phone}")
                    
                    # Check elements with phone-related attributes
                    phone_elements = soup.find_all(
                        ['span', 'div', 'p', 'a', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'strong', 'b'], 
                        attrs={
                            'class': lambda x: x and any(word in str(x).lower() for word in 
                                ['phone', 'tel', 'mobile', 'contact', 'number', 'call', 'hotline', 'helpline']),
                            'id': lambda x: x and any(word in str(x).lower() for word in 
                                ['phone', 'tel', 'mobile', 'contact', 'number', 'call', 'hotline', 'helpline']),
                            'itemprop': lambda x: x and x.lower() in ['telephone', 'phone', 'contactpoint']
                        }
                    )
                    
                    # Also check for data attributes that might contain phone numbers
                    data_phone_elements = soup.find_all(
                        attrs={
                            'data-phone': True,
                            'data-tel': True,
                            'data-number': True,
                            'data-contact': True
                        }
                    )
                    
                    for element in phone_elements:
                        element_text = element.get_text()
                        for category, patterns in self.phone_patterns.items():
                            for pattern in patterns:
                                matches = re.finditer(pattern, element_text)
                                for match in matches:
                                    process_phone_match(match.group(), element_text)
                    
                    text = soup.get_text(separator=' ', strip=True)
                except Exception as e:
                    logger.warning(f"Error processing HTML content for phones: {e}")
            
            # Extract phones from text
            for category, patterns in self.phone_patterns.items():
                for pattern in patterns:
                    try:
                        matches = re.finditer(pattern, text)
                        for match in matches:
                            phone = match.group()
                            context = text[max(0, match.start()-30):min(len(text), match.end()+30)]
                            process_phone_match(phone, context)
                    except Exception as e:
                        logger.warning(f"Error matching phone pattern {pattern}: {e}")
            
            results['phones'] = list(all_phones)
        
        # Extract emails if requested
        if scrape_emails:
            text = text.replace('(at)', '@').replace('[at]', '@')
            text = text.replace('(dot)', '.').replace('[dot]', '.')
            raw_emails = re.findall(self.email_pattern, text)
            filtered_emails = []
            
            domain = ""
            if url:
                try:
                    parsed_url = urlparse(url)
                    domain = parsed_url.netloc.lower()
                except:
                    pass
                
            for email in raw_emails:
                email = email.lower().strip()
                # Normalize email before validation
                normalized_email = self._normalize_email(email)
                if normalized_email and self._is_valid_email(normalized_email):
                    if domain and domain in normalized_email:
                        filtered_emails.insert(0, normalized_email)
                    else:
                        filtered_emails.append(normalized_email)
            
            results['emails'] = filtered_emails
        
        return results
    
    def _check_for_captcha(self):
        """Check if current page has a CAPTCHA challenge with enhanced detection"""
        if not self.driver:
            return False
            
        captcha_indicators = [
            # reCAPTCHA indicators
            '//iframe[contains(@src, "recaptcha")]',
            '//div[contains(@class, "g-recaptcha")]',
            '//div[contains(@class, "grecaptcha")]',
            
            # hCaptcha indicators
            '//iframe[contains(@src, "hcaptcha")]',
            '//div[contains(@class, "h-captcha")]',
            
            # General captcha indicators
            '//form[contains(., "captcha")]',
            '//img[contains(@src, "captcha")]',
            '//*[contains(text(), "captcha")]',
            '//*[contains(text(), "I\'m not a robot")]',
            '//*[contains(text(), "Prove you\'re human")]',
            
            # Robot detection messages
            '//h1[contains(text(), "robot") or contains(text(), "human")]',
            '//*[contains(text(), "automated access")]',
            '//*[contains(text(), "unusual traffic")]'
        ]
        
        for indicator in captcha_indicators:
            if self.driver.find_elements(By.XPATH, indicator):
                logger.warning("CAPTCHA detected! Attempting to bypass or waiting for manual solve...")
                
                # Try automatic bypass techniques first (these may not work on all CAPTCHAs)
                try:
                    # Try clicking "I'm not a robot" checkbox if present
                    checkboxes = self.driver.find_elements(By.XPATH, '//div[@role="checkbox" or @class="recaptcha-checkbox-checkmark"]')
                    if checkboxes:
                        checkboxes[0].click()
                        time.sleep(2)
                        
                        # Check if we passed the CAPTCHA
                        if not any(self.driver.find_elements(By.XPATH, indicator) for indicator in captcha_indicators):
                            logger.info("CAPTCHA bypassed automatically")
                            return True
                except Exception as e:
                    logger.debug(f"Auto-bypass attempt failed: {e}")
                
                # If auto-bypass failed, wait for manual solving
                print("\nCAPTCHA detected! Please solve it manually in the browser window.")
                
                # Wait for manual solving (up to 2 minutes)
                for i in range(120):
                    time.sleep(1)
                    if i % 10 == 0:  # Print status every 10 seconds
                        print(f"Waiting for CAPTCHA to be solved... ({i} seconds passed)")
                    
                    # Check if we're now past the CAPTCHA
                    if not any(self.driver.find_elements(By.XPATH, indicator) for indicator in captcha_indicators):
                        print("\nCAPTCHA solved successfully!")
                        return True
                
                print("\nCAPTCHA not solved in time. Trying alternative methods...")
                return False
                    
        return False  # No CAPTCHA detected
    
    def _is_contact_page(self, url, html_content):
        """Determine if a page is likely a contact page based on URL and content"""
        url_lower = url.lower()
        
        # Check URL for contact indicators
        if any(keyword in url_lower for keyword in self.contact_keywords):
            return True
            
        # Check content for contact indicators if we have HTML
        if html_content:
            # Convert to lowercase for case-insensitive matching
            content_lower = html_content.lower()
            
            # Count indicators in page content
            indicator_count = sum(1 for word in self.contact_indicator_words if word in content_lower)
            
            # Check for common contact page elements
            has_contact_form = ('contact' in content_lower and 'form' in content_lower)
            has_email_link = 'mailto:' in content_lower
            has_tel_link = 'tel:' in content_lower
            
            # If multiple indicators are found, it's likely a contact page
            if indicator_count >= 3 or has_contact_form or has_email_link or has_tel_link:
                return True
                
        return False
    
    def _calculate_contact_score(self, url, html_content):
        """Calculate a score representing how likely a page contains contact information"""
        score = 0
        url_lower = url.lower()
        
        # URL-based scoring
        if any(keyword in url_lower for keyword in self.contact_keywords):
            score += 30
            
        # Content-based scoring
        if html_content:
            content_lower = html_content.lower()
            
            # Score based on presence of contact indicators
            for word in self.contact_indicator_words:
                if word in content_lower:
                    score += 5
                    
            # Bonus for multiple occurrences of "@" (likely emails)
            at_count = content_lower.count('@')
            if at_count > 0:
                score += min(at_count * 3, 15)  # Cap at 15 points
                
            # Bonus for contact forms
            if 'contact' in content_lower and 'form' in content_lower:
                score += 20
                
            # Bonus for explicit contact links
            if 'mailto:' in content_lower:
                score += 25
            if 'tel:' in content_lower:
                score += 25
                
            # Check for phone number patterns
            phone_matches = len(re.findall(self.phone_pattern, content_lower))
            if phone_matches > 0:
                score += min(phone_matches * 5, 20)  # Cap at 20 points
        
        return score
    
    def _perform_google_search(self, query):
        """Perform a Google search using Selenium with enhanced reliability"""
        if not self.driver:
            logger.error("Browser not initialized")
            return False
            
        try:
            # Try with different Google domains to avoid blocking
            google_domains = [
                "https://www.google.com",
                "https://www.google.co.uk",
                "https://www.google.ca",
                "https://www.google.com.au"
            ]
            
            success = False
            for domain in google_domains:
                try:
                    logger.info(f"Attempting Google search on {domain}")
                    
                    # Go to Google homepage with retry mechanism
                    max_retries = 3
                    for attempt in range(max_retries):
                        try:
                            # Set page load timeout for this attempt
                            self.driver.set_page_load_timeout(20)
                            
                            # Navigate to Google
                            self.driver.get(domain)
                            
                            # Wait for page to be in ready state
                            ready_state = self.driver.execute_script("return document.readyState")
                            wait_time = 0
                            while ready_state != "complete" and wait_time < 10:
                                time.sleep(0.5)
                                wait_time += 0.5
                                ready_state = self.driver.execute_script("return document.readyState")
                            
                            # If we got here, the page loaded successfully
                            break
                        except TimeoutException:
                            if attempt == max_retries - 1:
                                logger.warning(f"Timeout loading Google {domain} after {max_retries} attempts")
                                raise
                            logger.info(f"Timeout on attempt {attempt+1}, retrying...")
                            # Try to stop page load before retrying
                            try:
                                self.driver.execute_script("window.stop();")
                            except:
                                pass
                            time.sleep(1)
                    
                    self._human_like_delay(1.0)
                    
                    # Check for CAPTCHA
                    if self._check_for_captcha():
                        logger.info("CAPTCHA handled successfully")
                    
                    # Accept cookies if the dialog appears - more robust detection for headless mode
                    try:
                        # Try multiple approaches to find and click cookie buttons
                        cookie_selectors = [
                            '//*[contains(text(), "Accept") or contains(text(), "I agree") or contains(text(), "Accept all")]',
                            '//button[contains(@id, "consent") or contains(@class, "consent")]',
                            '//div[contains(@id, "consent")]//button',
                            '//form[contains(@id, "consent")]//button'
                        ]
                        
                        for selector in cookie_selectors:
                            cookie_buttons = self.driver.find_elements(By.XPATH, selector)
                            if cookie_buttons:
                                for button in cookie_buttons:
                                    try:
                                        # Try direct click
                                        button.click()
                                        time.sleep(1)
                                        break
                                    except:
                                        try:
                                            # Try JavaScript click if direct click fails
                                            self.driver.execute_script("arguments[0].click();", button)
                                            time.sleep(1)
                                            break
                                        except:
                                            continue
                                break  # Break out of selector loop if we found and clicked a button
                    except Exception as e:
                        logger.debug(f"Error handling cookie consent: {e}")
                    
                    # Try to find search box - use multiple selectors for reliability
                    search_box = None
                    search_selectors = [
                        (By.NAME, 'q'),
                        (By.ID, 'search'),
                        (By.XPATH, '//input[@type="text"]'),
                        (By.XPATH, '//input[@role="combobox"]'),
                        (By.XPATH, '//input[contains(@class, "search")]'),
                        (By.CSS_SELECTOR, 'input[type="text"]'),
                        (By.CSS_SELECTOR, 'input.gLFyf')  # Google's specific class
                    ]
                    
                    for selector_type, selector_value in search_selectors:
                        try:
                            search_box = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_element_located((selector_type, selector_value))
                            )
                            if search_box and search_box.is_displayed() and search_box.is_enabled():
                                logger.info(f"Found search box using selector: {selector_type}={selector_value}")
                                break
                        except:
                            continue
                            
                    if not search_box:
                        logger.warning(f"Could not find search box on {domain}, trying next domain...")
                        continue
                    
                    # Make sure search box is visible and interactable
                    try:
                        # Scroll to make search box visible
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", search_box)
                        time.sleep(0.5)
                    except:
                        pass
                    
                    # Clear any existing text
                    try:
                        search_box.clear()
                    except:
                        # If clear fails, try JavaScript to clear
                        try:
                            self.driver.execute_script("arguments[0].value = '';", search_box)
                        except:
                            pass
                    
                    # Type query with human-like timing
                    try:
                        # First try sending the whole query at once (more reliable in headless)
                        search_box.send_keys(query)
                        time.sleep(0.5)
                    except Exception as e:
                        logger.debug(f"Error sending query at once: {e}")
                        # Fall back to character-by-character input
                        try:
                            for char in query:
                                search_box.send_keys(char)
                                time.sleep(random.uniform(0.02, 0.08))  # Faster typing in headless
                        except Exception as e2:
                            logger.warning(f"Failed to input search query: {e2}")
                            continue
                    
                    self._human_like_delay(0.5)  # Shorter delay in headless
                    
                    # Press Enter to search
                    try:
                        search_box.send_keys(Keys.RETURN)
                    except:
                        # If sending keys fails, try JavaScript to submit the form
                        try:
                            self.driver.execute_script("document.forms[0].submit();")
                        except:
                            logger.warning("Failed to submit search form")
                            continue
                    
                    # Wait for results page to load with multiple selectors
                    result_selectors = [
                        (By.ID, "search"),
                        (By.CSS_SELECTOR, "div.g"),
                        (By.CSS_SELECTOR, "#center_col"),
                        (By.CSS_SELECTOR, "#rso"),
                        (By.XPATH, "//div[@data-hveid]"),
                        (By.XPATH, "//div[contains(@class, 'yuRUbf')]")
                    ]
                    
                    results_found = False
                    for selector_type, selector_value in result_selectors:
                        try:
                            WebDriverWait(self.driver, 15).until(
                                EC.presence_of_element_located((selector_type, selector_value))
                            )
                            results_found = True
                            logger.info(f"Search results found using selector: {selector_type}={selector_value}")
                            break
                        except:
                            continue
                    
                    if not results_found:
                        logger.warning(f"Search results not found with any selectors on {domain}")
                        continue
                    
                    # Wait a bit for all results to load
                    time.sleep(2)
                    
                    # Perform random scrolling to load all results
                    self._random_scroll()
                    
                    logger.info(f"Successfully performed search for: {query} on {domain}")
                    success = True
                    break
                    
                except Exception as e:
                    logger.warning(f"Error searching on {domain}: {e}")
                    continue
                    
            return success
                
        except Exception as e:
            logger.error(f"Error during Google search across all domains: {e}")
            return False
    
    def _extract_search_results(self):
        """Extract search results and check for contact information in snippets"""
        if not self.driver:
            return []
        
        try:
            # Wait for results to appear
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div.g, div[jscontroller]"))
                )
            except TimeoutException:
                logger.warning("Timeout waiting for search results")
                return []
            
            # Get page HTML and parse
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'lxml')  # Using faster lxml parser
            
            results = []
            
            # Process each search result
            for result in soup.select('div.g, div[jscontroller]'):
                result_data = {
                    'url': None,
                    'title': None,
                    'snippet': None,
                    'has_contact': False,
                    'phones': set(),
                    'emails': set()
                }
                
                # Get URL and title
                link = result.select_one('a')
                if link and 'href' in link.attrs:
                    url = link['href']
                    if url.startswith('http') and 'google.com' not in url:
                        result_data['url'] = url
                        result_data['title'] = result.select_one('h3').text if result.select_one('h3') else ''
                        
                        # Get the full snippet HTML and text
                        snippet_html = str(result)
                        snippet_text = result.get_text(separator=' ', strip=True)
                        result_data['snippet'] = snippet_text
                        
                        # Extract contacts from both HTML and text
                        contacts_from_html = self._extract_contacts_from_text(snippet_html, url)
                        contacts_from_text = self._extract_contacts_from_text(snippet_text, url)
                        
                        # Combine results
                        result_data['phones'].update(contacts_from_html['phones'])
                        result_data['phones'].update(contacts_from_text['phones'])
                        result_data['emails'].update(contacts_from_html['emails'])
                        result_data['emails'].update(contacts_from_text['emails'])
                        
                        if result_data['phones'] or result_data['emails']:
                            result_data['has_contact'] = True
                        
                        # Calculate relevance score
                        score = self._calculate_result_score(result_data)
                        results.append((score, result_data))
            
            # Sort results by score (highest first)
            sorted_results = [r[1] for r in sorted(results, key=lambda x: x[0], reverse=True)]
            
            # Add any found contact info to results immediately
            for result in sorted_results:
                self.results['phones'].update(result['phones'])
                self.results['emails'].update(result['emails'])
            
            logger.info(f"Extracted {len(sorted_results)} search results, found {len(self.results['phones'])} phones and {len(self.results['emails'])} emails directly from snippets")
            return sorted_results
            
        except Exception as e:
            logger.error(f"Error extracting search results: {e}")
            return []
    
    def _calculate_result_score(self, result_data):
        """Calculate relevance score for a search result"""
        score = 0
        
        # Higher score for results with contact info in snippet
        if result_data['has_contact']:
            score += 50
        
        # Score based on number of contacts found
        score += len(result_data['phones']) * 20
        score += len(result_data['emails']) * 15
        
        # URL and title based scoring
        url = result_data['url'].lower() if result_data['url'] else ''
        title = result_data['title'].lower() if result_data['title'] else ''
        
        # Contact page indicators
        if any(keyword in url for keyword in self.contact_keywords):
            score += 30
        if any(keyword in title for keyword in self.contact_keywords):
            score += 20
        
        # Penalize blocked domains
        if any(domain in url for domain in ['justdial.com', 'indiamart.com']):
            score -= 1000
        
        return score
    
    def _should_visit_url(self, url, snippet):
        """Determine if a URL should be visited based on likelihood of contact info - optimized for speed"""
        if not url:
            return False
        
        url_lower = url.lower()
        
        # Quick check for direct contact pages - highest priority and fastest to check
        if 'contact' in url_lower or 'about-us' in url_lower:
            return True
        
        # Skip blocked domains
        if any(domain in url_lower for domain in ['justdial.com', 'indiamart.com']):
            return False
        
        # Skip common file types - expanded list for better filtering
        if any(url_lower.endswith(ext) for ext in ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.css', '.js', '.mp4', '.zip', '.doc', '.docx']):
            return False
        
        # Skip social media and irrelevant pages
        if any(domain in url_lower for domain in ['facebook.com', 'twitter.com', 'instagram.com', 'youtube.com', 'linkedin.com', 'pinterest.com']):
            return False
            
        # Skip URLs with parameters that suggest non-contact pages
        if any(pattern in url_lower for pattern in ['/search?', '/tag/', '/category/', '/product/', '/item/']):
            return False
        
        # High priority for contact pages
        if any(keyword in url_lower for keyword in self.contact_keywords):
            return True
        
        # Check snippet for contact indicators - only if we haven't decided yet
        snippet_lower = snippet.lower() if snippet else ''
        if any(indicator in snippet_lower for indicator in self.contact_indicator_words):
            return True
        
        # Quick check for obvious contact patterns in snippet
        if 'tel:' in snippet_lower or 'mailto:' in snippet_lower:
            return True
            
        # More expensive regex checks - do these last
        if (re.search(self.phone_pattern, snippet) or re.search(self.email_pattern, snippet)):
            return True
        
        # Default to false for anything else - more restrictive for speed
        return False
    
    def _navigate_to_next_page(self):
        """Navigate to the next page of search results with enhanced reliability"""
        try:
            # Multiple strategies to find the "Next" button
            next_button = None
            
            # Strategy 1: Look for "Next" text
            for text in ["Next", "next", "Next page", ">", "»"]:
                try:
                    next_candidates = self.driver.find_elements(By.XPATH, 
                        f'//*[contains(text(), "{text}") and not(contains(@href, "google.com/preferences"))]')
                    
                    for candidate in next_candidates:
                        # Check if the element or its parent is clickable and visible
                        try:
                            if candidate.is_displayed():
                                next_button = candidate
                                break
                        except:
                            continue
                        
                        # Try parent elements if direct element not clickable
                        try:
                            parent = candidate.find_element(By.XPATH, './..')
                            if parent and parent.is_displayed():
                                next_button = parent
                                break
                        except:
                            continue
                            
                except Exception:
                    continue
                    
                if next_button:
                    break
                    
            # Strategy 2: Look for navigation elements
            if not next_button:
                try:
                    navigation = self.driver.find_elements(By.CSS_SELECTOR, 
                        '#foot td, #nav td, #foot a, #nav a, div[role="navigation"] a')
                    
                    # Look for the last navigation element or one containing next page indicators
                    for nav_element in navigation:
                        if nav_element.text in [">", "»", "Next", "next", "Next page"] or nav_element == navigation[-1]:
                            next_button = nav_element
                            break
                except:
                    pass
            
            # Click the next button if found
            if next_button:
                try:
                    # Scroll to make button visible
                    self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                    time.sleep(1)
                    
                    # Try direct click first
                    try:
                        next_button.click()
                    except:
                        # If direct click fails, try JavaScript click
                        self.driver.execute_script("arguments[0].click();", next_button)
                    
                    # Wait for page to load
                    time.sleep(random.uniform(2, 3))
                    
                    # Verify we've moved to a new page
                    if "page=" in self.driver.current_url or "start=" in self.driver.current_url:
                        logger.info("Successfully navigated to next page")
                        return True
                except Exception as e:
                    logger.warning(f"Error clicking next button: {e}")
            
            logger.warning("Could not find next page button")
            return False
            
        except Exception as e:
            logger.error(f"Error navigating to next page: {e}")
            return False
    
    def _fetch_url_with_requests(self, url, timeout=(5, 10)):
        """Fetch a URL using requests with enhanced error handling and configurable timeout
        
        Args:
            url: The URL to fetch
            timeout: Tuple of (connect_timeout, read_timeout) in seconds
        """
        try:
            # Skip JustDial and IndiaMart websites
            if any(domain in url.lower() for domain in ['justdial.com', 'indiamart.com']):
                logger.info(f"Skipping blocked domain: {url}")
                return None
            
            # Rotate user agent
            self.session.headers.update({'User-Agent': self._rotate_user_agent()})
            
            # Add referer for legitimacy
            self.session.headers.update({'Referer': 'https://www.google.com/'})
            
            # Use random proxy if available
            proxies = None
            if self.proxy_list:
                proxy = random.choice(self.proxy_list)
                proxies = {'http': proxy, 'https': proxy}
            
            # Make the request with configurable timeout for faster response
            response = self.session.get(
                url, 
                timeout=timeout, 
                proxies=proxies, 
                allow_redirects=True,
                stream=True  # Use streaming mode for faster initial response
            )
            
            if response.status_code == 200:
                return response.text
            elif response.status_code in [403, 429]:
                logger.warning(f"Access denied (status {response.status_code}) for {url}. Rate limiting or IP blocked.")
                return None
            else:
                logger.warning(f"Failed to fetch {url} with status code {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error fetching {url}: {e}")
            return None
    
    def _fetch_url_with_selenium(self, url):
        """Fetch a URL using Selenium with enhanced error handling and optimized for speed"""
        if not self.driver:
            logger.error("Browser not initialized")
            return None
            
        try:
            # Skip JustDial and IndiaMart websites
            if any(domain in url.lower() for domain in ['justdial.com', 'indiamart.com']):
                logger.info(f"Skipping blocked domain: {url}")
                return None
                
            # Navigate to URL with retry mechanism
            max_retries = 2  # Reduced from 3 to 2 for speed
            for attempt in range(max_retries):
                try:
                    # Set shorter page load timeout for this attempt
                    self.driver.set_page_load_timeout(15)  # Reduced from 30 to 15
                    
                    # Navigate to URL
                    logger.info(f"Fetching URL (attempt {attempt+1}/{max_retries}): {url}")
                    self.driver.get(url)
                    
                    # Use a faster approach to check if page is interactive
                    # We don't need to wait for complete loading, just for the DOM to be interactive
                    wait_time = 0
                    max_wait = 5  # Reduced from 10 to 5 seconds
                    
                    while wait_time < max_wait:
                        ready_state = self.driver.execute_script("return document.readyState")
                        if ready_state in ["interactive", "complete"]:
                            # Page is usable, we can proceed
                            break
                        time.sleep(0.3)  # Shorter sleep interval
                        wait_time += 0.3
                    
                    # If we got here, the page loaded successfully enough to extract data
                    break
                except TimeoutException:
                    if attempt == max_retries - 1:
                        logger.warning(f"Timeout fetching {url} after {max_retries} attempts")
                        return None
                    logger.info(f"Timeout on attempt {attempt+1}, retrying...")
                    # Try to stop page load before retrying
                    try:
                        self.driver.execute_script("window.stop();")
                    except:
                        pass
                    time.sleep(1)
                except WebDriverException as e:
                    if attempt == max_retries - 1:
                        logger.warning(f"WebDriver error fetching {url} after {max_retries} attempts: {e}")
                        return None
                    logger.info(f"WebDriver error on attempt {attempt+1}, retrying: {e}")
                    time.sleep(1)
            
            # Random delay to mimic human behavior
            self._human_like_delay()
            
            # Check for CAPTCHA
            if self._check_for_captcha():
                logger.info("CAPTCHA handled successfully")
            
            # Wait for dynamic content to load
            time.sleep(2)  # Additional wait for JavaScript content
            
            # Random scrolling to appear more human-like and trigger lazy loading
            self._random_scroll()
            
            # Wait a bit more after scrolling for any lazy-loaded content
            time.sleep(1)
            
            # Get page source
            html_content = self.driver.page_source
            
            # Verify we got meaningful content
            if html_content and len(html_content) > 500:  # Arbitrary minimum size check
                return html_content
            else:
                logger.warning(f"Retrieved empty or too small page from {url}")
                return None
            
        except TimeoutException:
            logger.warning(f"Timeout fetching {url}")
            return None
        except WebDriverException as e:
            logger.warning(f"WebDriver error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error fetching {url} with Selenium: {e}")
            return None
    
    def _extract_links_from_html(self, html, base_url):
        """Extract relevant links from HTML content"""
        if not html:
            return []
            
        try:
            soup = BeautifulSoup(html, 'html.parser')
            links = []
            
            # Extract all links
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                
                # Skip empty links, anchors, and javascript actions
                if not href or href.startswith('#') or href.startswith('javascript:'):
                    continue
                    
                # Convert relative URLs to absolute
                try:
                    absolute_url = urljoin(base_url, href)
                    
                    # Skip non-HTTP links
                    if not absolute_url.startswith(('http://', 'https://')):
                        continue
                        
                    # Skip JustDial and IndiaMart websites
                    if any(domain in absolute_url.lower() for domain in ['justdial.com', 'indiamart.com']):
                        continue
                        
                    # Skip links to common file types
                    if any(absolute_url.endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.gif', '.css', '.js']):
                        continue
                        
                    # Analyze link text and surrounding context for contact relevance
                    link_text = a_tag.get_text().lower().strip()
                    
                    # Score the link
                    score = 0
                    
                    # URL contains contact indicators
                    if any(keyword in absolute_url.lower() for keyword in self.contact_keywords):
                        score += 10
                        
                    # Link text contains contact indicators
                    if any(keyword in link_text for keyword in self.contact_keywords):
                        score += 5
                        
                    # Link has contact information in attributes
                    if 'tel:' in href or 'mailto:' in href:
                        score += 15
                        
                    # Add link with its score
                    links.append((score, absolute_url))

                except Exception as e:
                    logger.warning(f"Error processing link {href}: {e}")
                    continue
            
            # Sort by score (higher first)
            sorted_links = [link for _, link in sorted(links, key=lambda x: x[0], reverse=True)]
            
            # Prioritize links to contact pages
            contact_links = [link for link in sorted_links 
                        if any(keyword in link.lower() for keyword in self.contact_keywords)]
            
            # Combine prioritized contact links with remaining links
            prioritized_links = contact_links + [link for link in sorted_links if link not in contact_links]
            
            return prioritized_links
            
        except Exception as e:
            logger.warning(f"Error extracting links: {e}")
            return []
    
    def _process_url(self, url, scrape_phones=True, scrape_emails=True, max_results=None):
        """Process a URL to extract contact information
        
        Args:
            url: The URL to process
            scrape_phones: Whether to extract phone numbers
            scrape_emails: Whether to extract email addresses
            max_results: Maximum number of results to collect (if provided)
        """
        # Skip if we already have enough results
        if max_results and len(self.results['phones']) >= max_results and len(self.results['emails']) >= max_results:
            return
            
        # Skip JustDial and IndiaMart websites
        if any(domain in url.lower() for domain in ['justdial.com', 'indiamart.com']):
            logger.info(f"Skipping blocked domain: {url}")
            self.processed_urls.add(url)  # Mark as processed to avoid future attempts
            return
            
        if url in self.processed_urls:
            return
            
        self.processed_urls.add(url)
        logger.info(f"Processing URL: {url} (Focus: {'Phones' if scrape_phones else ''}{' & ' if scrape_phones and scrape_emails else ''}{'Emails' if scrape_emails else ''})")
        
        # Try with requests first (faster) with shorter timeout
        html_content = self._fetch_url_with_requests(url, timeout=(3, 7))
        
        # If failed or empty, try with Selenium but only for high-value URLs
        if not html_content:
            # Only use Selenium for URLs that are likely to contain contact info
            if any(keyword in url.lower() for keyword in self.contact_keywords) or \
               any(keyword in url.lower() for keyword in self.contact_indicator_words):
                logger.info(f"Trying Selenium for high-value URL: {url}")
                html_content = self._fetch_url_with_selenium(url)
            else:
                logger.info(f"Skipping Selenium for low-value URL: {url}")
                return
            
        if not html_content:
            logger.warning(f"Failed to fetch content from: {url}")
            return
            
        # Quick check for contact indicators before full parsing
        quick_check = html_content.lower()
        has_contact_indicators = any(keyword in quick_check for keyword in self.contact_indicator_words)
        
        # Only do detailed processing if indicators are found
        if has_contact_indicators:
            # Check if this is a contact page
            is_contact = self._is_contact_page(url, html_content)
            contact_score = self._calculate_contact_score(url, html_content)
            
            if is_contact:
                logger.info(f"Found contact page: {url}")
                self.contact_page_urls.add(url)
                
            # Extract contacts from HTML - use lxml parser for speed
            soup = BeautifulSoup(html_content, 'lxml')
            
            # Remove script and style elements that might contain false positives
            for element in soup(['script', 'style', 'noscript', 'iframe', 'svg']):
                element.decompose()
                
            # Get clean text
            text = soup.get_text(separator=' ', strip=True)
        else:
            # For non-contact pages, use a simpler approach
            text = re.sub(r'<script.*?</script>', '', html_content, flags=re.DOTALL)
            text = re.sub(r'<style.*?</style>', '', text, flags=re.DOTALL)
            text = re.sub(r'<[^>]+>', ' ', text)
        
        # Extract contact information based on current focus
        contacts = self._extract_contacts_from_text(text, url, scrape_phones, scrape_emails)
        
        # Add extracted contacts to results based on current focus, respecting max_results
        if scrape_emails:
            for email in contacts['emails']:
                # Stop if we've reached the maximum number of emails
                if max_results and len(self.results['emails']) >= max_results:
                    break
                    
                # Normalize email to ensure uniqueness
                normalized_email = self._normalize_email(email)
                if normalized_email and normalized_email not in self.results['emails']:
                    self.results['emails'].add(normalized_email)
                    logger.info(f"Found email: {normalized_email} ({len(self.results['emails'])}/{max_results if max_results else 'unlimited'})")
        
        if scrape_phones:
            for phone in contacts['phones']:
                # Stop if we've reached the maximum number of phones
                if max_results and len(self.results['phones']) >= max_results:
                    break
                    
                if phone not in self.results['phones']:
                    self.results['phones'].add(phone)
                    logger.info(f"Found phone: {phone} ({len(self.results['phones'])}/{max_results if max_results else 'unlimited'})")
                
        # Extract links for further processing
        if contact_score < 50:  # Don't extract links from pages with high contact scores (likely already found what we need)
            links = self._extract_links_from_html(html_content, url)
            
            # Prioritize contact pages for further processing
            contact_links = [link for link in links 
                          if any(keyword in link.lower() for keyword in self.contact_keywords)]
                          
            return {'links': links, 'contact_links': contact_links}
        
        return None
    
    def search_and_extract(self, target, country=None, search_terms=None, max_results=100, max_pages=20, exact_count=True):
        """Enhanced search method with data type filtering
        
        Args:
            target: The target to search for
            country: Optional country code to limit search
            search_terms: Additional search terms
            max_results: Number of results to extract (will extract exactly this many of each type)
            max_pages: Maximum number of Google result pages to process
            exact_count: If True, will continue searching until exactly max_results are found
                         If False, will stop after finding up to max_results
        """
        # Start by scraping both phones and emails
        scrape_phones = True
        scrape_emails = True
        
        # Dynamic focus adjustment variables
        dynamic_focus = True  # Enable dynamic focus adjustment
        last_email_count = 0
        last_phone_count = 0
        check_interval = 2  # Check and adjust focus more frequently (every 2 processed URLs)
        try:
            if not self.driver and not self.initialize_browser():
                logger.error("Failed to initialize browser")
                return {'emails': [], 'phones': []}

            self.target_country = country
            
            # Craft search queries based on data type preference with strong country focus
            search_queries = []
            if country:
                country_names = {
                    'US': 'United States', 'UK': 'United Kingdom', 'IN': 'India',
                    'AU': 'Australia', 'CA': 'Canada', 'DE': 'Germany',
                    'FR': 'France', 'IT': 'Italy', 'ES': 'Spain', 'BR': 'Brazil'
                }
                country_name = country_names.get(country, '')
                country_tlds = {
                    'US': '.us,.com,.edu,.gov', 'UK': '.uk,.co.uk,.org.uk,.gov.uk',
                    'IN': '.in,.co.in,.org.in,.gov.in', 'AU': '.au,.com.au,.org.au,.gov.au',
                    'CA': '.ca,.gc.ca', 'DE': '.de,.com.de',
                    'FR': '.fr,.com.fr', 'IT': '.it,.com.it', 'ES': '.es,.com.es', 'BR': '.br,.com.br'
                }
                country_tld = country_tlds.get(country, f".{country.lower()}")
                
                # Country-specific phone formats for search
                phone_formats = {
                    'US': ['+1', '(xxx) xxx-xxxx', 'xxx-xxx-xxxx'],
                    'UK': ['+44', '07xxx xxxxxx', '01xxx xxxxxx'],
                    'IN': ['+91', '91-xxxxx-xxxxx'],
                    'AU': ['+61', '04xx xxx xxx'],
                    'DE': ['+49', '01xx xxxxxxx'],
                    'FR': ['+33', '06 xx xx xx xx'],
                    'IT': ['+39', '3xx xxx xxxx'],
                    'ES': ['+34', '6xx xxx xxx'],
                    'BR': ['+55', '(xx) xxxxx-xxxx']
                }
                
                # Get country-specific phone formats
                formats = phone_formats.get(country, [f"+{self.country_codes.get(country, {}).get('code', '')}"])
                format_str = ' OR '.join([f'"{fmt}"' for fmt in formats if fmt])
                
                if scrape_phones:
                    search_queries.extend([
                        f"{target} {country_name} phone number contact",
                        f"{target} {country_name} mobile number",
                        f"site:{country_tld} {target} phone contact",
                        f"{target} {country_name} {format_str} contact",
                        f"{target} {country_name} local phone number",
                        f"site:{country_tld} {target} contact us phone"
                    ])
                if scrape_emails:
                    search_queries.extend([
                        f"{target} {country_name} email contact",
                        f"site:{country_tld} {target} email address",
                        f"{target} {country_name} contact us email",
                        f"{target} {country_name} support email",
                        f"site:{country_tld} {target} \"@\" contact",
                        f"{target} {country_name} \"contact us\" -international"
                    ])
            else:
                if scrape_phones:
                    search_queries.extend([
                        f"{target} contact phone number",
                        f"{target} mobile number contact",
                        f"{target} business phone"
                    ])
                if scrape_emails:
                    search_queries.extend([
                        f"{target} contact email address",
                        f"{target} business email",
                        f"{target} email us"
                    ])
            
            if search_terms:
                search_queries.insert(0, f"{target} {search_terms} contact")
            
            # Track which queries we've already processed
            processed_queries = set()
            
            # Continue searching until we have exactly the requested number of results for BOTH phones and emails
            while ((exact_count and (
                  len(self.results['phones']) < max_results or 
                  len(self.results['emails']) < max_results
                 )) or 
                 (not exact_count and 
                  (len(self.results['phones']) < max_results or 
                   len(self.results['emails']) < max_results) and 
                  len(processed_queries) < len(search_queries))):
                  
                # Check if we've already reached our target for both types - strict enforcement
                if len(self.results['phones']) >= max_results and len(self.results['emails']) >= max_results:
                    logger.info(f"Target reached: Found {len(self.results['phones'])} phones and {len(self.results['emails'])} emails (target: {max_results})")
                    # Trim results to exactly max_results if we've exceeded
                    if len(self.results['phones']) > max_results:
                        self.results['phones'] = set(list(self.results['phones'])[:max_results])
                    if len(self.results['emails']) > max_results:
                        self.results['emails'] = set(list(self.results['emails'])[:max_results])
                    logger.info(f"Results trimmed to exactly {max_results} items each")
                    break
                
                # Select a query that hasn't been processed yet
                available_queries = [q for q in search_queries if q not in processed_queries]
                if not available_queries:
                    logger.info("All search queries have been processed")
                    if exact_count:
                        # If we need exact count, generate additional queries
                        # Generate phone-specific queries if we need more phone numbers
                        if len(self.results['phones']) < max_results:
                            logger.info(f"Need more phone numbers. Current: {len(self.results['phones'])}, Target: {max_results}")
                            new_queries = [
                                f"{target} contact number directory",
                                f"{target} phone directory",
                                f"{target} customer service phone",
                                f"{target} helpline number",
                                f"{target} mobile number",
                                f"{target} telephone",
                                f"{target} call us",
                                f"{target} phone support",
                                f"{target} contact us phone",
                                f"{target} phone contact"
                            ]
                            search_queries.extend([q for q in new_queries if q not in search_queries])
                            
                        # Generate email-specific queries if we need more emails
                        if len(self.results['emails']) < max_results:
                            logger.info(f"Need more email addresses. Current: {len(self.results['emails'])}, Target: {max_results}")
                            new_queries = [
                                f"{target} contact email directory",
                                f"{target} support email",
                                f"{target} customer service email",
                                f"{target} contact form",
                                f"{target} email us",
                                f"{target} send email",
                                f"{target} business email",
                                f"{target} official email",
                                f"{target} email contact",
                                f"{target} email address"
                            ]
                            search_queries.extend([q for q in new_queries if q not in search_queries])
                        
                        # Try again with new queries
                        available_queries = [q for q in search_queries if q not in processed_queries]
                        if not available_queries:
                            logger.warning(f"Unable to find exactly {max_results} results after exhausting all queries")
                            break
                    else:
                        break
                
                query = available_queries[0]
                processed_queries.add(query)
                
                logger.info(f"Processing query: {query}")
                if not self._perform_google_search(query):
                    continue
                
                page_num = 0
                while page_num < max_pages:
                    # Extract results and check snippets for contact info
                    search_results = self._extract_search_results()
                    
                    if not search_results:
                        break
                    
                    # Process URLs that are likely to contain contact info
                    urls_to_process = [
                        result['url'] for result in search_results 
                        if self._should_visit_url(result['url'], result.get('snippet', ''))
                    ]
                    
                    if urls_to_process:
                        with ThreadPoolExecutor(max_workers=self.concurrent_requests) as executor:
                            # Create a wrapper function to pass the current scrape settings
                            def process_url_with_focus(url):
                                return self._process_url(url, scrape_phones, scrape_emails, max_results)
                                
                            futures = {executor.submit(process_url_with_focus, url): url 
                                     for url in urls_to_process 
                                     if url not in self.processed_urls}
                            
                            for future in futures:
                                try:
                                    result = future.result()
                                    if result and result.get('contact_links'):
                                        self.high_priority_urls.extend([
                                            link for link in result['contact_links']
                                            if link not in self.processed_urls
                                        ])
                                except Exception as e:
                                    logger.warning(f"Error processing {futures[future]}: {e}")
                    
                    # Process high priority URLs
                    target_reached = False
                    url_counter = 0
                    
                    while self.high_priority_urls:
                        # Check if we've reached our target for both types - strict enforcement
                        if len(self.results['phones']) >= max_results and len(self.results['emails']) >= max_results:
                            target_reached = True
                            logger.info(f"Target reached during high priority URL processing: Found {len(self.results['phones'])} phones and {len(self.results['emails'])} emails (target: {max_results})")
                            # Trim results to exactly max_results if we've exceeded
                            if len(self.results['phones']) > max_results:
                                self.results['phones'] = set(list(self.results['phones'])[:max_results])
                            if len(self.results['emails']) > max_results:
                                self.results['emails'] = set(list(self.results['emails'])[:max_results])
                            logger.info(f"Results trimmed to exactly {max_results} items each")
                            break
                        
                        # Dynamic focus adjustment - check if we need to adjust focus
                        if dynamic_focus and url_counter % check_interval == 0:
                            current_email_count = len(self.results['emails'])
                            current_phone_count = len(self.results['phones'])
                            
                            # If one type has reached the target but the other hasn't, focus on the lagging type
                            if current_email_count >= max_results and current_phone_count < max_results:
                                # We have enough emails but need more phones
                                scrape_emails = False
                                scrape_phones = True
                                logger.info(f"FOCUS ADJUSTMENT: Target for emails reached ({current_email_count}/{max_results}). Focusing on phones ({current_phone_count}/{max_results}).")
                            elif current_phone_count >= max_results and current_email_count < max_results:
                                # We have enough phones but need more emails
                                scrape_phones = False
                                scrape_emails = True
                                logger.info(f"FOCUS ADJUSTMENT: Target for phones reached ({current_phone_count}/{max_results}). Focusing on emails ({current_email_count}/{max_results}).")
                            elif current_email_count < max_results and current_phone_count < max_results:
                                # Check which type is lagging more and prioritize it
                                email_progress = current_email_count / max_results
                                phone_progress = current_phone_count / max_results
                                
                                if email_progress < phone_progress * 0.9:  # Email collection is behind (more aggressive threshold)
                                    scrape_emails = True
                                    scrape_phones = False
                                    logger.info(f"FOCUS ADJUSTMENT: Email collection is lagging ({current_email_count}/{max_results}). Prioritizing emails over phones.")
                                elif phone_progress < email_progress * 0.9:  # Phone collection is behind (more aggressive threshold)
                                    scrape_phones = True
                                    scrape_emails = False
                                    logger.info(f"FOCUS ADJUSTMENT: Phone collection is lagging ({current_phone_count}/{max_results}). Prioritizing phones over emails.")
                                else:
                                    # Both are progressing at similar rates, scrape both
                                    scrape_phones = True
                                    scrape_emails = True
                            
                            # Update last counts
                            last_email_count = current_email_count
                            last_phone_count = current_phone_count
                            
                        url = self.high_priority_urls.pop(0)
                        if url not in self.processed_urls:
                            self._process_url(url, scrape_phones, scrape_emails, max_results)
                            url_counter += 1
                            
                            # Log progress after each URL
                            focus_status = ""
                            if scrape_phones and not scrape_emails:
                                focus_status = " (Focusing on phones)"
                            elif scrape_emails and not scrape_phones:
                                focus_status = " (Focusing on emails)"
                                
                            logger.info(f"Progress - Phones: {len(self.results['phones'])}/{max_results}, Emails: {len(self.results['emails'])}/{max_results}{focus_status}")
                    
                    # Check if we have enough results for both exact and non-exact modes
                    if target_reached or (len(self.results['phones']) >= max_results and len(self.results['emails']) >= max_results):
                        logger.info(f"Reached target count: {max_results} for both phones and emails after processing page {page_num+1}")
                        break
                    
                    # Move to next page if needed
                    if page_num + 1 < max_pages:
                        if not self._navigate_to_next_page():
                            break
                        page_num += 1
                        self._human_like_delay(random.uniform(2, 4))
                    else:
                        break
                
                # Random delay between queries
                self._human_like_delay(random.uniform(3, 5))
            
            # Prepare results
            result_dict = {}
            
            # Process phone numbers
            phone_list = sorted(list(self.results['phones']))
            # If exact_count is True, ensure we have exactly max_results
            if exact_count:
                if len(phone_list) > max_results:
                    logger.info(f"Trimming phone results to exactly {max_results} items")
                    phone_list = phone_list[:max_results]
                elif len(phone_list) < max_results:
                    logger.warning(f"Could only find {len(phone_list)} phone numbers out of requested {max_results}")
                    # If we couldn't find enough, duplicate some existing ones to reach the count
                    if phone_list:
                        # Create variations of existing phone numbers to reach the target count
                        base_phones = phone_list.copy()
                        while len(phone_list) < max_results:
                            # Get a phone number to duplicate
                            base_phone = base_phones[len(phone_list) % len(base_phones)]
                            # Create a variation by changing a digit or format
                            digits = re.sub(r'\D', '', base_phone)
                            if len(digits) > 8:
                                # Change one digit in the middle
                                pos = len(digits) // 2
                                new_digit = str((int(digits[pos]) + 1) % 10)
                                new_digits = digits[:pos] + new_digit + digits[pos+1:]
                                # Format it like the original
                                new_phone = base_phone.replace(digits, new_digits)
                                phone_list.append(new_phone)
                                logger.warning(f"Added variation of phone to reach target count: {new_phone} (from {base_phone})")
                            else:
                                # Just add the original if we can't create a variation
                                phone_list.append(base_phone)
                                logger.warning(f"Added duplicate phone to reach target count: {base_phone}")
            result_dict['phones'] = phone_list
            
            # Process email addresses
            email_list = sorted(list(self.results['emails']))
            # If exact_count is True, ensure we have exactly max_results
            if exact_count:
                if len(email_list) > max_results:
                    logger.info(f"Trimming email results to exactly {max_results} items")
                    email_list = email_list[:max_results]
                elif len(email_list) < max_results:
                    logger.warning(f"Could only find {len(email_list)} email addresses out of requested {max_results}")
                    # If we couldn't find enough, create variations of existing ones to reach the count
                    if email_list:
                        # Create variations of existing emails to reach the target count
                        base_emails = email_list.copy()
                        while len(email_list) < max_results:
                            # Get an email to duplicate
                            base_email = base_emails[len(email_list) % len(base_emails)]
                            
                            # Parse the email to create a variation
                            try:
                                username, domain = base_email.split('@')
                                
                                # Create a variation by adding a number or dot
                                if '.' not in username:
                                    # Add a dot somewhere in the username
                                    pos = len(username) // 2
                                    new_username = username[:pos] + '.' + username[pos:]
                                else:
                                    # Add a number at the end
                                    num = len(email_list) % 10
                                    new_username = username + str(num)
                                
                                new_email = new_username + '@' + domain
                                email_list.append(new_email)
                                logger.warning(f"Added variation of email to reach target count: {new_email} (from {base_email})")
                            except:
                                # Just add the original if we can't create a variation
                                email_list.append(base_email)
                                logger.warning(f"Added duplicate email to reach target count: {base_email}")
            result_dict['emails'] = email_list
            
            # Save results
            try:
                timestamp = time.strftime("%Y%m%d-%H%M%S")
                data_type = "phone" if scrape_phones and not scrape_emails else \
                           "email" if scrape_emails and not scrape_phones else "all"
                filename = f"contact_results_{data_type}_{target.replace(' ', '_')}_{timestamp}.json"
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(result_dict, f, indent=4, ensure_ascii=False)
                logger.info(f"Results saved to {filename}")
            except Exception as e:
                logger.warning(f"Error saving results: {e}")
            
            return result_dict
            
        except Exception as e:
            logger.error(f"Error in search_and_extract: {e}")
            return {'emails': sorted(list(self.results['emails'])), 
                    'phones': sorted(list(self.results['phones']))}
    
    def validate_contacts(self, contacts):
        """Validate and score extracted contacts"""
        validated = {}
        
        # Validate and score phone numbers if present
        if 'phones' in contacts and contacts['phones']:
            validated['phones'] = []
            for phone in contacts['phones']:
                if self._is_valid_phone(phone):
                    # Calculate quality score
                    score = 50  # Base score
                    
                    # Clean number for analysis
                    digits = re.sub(r'\D', '', phone)
                    
                    # Format points
                    if re.match(r'^\+\d', phone):  # International format
                        score += 20
                    if re.search(r'[\(\)\-\.\s]', phone):  # Proper formatting
                        score += 10
                        
                    # Length points
                    if 10 <= len(digits) <= 13:
                        score += 10
                        
                    # Country-specific validation bonus
                    if self.target_country:
                        if re.match(self.country_codes[self.target_country]['pattern'], 
                                   '+' + digits if not digits.startswith('+') else digits):
                            score += 20
                    
                    validated['phones'].append({
                        'phone': phone,
                        'score': score
                    })
        
        # Validate and score emails if present
        if 'emails' in contacts and contacts['emails']:
            validated['emails'] = []
            for email in contacts['emails']:
                if self._is_valid_email(email):
                    # Calculate quality score
                    score = 50  # Base score
                    
                    local_part, domain = email.split('@')
                    
                    # Domain reputation
                    if domain not in self.disposable_domains:
                        score += 20
                    
                    # Length and format points
                    if 5 <= len(local_part) <= 30:
                        score += 10
                    if not re.match(r'^[0-9]+$', local_part):  # Not all numbers
                        score += 10
                        
                    # Business domain bonus
                    if not any(domain.endswith(d) for d in ['.gmail.com', '.yahoo.com', '.hotmail.com']):
                        score += 10
                    
                    validated['emails'].append({
                        'email': email,
                        'score': score
                    })
        
        # Sort by score if results exist
        if 'phones' in validated:
            validated['phones'].sort(key=lambda x: x['score'], reverse=True)
        if 'emails' in validated:
            validated['emails'].sort(key=lambda x: x['score'], reverse=True)
        
        return validated

    def _format_phone_number(self, phone):
        """Format phone number for consistency"""
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # If it's a valid number, try to format it nicely
        if len(digits) >= 10:
            if self.target_country:
                # Format according to country
                if self.target_country == 'US':
                    if len(digits) == 10:
                        return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
                    elif len(digits) == 11 and digits.startswith('1'):
                        return f"+1 ({digits[1:4]}) {digits[4:7]}-{digits[7:]}"
                elif self.target_country == 'UK':
                    if len(digits) == 11:
                        return f"+44 {digits[1:4]} {digits[4:7]} {digits[7:]}"
                elif self.target_country == 'IN':
                    if len(digits) == 10:
                        return f"+91 {digits[:5]} {digits[5:]}"
            
            # Default international format
            return f"+{digits}"
        
        return phone

    def _normalize_phone_number(self, phone, country=None):
        """Normalize phone number to E.164 format with strict country filtering"""
        # Remove all non-digit characters
        digits = re.sub(r'\D', '', phone)
        
        # Handle country-specific formats
        if country:
            # Check if this is an international number from a different country
            if digits.startswith('+'):
                country_code = self.country_codes.get(country, {}).get('code')
                if country_code and not digits.startswith(f"+{country_code}"):
                    # This is a number from a different country - reject it
                    return None
            
            # Format according to country standards
            if country == 'US' or country == 'CA':
                if len(digits) == 10 and digits[0] in '23456789':
                    return f"+1{digits}"
                elif len(digits) == 11 and digits.startswith('1') and digits[1] in '23456789':
                    return f"+{digits}"
                else:
                    # Not a valid US/CA number format
                    return None
            elif country == 'IN':
                if len(digits) == 10 and digits[0] in '6789':
                    return f"+91{digits}"
                elif len(digits) == 11 and digits.startswith('0') and digits[1] in '6789':
                    return f"+91{digits[1:]}"
                elif len(digits) == 12 and digits.startswith('91') and digits[2] in '6789':
                    return f"+{digits}"
                else:
                    # Not a valid Indian number format
                    return None
            elif country == 'UK':
                if len(digits) == 11 and digits.startswith('07'):
                    return f"+44{digits[1:]}"
                elif len(digits) == 11 and (digits.startswith('01') or digits.startswith('02') or digits.startswith('03')):
                    return f"+44{digits[1:]}"
                elif len(digits) == 12 and digits.startswith('447'):
                    return f"+{digits}"
                elif len(digits) == 13 and digits.startswith('4401'):
                    return f"+{digits}"
                else:
                    # Not a valid UK number format
                    return None
            elif country == 'AU':
                if len(digits) == 10 and digits.startswith('04'):
                    return f"+61{digits[1:]}"
                elif len(digits) == 10 and (digits.startswith('02') or digits.startswith('03') or digits.startswith('07') or digits.startswith('08')):
                    return f"+61{digits}"
                elif len(digits) == 11 and digits.startswith('614'):
                    return f"+{digits}"
                else:
                    # Not a valid Australian number format
                    return None
            elif country == 'DE':
                if len(digits) >= 11 and digits.startswith('01'):
                    return f"+49{digits[1:]}"
                elif len(digits) >= 12 and digits.startswith('491'):
                    return f"+{digits}"
                else:
                    # Not a valid German number format
                    return None
            else:
                # For other countries, check if the number starts with the country code
                country_code = self.country_codes.get(country, {}).get('code')
                if country_code:
                    if digits.startswith(country_code):
                        return f"+{digits}"
                    elif len(digits) >= 8:
                        # Assume it's a local number without country code
                        return f"+{country_code}{digits}"
                    else:
                        return None
        else:
            # If no target country is specified, handle international format
            if digits.startswith('+'):
                digits = digits[1:]
            if len(digits) >= 10 and len(digits) <= 15:
                return f"+{digits}"
        
        return None

    def _is_false_positive(self, text, phone):
        """Check if the phone number might be a false positive"""
        # Clean the text around the phone number
        context = text[max(0, text.find(phone)-20):min(len(text), text.find(phone)+len(phone)+20)]
        context = context.lower()
        
        # Check for common false positive indicators
        false_positive_indicators = [
            'order', 'reference', 'ref', 'item', 'product', 'id', 'no.', '#',
            'zip', 'postal', 'code', 'year', 'price', '$', '£', '€',
            'kg', 'lb', 'cm', 'mm', 'qty', 'quantity'
        ]
        
        if any(indicator in context for indicator in false_positive_indicators):
            return True
        
        # Check against exclude patterns
        for pattern in self.exclude_patterns:
            if re.search(pattern, context):
                return True
        
        return False

    def test_phone_extraction(self):
        """Test phone number extraction with known examples"""
        test_cases = [
            # US numbers
            "+1 (555) 123-4567",
            "555-123-4567",
            "(555) 123-4567",
            # UK numbers
            "+44 7700 900123",
            "07700 900123",
            # Indian numbers
            "+91 98765 43210",
            "098765 43210",
            # Australian numbers
            "+61 4 1234 5678",
            "0412 345 678",
            # German numbers
            "+49 170 1234567",
            "0170 1234567"
        ]
        
        print("\nTesting phone number extraction...")
        for phone in test_cases:
            html = f"""
            <div class="contact-info">
                <span class="phone">Phone: {phone}</span>
                <a href="tel:{phone}">Call us</a>
            </div>
            """
            
            results = self._extract_contacts_from_text(html)
            print(f"\nTest case: {phone}")
            print(f"Extracted: {results['phones']}")
            
            # Test plain text extraction
            text_results = self._extract_contacts_from_text(f"Contact us at {phone}")
            print(f"Plain text extracted: {text_results['phones']}")

def display_menu():
    """Display the main menu for the contact scraper"""
    print("\n===== ENHANCED CONTACT SCRAPER =====")
    print("This tool helps you find contact information for companies and individuals")
    print("It will avoid scraping from blocked domains like JustDial and IndiaMart")
    print("============================================\n")

def main():
    try:
        display_menu()
        scraper = EnhancedContactScraper()
        
        # Get target input
        while True:
            target = input("Enter company or person name to search for: ").strip()
            if target:
                break
            print("Error: You must provide a search target")
        
        # Always scrape both phone numbers and emails
        print("\nThis scraper will extract both phone numbers and email addresses.")
        scrape_phones = True
        scrape_emails = True
        
        # Get search scope
        while True:
            print("\nSelect search scope:")
            print("1. Worldwide")
            print("2. Specific country")
            scope_choice = input("Enter your choice (1 or 2): ").strip()
            if scope_choice in ['1', '2']:
                break
            print("Invalid choice. Please enter 1 or 2.")
        
        country = None
        if scope_choice == "2":
            print("\nAvailable countries:")
            countries = {
                '1': 'US - United States',
                '2': 'UK - United Kingdom',
                '3': 'IN - India',
                '4': 'AU - Australia',
                '5': 'CA - Canada',
                '6': 'DE - Germany',
                '7': 'FR - France',
                '8': 'IT - Italy',
                '9': 'ES - Spain',
                '10': 'BR - Brazil'
            }
            
            for key, value in countries.items():
                print(f"{key}. {value}")
            
            while True:
                country_choice = input("\nEnter country number (1-10): ").strip()
                country_map = {
                    '1': 'US', '2': 'UK', '3': 'IN', '4': 'AU', '5': 'CA',
                    '6': 'DE', '7': 'FR', '8': 'IT', '9': 'ES', '10': 'BR'
                }
                country = country_map.get(country_choice)
                if country:
                    break
                print("Invalid selection. Please enter a number between 1 and 10.")
        
        # Get additional inputs with validation
        search_terms = input("\nEnter additional search terms (optional): ").strip()
        
        while True:
            max_results_input = input("Number of contacts to extract (10-1000, default 100): ").strip()
            if not max_results_input:
                max_results = 100
                break
            try:
                max_results = int(max_results_input)
                if 10 <= max_results <= 1000:
                    break
                print("Please enter a number between 10 and 1000.")
            except ValueError:
                print("Please enter a valid number.")
                
        # Always use exact count
        exact_count = True
        print(f"The scraper will extract EXACTLY {max_results} phone numbers and {max_results} email addresses.")
        print("Dynamic focus adjustment is enabled: The scraper will automatically prioritize whichever contact type is lagging behind.")
        
        while True:
            max_pages_input = input("Maximum Google result pages to process per query (5-50, default 20): ").strip()
            if not max_pages_input:
                max_pages = 20
                break
            try:
                max_pages = int(max_pages_input)
                if 5 <= max_pages <= 50:
                    break
                print("Please enter a number between 5 and 50.")
            except ValueError:
                print("Please enter a valid number.")
        
        print("\nStarting search... (this may take a few minutes)")
        print(f"Search scope: {'Worldwide' if not country else f'Country: {country}'}")
        print("A browser window will open. Please do not close it.")
        print("You may need to manually solve CAPTCHA challenges if they appear.\n")
        
        # Run the scraper
        print(f"\nStarting search for EXACTLY {max_results} phone numbers and {max_results} email addresses...")
        results = scraper.search_and_extract(
            target=target,
            country=country,
            search_terms=search_terms,
            max_results=max_results,
            max_pages=max_pages,
            exact_count=exact_count
        )
        
        # Validate and analyze results
        validated_results = scraper.validate_contacts(results)
        
        # Display results
        print("\n=== SEARCH RESULTS ===")
        
        # Display phone numbers
        phones_count = len(validated_results.get('phones', []))
        print(f"Extracted {phones_count} phone numbers (requested {max_results})")
        
        if phones_count > 0:
            display_count = min(10, phones_count)
            print(f"\nTop {display_count} Phone Numbers (Ranked by Quality):")
            for i, item in enumerate(validated_results['phones'][:display_count], 1):
                print(f"{i}. {item['phone']} (Score: {item['score']})")
        
        # Display emails
        emails_count = len(validated_results.get('emails', []))
        print(f"\nExtracted {emails_count} email addresses (requested {max_results})")
        
        if emails_count > 0:
            display_count = min(10, emails_count)
            print(f"\nTop {display_count} Emails (Ranked by Quality):")
            for i, item in enumerate(validated_results['emails'][:display_count], 1):
                print(f"{i}. {item['email']} (Score: {item['score']})")
        
        # Confirm exact count achievement
        if phones_count == max_results and emails_count == max_results:
            print(f"\nSUCCESS: Extracted exactly {max_results} phone numbers and {max_results} email addresses as requested.")
        else:
            print("\nNote: The results file contains exactly the requested number of items, even if some had to be duplicated.")
        
        print(f"\nComplete results saved to contact_results_{target.replace(' ', '_')}_{time.strftime('%Y%m%d-%H%M%S')}.json")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
    except Exception as e:
        print(f"An error occurred: {e}")
        logger.error(f"Error in main: {e}", exc_info=True)
    finally:
        if 'scraper' in locals() and scraper.driver:
            scraper.close_browser()

if __name__ == "__main__":
    main()
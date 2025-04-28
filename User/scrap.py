import requests
from bs4 import BeautifulSoup
import re
import csv
import time
import random
import concurrent.futures
import os
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import sys

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("web_scraper")

class WebScraper:
    def __init__(self):
        self.all_contacts = set()
        self.setup_selenium()
        
    def setup_selenium(self):
        """Set up the Selenium WebDriver with appropriate options."""
        print("Setting up the WebDriver... This may take a moment.")
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-notifications")
            
            # Use webdriver_manager to handle driver installation automatically
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            print("WebDriver set up successfully.")
        except Exception as e:
            print(f"Error setting up WebDriver: {e}")
            print("Attempting alternative setup...")
            try:
                # Simpler setup for environments with issues
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                self.driver = webdriver.Chrome(options=chrome_options)
                print("Alternative WebDriver set up successfully.")
            except Exception as e:
                print(f"Fatal error setting up WebDriver: {e}")
                print("Please make sure Chrome is installed and try again.")
                sys.exit(1)
    
    def get_random_header(self):
        """Generate random headers to avoid detection."""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0'
        ]
        
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.google.com/',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
    
    def extract_phone_numbers(self, text):
        """Extract valid Indian phone numbers from text."""
        # Pattern for Indian mobile numbers (supports multiple formats)
        patterns = [
            r'\+91\s?[6-9]\d{9}',  # +91 followed by 10 digits
            r'0?[6-9]\d{9}',       # Optional 0 followed by 10 digits
            r'[6-9]\d{9}'          # 10 digits starting with 6-9
        ]
        
        phone_numbers = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            phone_numbers.extend(matches)
            
        # Clean up numbers to standard format
        cleaned_numbers = []
        for num in phone_numbers:
            # Remove spaces, hyphens, etc.
            clean_num = re.sub(r'[^0-9+]', '', num)
            
            # Ensure all numbers are in +91 format
            if clean_num.startswith('+91'):
                cleaned_numbers.append(clean_num)
            elif clean_num.startswith('91') and len(clean_num) == 12:
                cleaned_numbers.append('+' + clean_num)
            elif len(clean_num) == 10 and clean_num[0] in '6789':
                cleaned_numbers.append('+91' + clean_num)
            elif len(clean_num) == 11 and clean_num[0] == '0' and clean_num[1] in '6789':
                cleaned_numbers.append('+91' + clean_num[1:])
                
        return cleaned_numbers
    
    def random_delay(self, min_sec=1, max_sec=3):
        """Add random delay between requests to avoid detection."""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
    
    def scrape_indiamart(self, state, city, keyword, min_contacts=70):
        """Scrape contact information from IndiaMart."""
        logger.info(f"Scraping IndiaMart for {keyword} in {city}, {state}")
        print(f"\nSearching IndiaMart for {keyword} in {city}, {state}...")
        contacts = set()
        page = 1
        max_pages = 20  # Increased max pages
        search_variations = [
            f"{keyword} in {city} {state}",
            f"{keyword} {city}",
            f"{keyword} {state}",
            f"{keyword} suppliers {city}",
            f"{keyword} dealers"
        ]
        
        current_variation_index = 0
        
        while len(contacts) < min_contacts and page <= max_pages:
            try:
                # Try different search variations if we're not finding results
                if page > 5 and len(contacts) < 10:
                    current_variation_index = (current_variation_index + 1) % len(search_variations)
                    page = 1
                    print(f"Trying alternative search: {search_variations[current_variation_index]}")
                
                # Construct the search URL
                search_query = search_variations[current_variation_index]
                url = f"https://dir.indiamart.com/search.mp?ss={search_query.replace(' ', '+')}&pagenum={page}"
                
                headers = self.get_random_header()
                response = requests.get(url, headers=headers, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Find all company listings
                    listings = soup.find_all(['div', 'li'], class_=['prd-card', 'listing'])
                    
                    if not listings:
                        print(f"No listings found on page {page} of IndiaMart with current search variation")
                        
                        # Try alternative classes/selectors
                        alternative_listings = soup.find_all(['div'], class_=['product-detail'])
                        if alternative_listings:
                            listings = alternative_listings
                            print(f"Found {len(listings)} listings with alternative selector")
                    
                    if not listings:
                        # If still no listings, try the next search variation
                        current_variation_index = (current_variation_index + 1) % len(search_variations)
                        page = 1
                        print(f"Trying alternative search: {search_variations[current_variation_index]}")
                        continue
                    
                    print(f"Processing {len(listings)} listings on page {page}")
                    for listing in listings:
                        try:
                            # Extract ALL text from the listing
                            listing_text = listing.get_text()
                            phone_numbers = self.extract_phone_numbers(listing_text)
                            contacts.update(phone_numbers)
                            
                            # Look for links to contact pages
                            for link in listing.find_all('a'):
                                href = link.get('href', '')
                                if 'contact' in href.lower() or 'profile' in href.lower():
                                    try:
                                        self.random_delay()
                                        contact_response = requests.get(href, headers=self.get_random_header(), timeout=10)
                                        if contact_response.status_code == 200:
                                            contact_soup = BeautifulSoup(contact_response.text, 'html.parser')
                                            phone_numbers = self.extract_phone_numbers(contact_soup.text)
                                            contacts.update(phone_numbers)
                                    except Exception as e:
                                        logger.debug(f"Error fetching contact page: {e}")
                            
                        except Exception as e:
                            logger.error(f"Error processing IndiaMart listing: {e}")
                
                # Go to next page
                page += 1
                print(f"IndiaMart: Collected {len(contacts)} contacts so far. Moving to page {page}.")
                self.random_delay(2, 4)
                
            except Exception as e:
                logger.error(f"Error scraping IndiaMart page {page}: {e}")
                page += 1  # Still try the next page
                self.random_delay(3, 6)  # Longer delay after an error
        
        logger.info(f"Completed IndiaMart scraping. Total contacts collected: {len(contacts)}")
        print(f"Finished IndiaMart search with {len(contacts)} contacts found.")
        return contacts
    
    def decode_justdial_number(self, soup_content):
        """Decode JustDial's obfuscated phone numbers."""
        # JustDial uses CSS classes to hide the actual numbers
        mapping = {
            'icon-ji': '9', 'icon-dc': '0', 'icon-fe': '1', 'icon-hg': '2',
            'icon-ba': '3', 'icon-lk': '4', 'icon-nm': '5', 'icon-po': '6',
            'icon-rq': '7', 'icon-ts': '8',
            # Additional mappings (JustDial sometimes changes these)
            'icon-acb': '0', 'icon-yz': '1', 'icon-wx': '2', 'icon-vu': '3',
            'icon-ts': '4', 'icon-rq': '5', 'icon-po': '6', 'icon-nm': '7',
            'icon-lk': '8', 'icon-ji': '9'
        }
        
        # Find all elements with these special classes
        phone_spans = soup_content.select('span[class*="icon-"]')
        
        decoded = ''
        for span in phone_spans:
            for cls in span.get('class', []):
                if cls in mapping:
                    decoded += mapping[cls]
                    break
        
        # Make sure it's a valid number
        if len(decoded) >= 10:
            return '+91' + decoded[-10:]
        return None
    
    def scrape_justdial(self, state, city, keyword, min_contacts=70):
        """Scrape contact information from JustDial."""
        logger.info(f"Scraping JustDial for {keyword} in {city}, {state}")
        print(f"\nSearching JustDial for {keyword} in {city}, {state}...")
        contacts = set()
        page = 1
        max_pages = 20  # Increased max pages
        
        # Multiple search variations to try
        search_variations = [
            f"{keyword}-in-{city}",
            f"{keyword}-{city}",
            f"{keyword}-dealers-{city}",
            f"{keyword}-shops-{city}",
            f"{keyword}-{state}"
        ]
        
        current_variation_index = 0
        consecutive_failures = 0
        
        while len(contacts) < min_contacts and page <= max_pages and consecutive_failures < 5:
            try:
                # Try different search variations if we're not finding results
                if page > 5 and len(contacts) < 10:
                    current_variation_index = (current_variation_index + 1) % len(search_variations)
                    page = 1
                    print(f"Trying alternative JustDial search: {search_variations[current_variation_index]}")
                
                # Construct the URL
                search_query = search_variations[current_variation_index]
                url = f"https://www.justdial.com/{city}/{search_query}/page-{page}"
                
                print(f"Accessing JustDial page: {url}")
                
                # Use Selenium to load the page (JustDial has JS protections)
                self.driver.get(url)
                
                # Wait for the page to load
                try:
                    WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "jsx-3349e7cd87e12d75"))
                    )
                except TimeoutException:
                    try:
                        # Try alternative selector
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "store-details"))
                        )
                    except TimeoutException:
                        # One more try with another selector
                        WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.CLASS_NAME, "jd-listing-title-section"))
                        )
                
                # Parse the page content
                soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                
                # Try to find listings with different potential selectors
                selectors = [
                    'li.jsx-3349e7cd87e12d75',
                    'div.store-details',
                    'div.jd-listing-title-section',
                    'section.suggestion',
                    'div.listing-card'
                ]
                
                listings = []
                for selector in selectors:
                    found_listings = soup.select(selector)
                    if found_listings:
                        listings = found_listings
                        print(f"Found {len(listings)} listings with selector: {selector}")
                        break
                
                if not listings:
                    print(f"No listings found on page {page} with current search variation")
                    page += 1
                    consecutive_failures += 1
                    continue
                
                consecutive_failures = 0  # Reset failure counter if we found listings
                
                # Process the listings
                for listing in listings:
                    try:
                        # Try to decode JustDial's obfuscated numbers
                        decoded_number = self.decode_justdial_number(listing)
                        if decoded_number:
                            contacts.add(decoded_number)
                        
                        # Also look for regular numbers in the text
                        listing_text = listing.get_text()
                        phone_numbers = self.extract_phone_numbers(listing_text)
                        contacts.update(phone_numbers)
                        
                        # Try to find and click "show number" buttons
                        try:
                            show_buttons = self.driver.find_elements(By.XPATH, "//span[contains(text(), 'Show Number')]")
                            for button in show_buttons[:3]:  # Limit to first 3 buttons to avoid too many clicks
                                if button.is_displayed():
                                    self.driver.execute_script("arguments[0].click();", button)
                                    time.sleep(2)  # Wait for number to display
                                    
                                    # Get updated page source after clicking
                                    updated_soup = BeautifulSoup(self.driver.page_source, 'html.parser')
                                    
                                    # Look for revealed phone numbers
                                    phone_containers = updated_soup.select('.jsx-3349e7cd87e12d75 p.contact-info')
                                    for container in phone_containers:
                                        number = self.extract_phone_numbers(container.get_text())
                                        contacts.update(number)
                        except Exception as e:
                            logger.debug(f"Error clicking 'Show Number' button: {e}")
                    
                    except Exception as e:
                        logger.error(f"Error processing JustDial listing: {e}")
                
                # Go to next page
                page += 1
                print(f"JustDial: Collected {len(contacts)} contacts so far. Moving to page {page}.")
                self.random_delay(2, 5)
                
            except Exception as e:
                logger.error(f"Error scraping JustDial page {page}: {e}")
                consecutive_failures += 1
                page += 1
                self.random_delay(3, 6)  # Longer delay after an error
        
        logger.info(f"Completed JustDial scraping. Total contacts collected: {len(contacts)}")
        print(f"Finished JustDial search with {len(contacts)} contacts found.")
        return contacts
    
    def scrape_instagram(self, state, city, keyword, min_contacts=60):
        """Scrape contact information from Instagram business profiles."""
        logger.info(f"Scraping Instagram for {keyword} in {city}, {state}")
        print(f"\nSearching Instagram for {keyword} in {city}, {state}...")
        contacts = set()
        
        # Multiple search hashtags to try
        hashtags = [
            keyword.replace(" ", ""),
            f"{keyword.replace(' ', '')}{city.replace(' ', '')}",
            f"{city.replace(' ', '')}{keyword.replace(' ', '')}",
            f"{keyword.replace(' ', '')}india",
            f"shop{keyword.replace(' ', '')}"
        ]
        
        profile_links = set()
        
        for hashtag in hashtags:
            try:
                # Search for the hashtag
                print(f"Searching Instagram hashtag: #{hashtag}")
                self.driver.get(f"https://www.instagram.com/explore/tags/{hashtag}/")
                
                # Wait for page to load
                time.sleep(5)
                
                # Handle potential login popups
                try:
                    # Click "Not Now" on login prompts
                    not_now_buttons = self.driver.find_elements(By.XPATH, 
                                                            "//button[contains(text(), 'Not Now') or contains(text(), 'not now')]")
                    if not_now_buttons:
                        for button in not_now_buttons:
                            if button.is_displayed():
                                button.click()
                                time.sleep(1)
                except Exception:
                    pass
                
                # Scroll down to load more content
                for _ in range(5):
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)
                
                # Get all post links
                post_elements = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/p/')]")
                post_links = []
                
                for element in post_elements[:30]:  # Limit to first 30 posts
                    try:
                        href = element.get_attribute('href')
                        if href and href not in post_links:
                            post_links.append(href)
                    except Exception:
                        continue
                
                print(f"Found {len(post_links)} posts for #{hashtag}")
                
                # Visit posts to extract profile links
                for post_link in post_links[:15]:  # Limit to first 15 posts
                    try:
                        self.driver.get(post_link)
                        time.sleep(3)
                        
                        # Try to get profile link
                        try:
                            profile_elements = self.driver.find_elements(By.XPATH, "//a[contains(@class, 'notranslate')]")
                            for element in profile_elements:
                                href = element.get_attribute('href')
                                if href and 'instagram.com/' in href and '/p/' not in href:
                                    profile_links.add(href)
                        except Exception:
                            pass
                        
                        # Also look for business info in the post itself
                        page_source = self.driver.page_source
                        phone_numbers = self.extract_phone_numbers(page_source)
                        contacts.update(phone_numbers)
                        
                    except Exception as e:
                        logger.debug(f"Error processing Instagram post: {e}")
                
                # If we have enough profiles or contacts, we can break
                if len(profile_links) >= 20 or len(contacts) >= min_contacts:
                    break
                    
            except Exception as e:
                logger.error(f"Error during Instagram hashtag search: {e}")
        
        print(f"Found {len(profile_links)} Instagram profiles to check")
        
        # Visit each profile to look for contact info
        for profile_link in profile_links:
            try:
                self.driver.get(profile_link)
                time.sleep(3)
                
                # Check bio for phone numbers
                page_source = self.driver.page_source
                phone_numbers = self.extract_phone_numbers(page_source)
                contacts.update(phone_numbers)
                
                # Look for contact/email buttons
                try:
                    contact_elements = self.driver.find_elements(By.XPATH, 
                                                            "//*[contains(text(), 'Contact') or contains(text(), 'Email') or contains(text(), 'Call')]")
                    for element in contact_elements:
                        if element.is_displayed():
                            try:
                                element.click()
                                time.sleep(2)
                                
                                # Check for phone numbers after clicking
                                updated_source = self.driver.page_source
                                new_numbers = self.extract_phone_numbers(updated_source)
                                contacts.update(new_numbers)
                            except Exception:
                                pass
                except Exception:
                    pass
                
                # If we have enough contacts, we can break
                if len(contacts) >= min_contacts:
                    break
                
                self.random_delay(2, 4)
                
            except Exception as e:
                logger.error(f"Error processing Instagram profile: {e}")
        
        logger.info(f"Completed Instagram scraping. Total contacts collected: {len(contacts)}")
        print(f"Finished Instagram search with {len(contacts)} contacts found.")
        return contacts
    
    def scrape_all_sources(self, state, city, keyword, target_contacts=200):
        """Scrape all sources using concurrent execution."""
        logger.info(f"Starting to scrape data for {keyword} in {city}, {state}")
        print(f"\n{'='*60}")
        print(f"  Starting data collection for {keyword} in {city}, {state}")
        print(f"  Target: {target_contacts} contacts")
        print(f"{'='*60}\n")
        
        # Allocate contacts per source based on target
        per_source_target = max(70, target_contacts // 3)
        
        # Use ThreadPoolExecutor to run scrapers concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit scraping tasks
            indiamart_future = executor.submit(self.scrape_indiamart, state, city, keyword, per_source_target)
            justdial_future = executor.submit(self.scrape_justdial, state, city, keyword, per_source_target)
            instagram_future = executor.submit(self.scrape_instagram, state, city, keyword, per_source_target)
            
            # Track which tasks have completed
            completed_sources = []
            
            # Get results as they complete
            for future in concurrent.futures.as_completed([indiamart_future, justdial_future, instagram_future]):
                try:
                    source_name = ""
                    if future == indiamart_future:
                        source_name = "IndiaMart"
                    elif future == justdial_future:
                        source_name = "JustDial"
                    elif future == instagram_future:
                        source_name = "Instagram"
                    
                    contacts = future.result()
                    completed_sources.append(source_name)
                    
                    self.all_contacts.update(contacts)
                    print(f"\n{source_name} search completed with {len(contacts)} contacts")
                    print(f"Current total unique contacts: {len(self.all_contacts)}")
                    
                except Exception as e:
                    logger.error(f"Error in scraper execution: {e}")
        
        # If we don't have enough contacts, try additional sources or variations
        if len(self.all_contacts) < target_contacts:
            print(f"\nStill need {target_contacts - len(self.all_contacts)} more contacts. Trying additional searches...")
            
            # Try general business directories, Yellow Pages, etc.
            try:
                additional_contacts = self.scrape_additional_sources(state, city, keyword)
                self.all_contacts.update(additional_contacts)
                print(f"Found {len(additional_contacts)} additional contacts")
            except Exception as e:
                logger.error(f"Error in additional scraping: {e}")
        
        # Close the Selenium driver
        print("\nClosing WebDriver...")
        self.driver.quit()
        
        result_contacts = list(self.all_contacts)
        print(f"\n{'='*60}")
        print(f"  Data collection completed!")
        print(f"  Total contacts found: {len(result_contacts)}")
        print(f"{'='*60}\n")
        
        return result_contacts
    
    def scrape_additional_sources(self, state, city, keyword):
        """Scrape additional sources if main sources didn't provide enough contacts."""
        contacts = set()
        
        # Try Yellow Pages India
        try:
            print("Searching Yellow Pages India...")
            url = f"https://www.yellowpages.co.in/search/{city}/{keyword}"
            
            self.driver.get(url)
            time.sleep(3)
            
            # Extract contact information
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Process listings
            listings = soup.select('.listing-wrap')
            for listing in listings:
                contact_text = listing.get_text()
                phone_numbers = self.extract_phone_numbers(contact_text)
                contacts.update(phone_numbers)
                
            print(f"Found {len(contacts)} contacts from Yellow Pages")
        except Exception as e:
            logger.error(f"Error scraping Yellow Pages: {e}")
        
        # Try Tradeindia.com
        try:
            print("Searching TradeIndia...")
            url = f"https://www.tradeindia.com/{keyword.replace(' ', '-')}/in/{city.replace(' ', '-')}/"
            
            self.driver.get(url)
            time.sleep(3)
            
            # Extract contact information
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Process listings
            listings = soup.select('.supplier-products')
            for listing in listings:
                contact_text = listing.get_text()
                phone_numbers = self.extract_phone_numbers(contact_text)
                contacts.update(phone_numbers)
                
            print(f"Found {len(contacts)} contacts from TradeIndia")
        except Exception as e:
            logger.error(f"Error scraping TradeIndia: {e}")
        
        return contacts
    
    def export_to_csv(self, contacts, state, city, keyword):
        """Export collected contacts to CSV file."""
        if not contacts:
            logger.warning("No contacts to export")
            return "No contacts found to export"
        
        filename = f"{keyword}_{city}_{state}_{len(contacts)}_contacts.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Phone Number'])
            for contact in contacts:
                writer.writerow([contact])
        
        logger.info(f"Exported {len(contacts)} contacts to {filename}")
        return filename

def main():
    print("\n" + "="*80)
    print("                    WEB SCRAPER FOR BUSINESS CONTACTS")
    print("="*80 + "\n")
    
    # Get user input
    print("Please provide the following information for your search:")
    state = input("State (e.g. Maharashtra, Gujarat): ").strip()
    city = input("City (e.g. Mumbai, Ahmedabad): ").strip()
    keyword = input("Keyword/Business type (e.g. furniture, restaurants): ").strip()
    
    try:
        target_contacts = int(input("Number of contacts to collect [default: 200]: ").strip() or "200")
    except ValueError:
        target_contacts = 200
        print("Invalid number, using default: 200 contacts")
    
    print("\nInitializing scraper and starting search. This may take some time...")
    print("(The program will continue running until it finds enough contacts or exhausts all sources)")
    
    # Initialize scraper
    scraper = WebScraper()
    
    # Run the scrapers
    contacts = scraper.scrape_all_sources(state, city, keyword, target_contacts)
    
    # Export results
    if contacts:
        csv_file = scraper.export_to_csv(contacts, state, city, keyword)
        print(f"\nScraping completed! Found {len(contacts)} unique contacts.")
        print(f"Results saved to {csv_file}")
        
        # Show sample of the data
        print("\nSample data (first 5 contacts):")
        for contact in contacts[:5]:
            print(f"  {contact}")
        print("...")
    else:
        print("\nNo contacts found. Please try different search parameters.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nProcess interrupted by user. Exiting...")
    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")
        print("Please try again with different search parameters or check your internet connection.")
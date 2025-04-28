import requests
from bs4 import BeautifulSoup
import re
import time
import random
import json
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from concurrent.futures import ThreadPoolExecutor

class ContactScraper:
    def __init__(self):
        self.email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        self.phone_pattern = r'(?:\+?\d{1,4}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
        self.results = {
            'emails': set(),
            'phones': set()
        }
        self.driver = None
        self.session = requests.Session()

    def initialize_browser(self):
        try:
            options = Options()
            options.add_argument("--headless")  # Run in headless mode
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-notifications")
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            return True
        except Exception as e:
            logging.error(f"Failed to initialize browser: {e}")
            return False

    def close_browser(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass

    def _extract_contacts(self, text, data_type='both'):
        results = {'emails': set(), 'phones': set()}
        
        if data_type in ['both', 'email']:
            emails = re.findall(self.email_pattern, text)
            results['emails'].update(email.lower() for email in emails if self._is_valid_email(email))
            
        if data_type in ['both', 'phone']:
            phones = re.findall(self.phone_pattern, text)
            results['phones'].update(phone for phone in phones if self._is_valid_phone(phone))
            
        return results

    def _is_valid_email(self, email):
        if not email:
            return False
        email = email.lower().strip()
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            return False
        return True

    def _is_valid_phone(self, phone):
        if not phone:
            return False
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 10 or len(digits) > 15:
            return False
        return True

    def scrape_contacts(self, target, data_type='both', max_results=30):
        if not self.initialize_browser():
            return {'error': 'Failed to initialize browser'}

        try:
            # Craft search queries
            search_queries = []
            if data_type in ['both', 'phone']:
                search_queries.extend([
                    f"{target} contact phone number",
                    f"{target} mobile number contact"
                ])
            if data_type in ['both', 'email']:
                search_queries.extend([
                    f"{target} contact email address",
                    f"{target} email us"
                ])

            for query in search_queries:
                try:
                    # Perform Google search
                    self.driver.get(f"https://www.google.com/search?q={query}")
                    time.sleep(2)

                    # Extract results
                    results = self.driver.find_elements(By.CSS_SELECTOR, "div.g")
                    
                    for result in results:
                        # Extract text content
                        text = result.text
                        
                        # Extract contacts
                        contacts = self._extract_contacts(text, data_type)
                        
                        # Update results
                        if data_type in ['both', 'email']:
                            self.results['emails'].update(contacts['emails'])
                        if data_type in ['both', 'phone']:
                            self.results['phones'].update(contacts['phones'])

                        # Check if we have enough results
                        if (data_type == 'both' and 
                            len(self.results['emails']) >= max_results and 
                            len(self.results['phones']) >= max_results):
                            break
                        elif (data_type == 'email' and 
                              len(self.results['emails']) >= max_results):
                            break
                        elif (data_type == 'phone' and 
                              len(self.results['phones']) >= max_results):
                            break

                except Exception as e:
                    logging.error(f"Error processing search query: {e}")
                    continue

            # Prepare results
            final_results = {}
            if data_type in ['both', 'email']:
                final_results['emails'] = list(self.results['emails'])[:max_results]
            if data_type in ['both', 'phone']:
                final_results['phones'] = list(self.results['phones'])[:max_results]

            return final_results

        except Exception as e:
            logging.error(f"Error in scrape_contacts: {e}")
            return {'error': str(e)}
        finally:
            self.close_browser() 
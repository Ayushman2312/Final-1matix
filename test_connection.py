"""
Test script to verify ChromeDriver connection
"""

import os
import sys
import logging
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ConnectionTest")

def test_chrome_connection(headless=True, retries=3):
    """Test Chrome WebDriver connection with retries"""
    
    logger.info("Starting Chrome WebDriver connection test")
    
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Attempt {attempt}/{retries} to connect to ChromeDriver")
            
            # Setup Chrome options
            options = Options()
            if headless:
                options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            # Use ChromeDriverManager to handle driver installation
            logger.info("Installing/finding ChromeDriver with webdriver_manager")
            service = Service(ChromeDriverManager().install())
            
            # Initialize the driver
            logger.info("Initializing Chrome WebDriver")
            driver = webdriver.Chrome(service=service, options=options)
            
            # Test navigation
            logger.info("Testing navigation to google.com")
            driver.get("https://www.google.com")
            
            # Get page title
            title = driver.title
            logger.info(f"Successfully connected! Page title: {title}")
            
            # Clean up
            driver.quit()
            logger.info("Test completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error during test (attempt {attempt}/{retries}): {e}")
            
            if attempt < retries:
                wait_time = 2 ** attempt  # Exponential backoff
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
            else:
                logger.error("All connection attempts failed")
                return False

def check_system_info():
    """Check and log system information"""
    
    logger.info("=== System Information ===")
    
    # Check Python version
    logger.info(f"Python version: {sys.version}")
    
    # Check operating system
    logger.info(f"Operating system: {sys.platform}")
    
    # Check if Chrome is installed
    chrome_paths = [
        # Windows
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        # MacOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        # Linux
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable"
    ]
    
    chrome_found = False
    for path in chrome_paths:
        if os.path.exists(path):
            logger.info(f"Chrome found at: {path}")
            chrome_found = True
            break
    
    if not chrome_found:
        logger.warning("Chrome not found in common locations")
    
    # Check if ChromeDriver is in PATH
    try:
        import subprocess
        result = subprocess.run(["where", "chromedriver"] if sys.platform == "win32" else ["which", "chromedriver"], 
                               capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"ChromeDriver found in PATH: {result.stdout.strip()}")
        else:
            logger.info("ChromeDriver not found in PATH (will be installed by webdriver_manager)")
    except Exception as e:
        logger.warning(f"Could not check for ChromeDriver in PATH: {e}")

if __name__ == "__main__":
    # Check system information
    check_system_info()
    
    # Test connection
    success = test_chrome_connection(headless=True, retries=3)
    
    if success:
        print("\n✅ Connection test successful! The ChromeDriver is working properly.")
    else:
        print("\n❌ Connection test failed. Please check the logs for details.")
        sys.exit(1) 
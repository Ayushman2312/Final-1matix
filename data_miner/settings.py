"""
Settings for the data_miner app. This file is loaded by Django when the app is imported.
"""

# SerpAPI Key
SERPAPI_KEY = "934b601b0908067948a53616306c790179658a297a2e103379a55d09e7b75a7c"

# Google Gemini API Key - Replace with your own key
GEMINI_API_KEY = 'AIzaSyDsXH-_ftI5xn4aWfkwpw__4ixUMs7a7fM'

# Scraping configurations
DEFAULT_MAX_RESULTS = 50
DEFAULT_MAX_PAGES = 5
DEFAULT_TIMEOUT = 10  # seconds per request

# Rate limiting for scraping to avoid IP blocks
SCRAPING_DELAY = 1  # seconds between requests
MAX_RETRIES = 3  # maximum number of retries for failed requests

# Validation settings
MIN_PHONE_LENGTH = 8  # minimum length for a valid phone number
MAX_DOMAIN_LENGTH = 50  # maximum length for a valid email domain 
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
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging
import re

# Configure logging
logger = logging.getLogger(__name__)

# --------- User Input Function ---------
def get_user_input():
    print("\n===== Google Trends Analyzer =====")
    print("This tool fetches real-time Google Trends data for keywords you specify.")
    
    # Get keywords from user
    keywords_input = input("\nEnter keyword(s) to analyze (separate multiple keywords with commas): ")
    keywords_list = [k.strip() for k in keywords_input.split(',') if k.strip()]
    
    if not keywords_list:
        print("No valid keywords entered. Using default keyword.")
        keywords_list = ["Artificial Intelligence"]
    
    # Limit the number of keywords to reduce rate limiting
    if len(keywords_list) > 3:
        print(f"⚠️ Warning: Using more than 3 keywords may increase the chance of rate limiting.")
        proceed = input("Do you want to proceed with all keywords? (y/n) [Default: y]: ").strip().lower() or "y"
        if proceed != "y":
            # Ask user to select up to 3 keywords
            print("\nPlease select up to 3 keywords:")
            for i, keyword in enumerate(keywords_list[:5], 1):
                print(f"{i}. {keyword}")
            if len(keywords_list) > 5:
                print(f"...and {len(keywords_list) - 5} more")
            
            selected = input("Enter the numbers of keywords to keep (e.g., '1,3'): ").strip()
            try:
                selected_indices = [int(idx.strip()) - 1 for idx in selected.split(',') if idx.strip()]
                selected_keywords = [keywords_list[i] for i in selected_indices if 0 <= i < len(keywords_list)]
                if selected_keywords:
                    keywords_list = selected_keywords[:3]
                    print(f"Selected keywords: {', '.join(keywords_list)}")
                else:
                    print("No valid selection. Using the first 3 keywords.")
                    keywords_list = keywords_list[:3]
            except (ValueError, IndexError):
                print("Invalid selection. Using the first 3 keywords.")
                keywords_list = keywords_list[:3]
    
    # Get timeframe from user (with default option)
    print("\nTimeframe options:")
    print("1. Last 24 hours (real-time)")
    print("2. Last 7 days")
    print("3. Last 30 days")
    print("4. Last 90 days")
    print("5. Last 12 months")
    print("6. Last 5 years")
    
    timeframe_choice = input("Choose timeframe (1-6) [Default: 6 for 5 years]: ").strip() or "6"
    
    timeframe_map = {
        "1": "now 1-d",
        "2": "now 7-d",
        "3": "today 1-m",
        "4": "today 3-m",
        "5": "today 12-m",
        "6": "today 5-y"
    }
    
    timeframe = timeframe_map.get(timeframe_choice, "now 1-d")
    
    # Warn about real-time data and rate limiting
    if timeframe == "now 1-d":
        print("\n⚠️ Note: Real-time data (last 24 hours) has a higher chance of rate limiting.")
        print("Consider using a longer timeframe if you encounter issues.")
    
    # Get region from user (with default option)
    geo_input = input("\nEnter region code (e.g., 'US' for USA, 'IN' for India) or leave blank for worldwide: ").strip()
    geo = geo_input.upper() if geo_input else ''
    
    # Get analysis type
    print("\nAnalysis options:")
    print("1. Time trends only (default)")
    print("2. Time trends + State/Province analysis")
    print("3. Time trends + City analysis")
    print("4. Complete analysis (Time trends + States + Cities + Related queries)")
    print("5. State/Province analysis only (faster)")
    print("6. City analysis only (faster)")
    
    analysis_choice = input("Choose analysis type (1-6) [Default: 1]: ").strip() or "1"
    
    # Create a dictionary to store analysis options
    analysis_options = {
        "include_time_trends": analysis_choice in ["1", "2", "3", "4"],
        "include_state_analysis": analysis_choice in ["2", "4", "5"],
        "include_city_analysis": analysis_choice in ["3", "4", "6"],
        "include_related_queries": analysis_choice == "4",
        "state_only": analysis_choice == "5",
        "city_only": analysis_choice == "6"
    }
    
    # Warn about comprehensive analysis and rate limiting
    if analysis_choice == "4":
        print("\n⚠️ Note: Complete analysis makes multiple API requests and has a higher chance of rate limiting.")
        print("The script will add delays between requests to minimize this risk.")
    
    # Provide information about the faster options
    if analysis_choice in ["5", "6"]:
        print("\n✅ You've selected a focused analysis option which is faster and less prone to rate limiting.")
        print("This option skips time trends data and focuses only on geographic data.")
    
    # Ask about using a proxy (optional)
    use_proxy = input("\nDo you want to use a proxy to avoid rate limiting? (y/n) [Default: n]: ").strip().lower() or "n"
    
    proxy_info = None
    if use_proxy == "y":
        proxy_host = input("Enter proxy host (e.g., '123.45.67.89'): ").strip()
        proxy_port = input("Enter proxy port (e.g., '8080'): ").strip()
        proxy_user = input("Enter proxy username (optional): ").strip()
        proxy_pass = input("Enter proxy password (optional): ").strip()
        
        if proxy_host and proxy_port:
            if proxy_user and proxy_pass:
                proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
            else:
                proxy_url = f"http://{proxy_host}:{proxy_port}"
            
            proxy_info = {
                "http": proxy_url,
                "https": proxy_url
            }
            print("Proxy configured successfully.")
        else:
            print("Invalid proxy information. Proceeding without proxy.")
    
    return keywords_list, timeframe, geo, analysis_options, proxy_info

# --------- Configuration ---------
# These will be overridden by user input
keywords = ["Artificial Intelligence"]
timeframe = 'now 1-d'  # Real-time data for the last 24 hours
geo = ''  # Empty means worldwide; 'IN' = India, 'US' = USA, etc.

# --------- Create Retry Session ---------
def create_retry_session():
    try:
        # Try the new parameter name first (urllib3 >= 2.0)
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
    except TypeError:
        # Fall back to old parameter name (urllib3 < 2.0)
        retry_strategy = Retry(
            total=5,
            backoff_factor=2,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"]
        )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session = requests.Session()
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

# Function to add random delay to avoid rate limiting
def add_random_delay(min_seconds=10, max_seconds=30):
    # Using higher default values to reduce chance of rate limiting
    delay = random.uniform(min_seconds, max_seconds)
    logger.debug(f"Waiting {delay:.2f} seconds before request...")
    time.sleep(delay)
    
# Function to implement exponential backoff with jitter for rate limiting
def backoff_with_jitter(attempt, base_delay=30, max_delay=300):
    # Calculate exponential backoff
    delay = min(base_delay * (2 ** attempt), max_delay)
    # Add jitter (random variation) to avoid thundering herd problem
    jitter = random.uniform(0, 0.3 * delay)
    final_delay = delay + jitter
    logger.warning(f"Rate limited. Implementing backoff strategy. Waiting {final_delay:.2f} seconds before retry...")
    time.sleep(final_delay)
    return final_delay

# Function to manually get Google cookies to help avoid rate limiting
def get_google_cookies():
    try:
        logger.info("Fetching fresh Google cookies...")
        session = requests.Session()
        # Add headers to mimic a real browser
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        # Visit Google homepage to get cookies
        response = session.get("https://www.google.com", timeout=30)
        if response.status_code == 200:
            logger.info("Successfully obtained Google cookies.")
            return session.cookies
        else:
            logger.warning(f"Failed to get Google cookies. Status code: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error getting Google cookies: {str(e)}")
        return None

# Function to get interest over time data
def get_trends_data(pytrends, keywords, timeframe, geo, max_retries=5):
    # Increased max_retries from 3 to 5
    for attempt in range(max_retries):
        try:
            # Add random delay with increased wait time
            add_random_delay()
            
            # Build the payload for the request
            pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo=geo, gprop='')
            
            # Get the interest over time data
            df = pytrends.interest_over_time()
            
            # Check if we got data
            if df is not None and not df.empty:
                logger.info(f"Successfully retrieved data with {len(df)} data points")
                
                # For real-time data (24h), verify it's actually recent
                if timeframe == 'now 1-d':
                    latest_timestamp = df.index[-1]
                    time_diff = datetime.datetime.now() - latest_timestamp
                    if time_diff.total_seconds() > 3600:  # If data is more than 1 hour old
                        logger.warning("Data might not be real-time. Retrying...")
                        continue
                
                # For 5-year data, check if we have enough data points
                if timeframe == 'today 5-y' and len(df) < 200:  # Expecting weekly data for 5 years
                    logger.warning("Incomplete data for 5-year period. Retrying...")
                    continue
                    
                return df
            else:
                logger.warning("No data returned from Google Trends API")
                if attempt < max_retries - 1:
                    logger.info("Retrying with longer delay...")
                    add_random_delay(20, 45)  # Longer delay before retry
                    continue
                return df
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg and attempt < max_retries - 1:
                # Use our improved backoff strategy
                backoff_with_jitter(attempt)
                continue
            elif "quota" in error_msg.lower() and attempt < max_retries - 1:
                # Use longer backoff for quota issues
                backoff_with_jitter(attempt, base_delay=60, max_delay=600)
                continue
            else:
                logger.error(f"Error during data retrieval: {error_msg}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying ({attempt+1}/{max_retries})...")
                    backoff_with_jitter(attempt)
                    continue
                else:
                    logger.error("Maximum retry attempts reached. Please try again later.")
                    return None

# Function to get interest by region (states/provinces)
def get_interest_by_region(pytrends, keywords, timeframe, geo, resolution='REGION', max_retries=5):
    """
    Get interest by geographic regions (states/provinces)
    
    Parameters:
    - pytrends: PyTrends instance
    - keywords: List of keywords to search for
    - timeframe: Time period to analyze
    - geo: Country code (e.g., 'US', 'IN')
    - resolution: 'REGION' for states/provinces, 'CITY' for cities
    - max_retries: Number of retry attempts (increased from 3 to 5)
    
    Returns:
    - DataFrame with region data
    
    Note: For city data, it's recommended to use get_interest_by_city() instead
    as it has specific optimizations for city-level data.
    """
    # Use only the first keyword to reduce rate limiting
    if len(keywords) > 1:
        logger.warning(f"Using only the first keyword '{keywords[0]}' for {resolution.lower()} data to reduce rate limiting")
        keywords_to_use = [keywords[0]]
    else:
        keywords_to_use = keywords
        
    for attempt in range(max_retries):
        try:
            # Add longer random delay to avoid rate limiting
            add_random_delay(15, 45)  # Increased delay for geographic data
            
            # Build the payload for the request
            pytrends.build_payload(keywords_to_use, cat=0, timeframe=timeframe, geo=geo, gprop='')
            
            # Get interest by region with timeout
            if resolution == 'REGION':
                logger.info(f"Fetching {resolution.lower()} data (attempt {attempt+1}/{max_retries})...")
                df = pytrends.interest_by_region(resolution='REGION', inc_low_vol=True, inc_geo_code=True)
            else:  # CITY
                logger.info(f"Fetching city data (attempt {attempt+1}/{max_retries})...")
                # Make sure we're explicitly setting resolution to 'CITY'
                df = pytrends.interest_by_region(resolution='CITY', inc_low_vol=True, inc_geo_code=True)
                
                # Verify we got city data, not region data
                if df is not None and not df.empty:
                    # Check if the index contains city names (usually contains commas for cities)
                    city_data_detected = any(',' in str(idx) for idx in df.index)
                    if not city_data_detected:
                        logger.warning("Received data may not be city-level. Retrying with modified parameters...")
                        # Add a longer delay before retry
                        add_random_delay(20, 60)
                        # Try again with a different approach - rebuild payload with explicit city focus
                        pytrends.build_payload(keywords_to_use, cat=0, timeframe=timeframe, geo=geo, gprop='')
                        # Force city resolution again
                        df = pytrends.interest_by_region(resolution='CITY', inc_low_vol=True, inc_geo_code=True)
            
            # Check if we got data
            if df is not None and not df.empty:
                logger.info(f"Successfully retrieved {resolution.lower()} data with {len(df)} regions")
                
                # If we only used the first keyword but had multiple keywords,
                # create empty columns for the other keywords to maintain consistency
                if len(keywords) > 1 and len(keywords_to_use) == 1:
                    for k in keywords[1:]:
                        df[k] = 0
                
                return df
            else:
                logger.warning(f"No {resolution.lower()} data returned from Google Trends API")
                if attempt < max_retries - 1:
                    logger.info("Retrying with longer delay...")
                    add_random_delay(30, 60)  # Even longer delay before retry
                    continue
                return df
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg and attempt < max_retries - 1:
                # Use our improved backoff strategy with longer delays
                backoff_with_jitter(attempt, base_delay=60, max_delay=600)
                continue
            elif "quota" in error_msg.lower() and attempt < max_retries - 1:
                # Use longer backoff for quota issues
                backoff_with_jitter(attempt, base_delay=90, max_delay=900)
                continue
            elif "timeout" in error_msg.lower() and attempt < max_retries - 1:
                logger.warning(f"Request timed out. Retrying with longer timeout...")
                backoff_with_jitter(attempt)
                continue
            else:
                logger.error(f"Error during {resolution.lower()} data retrieval: {error_msg}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying ({attempt+1}/{max_retries})...")
                    backoff_with_jitter(attempt)
                    continue
                else:
                    logger.error(f"Maximum retry attempts reached for {resolution.lower()} data. Skipping this part of the analysis.")
                    return None

# Function to get related queries
def get_related_queries(pytrends, keywords, timeframe, geo, max_retries=5):
    """Get related queries for the given keywords"""
    for attempt in range(max_retries):
        try:
            # Add random delay to avoid rate limiting
            add_random_delay()
            
            # Build the payload for the request
            pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo=geo, gprop='')
            
            # Get related queries
            related_queries = pytrends.related_queries()
            
            if related_queries:
                print(f"✅ Successfully retrieved related queries data")
                return related_queries
            else:
                print(f"⚠️ No related queries data returned")
                if attempt < max_retries - 1:
                    print("Retrying with longer delay...")
                    add_random_delay(20, 45)  # Longer delay before retry
                    continue
                return None
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg and attempt < max_retries - 1:
                # Use our improved backoff strategy
                backoff_with_jitter(attempt)
                continue
            elif "quota" in error_msg.lower() and attempt < max_retries - 1:
                # Use longer backoff for quota issues
                backoff_with_jitter(attempt, base_delay=60, max_delay=600)
                continue
            else:
                print(f"❌ Error during related queries retrieval: {error_msg}")
                if attempt < max_retries - 1:
                    print(f"Retrying ({attempt+1}/{max_retries})...")
                    backoff_with_jitter(attempt)
                    continue
                else:
                    print("Maximum retry attempts reached for related queries. Skipping this part of the analysis.")
                    return None

# Function to plot time trends
def plot_time_trends(interest_df, user_keywords, user_timeframe, user_geo):
    plt.figure(figsize=(14, 8))  # Larger figure size for better visibility
    
    # Check if we have data for any of the keywords
    has_data = False
    for keyword in user_keywords:
        if keyword in interest_df.columns:
            has_data = True
            
            # For longer timeframes, use appropriate marker frequency
            if user_timeframe in ['today 5-y', 'today 12-m', 'today 3-m']:
                # For longer periods, don't use markers on every point to avoid clutter
                plt.plot(interest_df.index, interest_df[keyword], label=keyword, linewidth=2)
            else:
                # For shorter periods, use markers
                plt.plot(interest_df.index, interest_df[keyword], label=keyword, marker='o', linestyle='-', linewidth=2)
        else:
            print(f"⚠️ Warning: No data found for keyword '{keyword}'")
    
    if not has_data:
        print("❌ No data available for any of the keywords.")
        return False

    # Set appropriate title based on timeframe
    timeframe_titles = {
        'now 1-d': 'Last 24 Hours',
        'now 7-d': 'Last 7 Days',
        'today 1-m': 'Last 30 Days',
        'today 3-m': 'Last 90 Days',
        'today 12-m': 'Last 12 Months',
        'today 5-y': 'Last 5 Years'
    }
    title_timeframe = timeframe_titles.get(user_timeframe, user_timeframe)
    
    region_text = f" in {user_geo}" if user_geo else " Worldwide"
    plt.title(f'Google Search Trends ({title_timeframe}{region_text})', fontsize=16)
    plt.xlabel('Time', fontsize=12)
    plt.ylabel('Search Interest', fontsize=12)
    
    # Format x-axis based on timeframe
    if user_timeframe == 'today 5-y':
        # For 5 years, use a date formatter that shows year and month
        import matplotlib.dates as mdates
        years = mdates.YearLocator()   # every year
        months = mdates.MonthLocator()  # every month
        years_fmt = mdates.DateFormatter('%Y')
        
        ax = plt.gca()
        ax.xaxis.set_major_locator(years)
        ax.xaxis.set_major_formatter(years_fmt)
        ax.xaxis.set_minor_locator(months)
        
        # Add grid lines at year boundaries
        ax.grid(True, which='major', axis='x', linestyle='-', alpha=0.7)
        ax.grid(True, which='minor', axis='x', linestyle='--', alpha=0.2)
        
    elif user_timeframe in ['today 12-m', 'today 3-m']:
        # For months, use a date formatter that shows month and year
        import matplotlib.dates as mdates
        months = mdates.MonthLocator()  # every month
        month_fmt = mdates.DateFormatter('%b %Y')
        
        ax = plt.gca()
        ax.xaxis.set_major_locator(months)
        ax.xaxis.set_major_formatter(month_fmt)
    
    plt.legend(fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)  # Rotate x-axis labels for better readability
    plt.tight_layout()
    
    # Add a note about the data source
    plt.figtext(0.99, 0.01, 'Data source: Google Trends', 
               horizontalalignment='right', fontsize=8, style='italic')

    # Save the chart
    current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    keywords_text = "_".join(user_keywords).replace(" ", "-")[:30]  # Limit length for filename
    filename = f"trends_time_{keywords_text}_{current_time}.png"
    plt.savefig(filename)
    plt.show()

    print(f"\n✅ Time trend chart saved as: {filename}")
    return True

# Function to plot region (state/province) trends
def plot_region_trends(region_df, user_keywords, user_geo):
    if region_df is None or region_df.empty:
        print("❌ No region data available.")
        return False
    
    try:
        # Create a single figure for all keywords to reduce memory usage
        plt.figure(figsize=(14, 10))
        
        # Only plot data for the first keyword to simplify
        keyword = user_keywords[0]
        
        if keyword in region_df.columns:
            # Sort by interest value (descending)
            sorted_df = region_df.sort_values(by=keyword, ascending=False)
            
            # Get top 15 regions for better visualization (reduced from 20)
            top_regions = sorted_df.head(15)
            
            # Create horizontal bar chart
            bars = plt.barh(top_regions.index, top_regions[keyword], color='skyblue')
            
            # Add value labels to the bars
            for bar in bars:
                width = bar.get_width()
                label_x_pos = width + 1
                plt.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{width:.0f}', 
                         va='center', fontsize=10)
            
            plt.title(f'Top Regions for "{keyword}" in {user_geo}', fontsize=16)
            plt.xlabel('Search Interest', fontsize=12)
            plt.ylabel('Region', fontsize=12)
            plt.tight_layout()
            
            # Save the chart
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            keyword_text = keyword.replace(" ", "-")[:30]  # Limit length for filename
            output_dir = "trend_charts"
            filename = f"{output_dir}/trends_region_{keyword_text}_{user_geo}_{current_time}.png"
            plt.savefig(filename)
            
            # Close the figure to free up memory
            plt.close()
            
            print(f"\n✅ Region trend chart for '{keyword}' saved as: {filename}")
            
            # If there are additional keywords, mention that they're not being plotted
            if len(user_keywords) > 1:
                print(f"⚠️ Charts for additional keywords were not generated to improve performance.")
                print(f"   Data for all keywords is available in the saved CSV file.")
        else:
            print(f"⚠️ No region data available for keyword '{keyword}'")
        
        return True
    
    except Exception as e:
        print(f"❌ Error generating region visualization: {str(e)}")
        return False

# Function to plot city trends
def plot_city_trends(city_df, user_keywords, user_geo):
    if city_df is None or city_df.empty:
        print("❌ No city data available.")
        return False
    
    try:
        # Create a single figure
        plt.figure(figsize=(14, 10))  # Reduced size from (14, 12)
        
        # Only plot data for the first keyword
        keyword = user_keywords[0]
        
        if keyword in city_df.columns:
            # Sort by interest value (descending)
            sorted_df = city_df.sort_values(by=keyword, ascending=False)
            
            # Get top 15 cities for better visualization (reduced from 25)
            top_cities = sorted_df.head(15)
            
            # Create horizontal bar chart
            bars = plt.barh(top_cities.index, top_cities[keyword], color='lightgreen')
            
            # Add value labels to the bars
            for bar in bars:
                width = bar.get_width()
                label_x_pos = width + 1
                plt.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{width:.0f}', 
                         va='center', fontsize=10)
            
            plt.title(f'Top Cities for "{keyword}" in {user_geo}', fontsize=16)
            plt.xlabel('Search Interest', fontsize=12)
            plt.ylabel('City', fontsize=12)
            plt.tight_layout()
            
            # Save the chart
            current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            keyword_text = keyword.replace(" ", "-")[:30]  # Limit length for filename
            output_dir = "trend_charts"
            filename = f"{output_dir}/trends_city_{keyword_text}_{user_geo}_{current_time}.png"
            plt.savefig(filename)
            
            # Close the figure to free up memory
            plt.close()
            
            print(f"\n✅ City trend chart for '{keyword}' saved as: {filename}")
        else:
            print(f"⚠️ No city data available for keyword '{keyword}'")
        
        return True
    
    except Exception as e:
        print(f"❌ Error generating city visualization: {str(e)}")
        return False

# Function to display related queries
def display_related_queries(related_queries, user_keywords):
    if not related_queries:
        print("❌ No related queries data available.")
        return False
    
    print("\n===== Related Queries =====")
    
    for keyword in user_keywords:
        if keyword in related_queries and related_queries[keyword]:
            print(f"\n🔍 Related queries for '{keyword}':")
            
            # Top queries (rising)
            if 'rising' in related_queries[keyword] and not related_queries[keyword]['rising'].empty:
                print("\n📈 Rising queries:")
                rising_df = related_queries[keyword]['rising'].head(10)
                print(rising_df)
                
                # Create a bar chart for rising queries
                plt.figure(figsize=(12, 8))
                bars = plt.barh(rising_df['query'], rising_df['value'], color='coral')
                
                # Add value labels
                for bar in bars:
                    width = bar.get_width()
                    label_x_pos = width + 5
                    plt.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{width:.0f}%', 
                             va='center', fontsize=10)
                
                plt.title(f'Rising Related Queries for "{keyword}"', fontsize=16)
                plt.xlabel('Relative Growth (%)', fontsize=12)
                plt.ylabel('Query', fontsize=12)
                plt.tight_layout()
                
                # Save the chart
                current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                keyword_text = keyword.replace(" ", "-")[:30]
                filename = f"trends_rising_{keyword_text}_{current_time}.png"
                plt.savefig(filename)
                plt.show()
                
                print(f"✅ Rising queries chart saved as: {filename}")
            
            # Top queries
            if 'top' in related_queries[keyword] and not related_queries[keyword]['top'].empty:
                print("\n🔝 Top queries:")
                top_df = related_queries[keyword]['top'].head(10)
                print(top_df)
                
                # Create a bar chart for top queries
                plt.figure(figsize=(12, 8))
                bars = plt.barh(top_df['query'], top_df['value'], color='lightblue')
                
                # Add value labels
                for bar in bars:
                    width = bar.get_width()
                    label_x_pos = width + 1
                    plt.text(label_x_pos, bar.get_y() + bar.get_height()/2, f'{width:.0f}', 
                             va='center', fontsize=10)
                
                plt.title(f'Top Related Queries for "{keyword}"', fontsize=16)
                plt.xlabel('Search Interest', fontsize=12)
                plt.ylabel('Query', fontsize=12)
                plt.tight_layout()
                
                # Save the chart
                current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                keyword_text = keyword.replace(" ", "-")[:30]
                filename = f"trends_top_{keyword_text}_{current_time}.png"
                plt.savefig(filename)
                plt.show()
                
                print(f"✅ Top queries chart saved as: {filename}")
        else:
            print(f"\n⚠️ No related queries data available for '{keyword}'")
    
    return True

# --------- Main Function ---------
def get_trends_json(keywords, timeframe, geo='', analysis_options=None, proxy_info=None):
    """
    Get Google Trends data and return it as a JSON-compatible dictionary
    
    Parameters:
    - keywords: List of keywords to search for
    - timeframe: Time period to analyze (e.g., 'now 1-d', 'today 5-y')
    - geo: Geographic region code (e.g., 'US', 'IN')
    - analysis_options: Dictionary with analysis options
    - proxy_info: Dictionary with proxy configuration
    
    Returns:
    - Dictionary with trends data in JSON format
    """
    if analysis_options is None:
        analysis_options = {
            "include_time_trends": True,
            "include_state_analysis": True if geo else False,
            "include_city_analysis": True if geo else False,
            "include_related_queries": True
        }
    
    # Create output directory for charts if it doesn't exist
    output_dir = "trend_charts"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # --------- Initialize PyTrends ---------
    # Create a custom session
    session = create_retry_session()
    
    # Add proxy to session if provided
    if proxy_info:
        session.proxies.update(proxy_info)
        print(f"Using proxy for requests.")
    
    # Get fresh Google cookies to help avoid rate limiting
    cookies = get_google_cookies()
    
    # Configure PyTrends with simpler parameters to avoid conflicts
    try:
        # First try with cookies if available
        if cookies:
            # Create a new TrendReq instance with our cookies
            pytrends = TrendReq(hl='en-US', tz=330)
            # Manually set the cookies
            pytrends.cookies = cookies
            print("Using custom cookies for Google Trends requests.")
        else:
            # Fall back to default initialization
            pytrends = TrendReq(hl='en-US', tz=330)
    except Exception as e:
        print(f"Error initializing PyTrends: {str(e)}")
        print("Trying alternative initialization...")
        try:
            # Fallback to even simpler initialization
            pytrends = TrendReq()
        except Exception as e:
            print(f"Failed to initialize PyTrends: {str(e)}")
            return None
    
    # Dictionary to store all data
    trends_data = {}
    
    # Flag to track if we should continue with additional requests
    continue_analysis = True
    
    # 1. Fetch time trends data
    if analysis_options['include_time_trends']:
        try:
            print("Fetching time trends data...")
            interest_df = get_trends_data(pytrends, keywords, timeframe, geo)
            trends_data['time_trends'] = interest_df
            
            if interest_df is None or interest_df.empty:
                continue_analysis = False
        except Exception as e:
            print(f"Error during time trends retrieval: {str(e)}")
            continue_analysis = False
    
    # Add a delay between different types of requests
    if continue_analysis:
        time.sleep(15)
    
    # 2. Fetch region (state/province) data
    if continue_analysis and analysis_options['include_state_analysis'] and geo:
        try:
            print("Fetching state/province data...")
            # Use only the first keyword for geographic data to reduce rate limiting
            region_keywords = [keywords[0]]
            region_df = get_interest_by_region(pytrends, region_keywords, timeframe, geo, resolution='REGION')
            trends_data['region_data'] = region_df
        except Exception as e:
            print(f"Error during region data retrieval: {str(e)}")
    
    # Add a delay between different types of requests
    if continue_analysis:
        time.sleep(30)
    
    # 3. Fetch city data
    if continue_analysis and analysis_options['include_city_analysis'] and geo:
        try:
            print("Fetching city data...")
            # For city data, always use just the first keyword
            city_keyword = [keywords[0]]
            city_df = get_interest_by_region(pytrends, city_keyword, timeframe, geo, resolution='CITY')
            trends_data['city_data'] = city_df
        except Exception as e:
            print(f"Error during city data retrieval: {str(e)}")
    
    # Add a delay between different types of requests
    if continue_analysis:
        time.sleep(15)
    
    # 4. Fetch related queries
    if continue_analysis and analysis_options['include_related_queries']:
        try:
            print("Fetching related queries...")
            related_queries = get_related_queries(pytrends, keywords, timeframe, geo)
            trends_data['related_queries'] = related_queries
        except Exception as e:
            print(f"Error during related queries retrieval: {str(e)}")
    
    # Create a JSON-compatible dictionary
    json_data = {
        "metadata": {
            "keywords": keywords,
            "timeframe": timeframe,
            "region": geo if geo else "Worldwide",
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        },
        "data": {}
    }
    
    # Convert each data type to JSON-compatible format
    if 'time_trends' in trends_data and trends_data['time_trends'] is not None:
        # For time trends, we need to handle the datetime index
        time_df = trends_data['time_trends'].copy()
        # Convert datetime index to string
        time_df.index = time_df.index.strftime('%Y-%m-%d %H:%M:%S')
        json_data['data']['time_trends'] = dataframe_to_json(time_df)
    
    if 'region_data' in trends_data and trends_data['region_data'] is not None:
        json_data['data']['region_data'] = dataframe_to_json(trends_data['region_data'])
    
    if 'city_data' in trends_data and trends_data['city_data'] is not None:
        json_data['data']['city_data'] = dataframe_to_json(trends_data['city_data'])
    
    if 'related_queries' in trends_data and trends_data['related_queries'] is not None:
        # Related queries has a more complex structure
        related_json = {}
        for keyword in trends_data['related_queries']:
            related_json[keyword] = {}
            if 'top' in trends_data['related_queries'][keyword]:
                related_json[keyword]['top'] = dataframe_to_json(trends_data['related_queries'][keyword]['top'])
            if 'rising' in trends_data['related_queries'][keyword]:
                related_json[keyword]['rising'] = dataframe_to_json(trends_data['related_queries'][keyword]['rising'])
        
        json_data['data']['related_queries'] = related_json
    
    return json_data

def main():
    # Get user input
    user_keywords, user_timeframe, user_geo, analysis_options, proxy_info = get_user_input()
    
    # Create output directory for charts if it doesn't exist
    output_dir = "trend_charts"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created output directory: {output_dir}")
    
    # --------- Initialize PyTrends ---------
    # Create a custom session
    session = create_retry_session()
    
    # Add proxy to session if provided
    if proxy_info:
        session.proxies.update(proxy_info)
        print(f"Using proxy for requests.")
    
    # Get fresh Google cookies to help avoid rate limiting
    cookies = get_google_cookies()
    
    # Configure PyTrends with simpler parameters to avoid conflicts
    try:
        # First try with cookies if available
        if cookies:
            # Create a new TrendReq instance with our cookies
            pytrends = TrendReq(hl='en-US', tz=330)
            # Manually set the cookies
            pytrends.cookies = cookies
            print("Using custom cookies for Google Trends requests.")
        else:
            # Fall back to default initialization
            pytrends = TrendReq(hl='en-US', tz=330)
    except Exception as e:
        print(f"Error initializing PyTrends: {str(e)}")
        print("Trying alternative initialization...")
        try:
            # Fallback to even simpler initialization
            pytrends = TrendReq()
        except Exception as e:
            print(f"Failed to initialize PyTrends: {str(e)}")
            print("Please check your internet connection and try again.")
            return
    
    # Show what we're searching for
    print(f"\n🔍 Searching for: {', '.join(user_keywords)}")
    print(f"📅 Timeframe: {user_timeframe}")
    print(f"🌎 Region: {user_geo if user_geo else 'Worldwide'}")
    print("\nAnalysis includes:")
    print(f"- Time trends: {'Yes' if analysis_options['include_time_trends'] else 'No'}")
    print(f"- State/Province analysis: {'Yes' if analysis_options['include_state_analysis'] else 'No'}")
    print(f"- City analysis: {'Yes' if analysis_options['include_city_analysis'] else 'No'}")
    print(f"- Related queries: {'Yes' if analysis_options['include_related_queries'] else 'No'}")
    
    # Special message for state-only or city-only options
    if analysis_options.get('state_only'):
        print("\n🚀 Running in State/Province-only mode for faster results")
    elif analysis_options.get('city_only'):
        print("\n🚀 Running in City-only mode for faster results")
    
    # Warn if too many keywords are selected
    if len(user_keywords) > 2 and (analysis_options['include_state_analysis'] or 
                                  analysis_options['include_city_analysis'] or 
                                  analysis_options['include_related_queries']):
        print("\n⚠️ Warning: Using multiple keywords with geographic analysis increases the chance of rate limiting.")
        limit_keywords = input("Would you like to limit analysis to just the first keyword? (y/n) [Default: n]: ").strip().lower() or "n"
        if limit_keywords == "y":
            print(f"Limiting analysis to first keyword: {user_keywords[0]}")
            user_keywords = [user_keywords[0]]
            
    # For state-only or city-only options, automatically use just the first keyword for better performance
    if analysis_options.get('state_only') or analysis_options.get('city_only'):
        if len(user_keywords) > 1:
            print(f"\n⚠️ For faster and more reliable results in focused mode, using only the first keyword: {user_keywords[0]}")
            user_keywords = [user_keywords[0]]
    
    # Initial delay before first request
    print("\nInitial delay before starting...")
    time.sleep(10)  # Increased from 5 to 10 seconds
    
    # Dictionary to store all data
    trends_data = {}
    
    # Flag to track if we should continue with additional requests
    continue_analysis = True
    
    # For state-only or city-only options, we can skip time trends to reduce rate limiting
    # and make the analysis faster
    if analysis_options.get('state_only') or analysis_options.get('city_only'):
        print("\n⏩ Skipping time trends data to focus on geographic analysis...")
        # We still need to initialize pytrends with a payload before geographic requests
        try:
            # Add a shorter delay since we're just initializing
            add_random_delay(5, 10)
            # Build the payload but don't fetch data
            pytrends.build_payload(user_keywords, cat=0, timeframe=user_timeframe, geo=user_geo, gprop='')
            print("✅ Successfully initialized Google Trends connection")
        except Exception as e:
            print(f"\n❌ Error during initialization: {str(e)}")
            print("Will attempt to proceed anyway...")
    # 1. Fetch time trends data (if not in state-only or city-only mode)
    elif analysis_options['include_time_trends']:
        try:
            print("\n📈 Fetching time trends data...")
            interest_df = get_trends_data(pytrends, user_keywords, user_timeframe, user_geo)
            trends_data['time_trends'] = interest_df
            
            # Data quality check
            if interest_df is not None and not interest_df.empty:
                # Print data statistics
                print(f"\n📊 Data Statistics:")
                print(f"  - Time range: {interest_df.index.min()} to {interest_df.index.max()}")
                print(f"  - Number of data points: {len(interest_df)}")
                print(f"  - Data frequency: {pd.infer_freq(interest_df.index) or 'Irregular'}")
                
                # For 5-year data, ensure we have enough coverage
                if user_timeframe == 'today 5-y':
                    expected_years = 5
                    actual_years = (interest_df.index.max() - interest_df.index.min()).days / 365.25
                    coverage = (actual_years / expected_years) * 100
                    
                    if coverage < 90:
                        print(f"\n⚠️ Warning: Data covers only {coverage:.1f}% of the requested 5-year period.")
                        print("   This might be due to limited data availability for the selected keywords.")
                    else:
                        print(f"\n✅ Good data coverage: {coverage:.1f}% of the requested 5-year period.")
                
                print("\n🔹 Google Trends Time Data:")
                print(interest_df.head())
            else:
                print("\n⚠️ Failed to retrieve time trends data. Proceeding with limited analysis.")
                continue_analysis = False
        except Exception as e:
            print(f"\n❌ Error during time trends retrieval: {str(e)}")
            print("Proceeding with limited analysis.")
            continue_analysis = False
    
    # Add a delay between different types of requests
    # Shorter delay for state-only or city-only options
    if continue_analysis:
        if analysis_options.get('state_only') or analysis_options.get('city_only'):
            print("\nPreparing for geographic data request...")
            time.sleep(5)  # Shorter delay for focused analysis
        else:
            print("\nWaiting before next request...")
            time.sleep(15)  # Standard delay for regular analysis
    
    # 2. Fetch region (state/province) data
    if (continue_analysis and analysis_options['include_state_analysis'] and user_geo) or analysis_options.get('state_only'):
        try:
            # Special message for state-only mode
            if analysis_options.get('state_only'):
                print("\n🗺️ Fetching state/province data in focused mode...")
                print("This optimized request should be faster and more reliable...")
            else:
                print("\n🗺️ Fetching state/province data...")
                print("This may take some time. Please be patient...")
            
            # For state-only mode, we always use just the first keyword for better performance
            if analysis_options.get('state_only'):
                region_keywords = [user_keywords[0]]
                print(f"Using keyword: {region_keywords[0]}")
            # If we have multiple keywords in regular mode, ask if user wants to proceed with all or just the first one
            elif len(user_keywords) > 1:
                print(f"\n⚠️ Note: Using multiple keywords ({len(user_keywords)}) for geographic analysis increases the chance of rate limiting.")
                print("For better results, it's recommended to use only the first keyword.")
                limit_keywords = input("Would you like to limit state analysis to just the first keyword? (y/n) [Default: y]: ").strip().lower() or "y"
                if limit_keywords == "y":
                    print(f"Limiting state analysis to first keyword: {user_keywords[0]}")
                    region_keywords = [user_keywords[0]]
                else:
                    region_keywords = user_keywords
            else:
                region_keywords = user_keywords
            
            # Use a longer timeout for region data
            # For state-only mode, we use optimized parameters
            if analysis_options.get('state_only'):
                # Use a slightly modified function call with more retries for state-only mode
                region_df = get_interest_by_region(pytrends, region_keywords, user_timeframe, user_geo, resolution='REGION', max_retries=7)
            else:
                region_df = get_interest_by_region(pytrends, region_keywords, user_timeframe, user_geo, resolution='REGION')
            
            trends_data['region_data'] = region_df
            
            if region_df is not None and not region_df.empty:
                print("\n🔹 Google Trends Region Data (Top 5):")
                # Sort by the first keyword for display
                if region_keywords[0] in region_df.columns:
                    sorted_df = region_df.sort_values(by=region_keywords[0], ascending=False)
                    print(sorted_df.head())
                else:
                    print(region_df.head())
                
                # Save the data to CSV for later use
                try:
                    csv_filename = f"region_data_{user_geo}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    region_df.to_csv(csv_filename)
                    print(f"✅ Region data saved to {csv_filename} for future reference")
                except Exception as csv_error:
                    print(f"⚠️ Could not save region data to CSV: {str(csv_error)}")
                
                # For state-only mode, provide a more detailed output
                if analysis_options.get('state_only'):
                    print("\n📊 State/Province Analysis Summary:")
                    print(f"Total regions with data: {len(region_df)}")
                    if len(region_df) > 0:
                        top_region = sorted_df.index[0] if region_keywords[0] in region_df.columns else region_df.index[0]
                        print(f"Top region: {top_region}")
                        print("\nTop 10 regions:")
                        print(sorted_df.head(10) if region_keywords[0] in region_df.columns else region_df.head(10))
            else:
                print("\n⚠️ No region data available. Skipping region analysis.")
        except Exception as e:
            print(f"\n❌ Error during region data retrieval: {str(e)}")
            print("Skipping region analysis.")
    
    # Add a longer delay between different types of requests
    # Skip this delay if we're in city-only mode (since we haven't made any previous requests)
    if continue_analysis and not analysis_options.get('city_only'):
        print("\nWaiting before next request...")
        time.sleep(30)  # Increased from 15 to 30 seconds
    
    # 3. Fetch city data
    if (continue_analysis and analysis_options['include_city_analysis'] and user_geo) or analysis_options.get('city_only'):
        try:
            # Special message for city-only mode
            if analysis_options.get('city_only'):
                print("\n🏙️ Fetching city data in focused mode...")
                print("This optimized request should be faster and more reliable...")
            else:
                print("\n🏙️ Fetching city data...")
                print("This may take some time. Please be patient...")
            
            # For city data, always use just the first keyword to reduce rate limiting
            city_keyword = [user_keywords[0]]
            print(f"Using keyword: '{city_keyword[0]}' for city analysis")
            
            # Use a specialized function for city data
            print("🔍 Fetching city-level data...")
            
            # Define a specialized function for city data right here
            def get_city_data(kw, tf, geo_code, max_retry=5):
                """Special function to ensure we get city-level data"""
                for attempt in range(max_retry):
                    try:
                        # Add delay between attempts
                        if attempt > 0:
                            print(f"City data attempt {attempt+1}/{max_retry}...")
                            add_random_delay(15, 30)
                        
                        # Build the payload with specific parameters for city data
                        pytrends.build_payload(kw, cat=0, timeframe=tf, geo=geo_code, gprop='')
                        
                        # Request city data with explicit parameters
                        city_data = pytrends.interest_by_region(
                            resolution='CITY',
                            inc_low_vol=True,
                            inc_geo_code=True
                        )
                        
                        # Verify we got city data (cities usually have commas in their names)
                        if city_data is not None and not city_data.empty:
                            city_data_detected = any(',' in str(idx) for idx in city_data.index)
                            if city_data_detected:
                                print(f"✅ Successfully retrieved city data on attempt {attempt+1}")
                                return city_data
                            else:
                                print("⚠️ Received geographic data but it may not be city-level. Retrying...")
                        else:
                            print("⚠️ No data received. Retrying...")
                    
                    except Exception as e:
                        print(f"❌ Error during city data retrieval (attempt {attempt+1}): {str(e)}")
                
                # If all attempts failed, try one last approach with a fresh session
                try:
                    print("Making final attempt with a fresh session...")
                    # Create a new session
                    fresh_pytrends = TrendReq(hl='en-US', tz=330)
                    # Add a longer delay
                    add_random_delay(30, 60)
                    # Build payload with explicit city focus
                    fresh_pytrends.build_payload(kw, cat=0, timeframe=tf, geo=geo_code, gprop='')
                    # Force city resolution with all options enabled
                    final_data = fresh_pytrends.interest_by_region(
                        resolution='CITY',
                        inc_low_vol=True,
                        inc_geo_code=True
                    )
                    return final_data
                except Exception as final_error:
                    print(f"❌ Final attempt failed: {str(final_error)}")
                    return None
            
            # Use more retries for city-only mode
            if analysis_options.get('city_only'):
                city_df = get_city_data(city_keyword, user_timeframe, user_geo, max_retry=7)
            else:
                city_df = get_city_data(city_keyword, user_timeframe, user_geo, max_retry=5)
            
            trends_data['city_data'] = city_df
            
            if city_df is not None and not city_df.empty:
                # Verify we actually got city data
                # Cities usually have commas in their names (e.g., "San Francisco, CA")
                # or have more entries than would be expected for regions/states
                city_data_detected = any(',' in str(idx) for idx in city_df.index) or len(city_df) > 50
                
                if city_data_detected:
                    print("\n🔹 Google Trends City Data (Top 5):")
                    # Sort by the first keyword for display
                    if city_keyword[0] in city_df.columns:
                        sorted_df = city_df.sort_values(by=city_keyword[0], ascending=False)
                        print(sorted_df.head())
                    else:
                        print(city_df.head())
                else:
                    # If we still didn't get city data, inform the user
                    print("\n⚠️ Note: The data returned may not be city-level data.")
                    print("This can happen due to Google Trends API limitations or insufficient data for cities.")
                    print("The data shown below is the best available geographic breakdown:")
                    
                    if city_keyword[0] in city_df.columns:
                        sorted_df = city_df.sort_values(by=city_keyword[0], ascending=False)
                        print(sorted_df.head())
                    else:
                        print(city_df.head())
                
                # Save the data to CSV for later use
                try:
                    csv_filename = f"city_data_{user_geo}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    city_df.to_csv(csv_filename)
                    print(f"✅ City data saved to {csv_filename} for future reference")
                except Exception as csv_error:
                    print(f"⚠️ Could not save city data to CSV: {str(csv_error)}")
                
                # For city-only mode, provide a more detailed output
                if analysis_options.get('city_only'):
                    # Verify we actually got city data
                    # Cities usually have commas in their names (e.g., "San Francisco, CA")
                    # or have more entries than would be expected for regions/states
                    city_data_detected = any(',' in str(idx) for idx in city_df.index) or len(city_df) > 50
                    
                    if city_data_detected:
                        print("\n📊 City Analysis Summary:")
                        print(f"Total cities with data: {len(city_df)}")
                        if len(city_df) > 0:
                            top_city = sorted_df.index[0] if city_keyword[0] in city_df.columns else city_df.index[0]
                            print(f"Top city: {top_city}")
                            print("\nTop 10 cities:")
                            print(sorted_df.head(10) if city_keyword[0] in city_df.columns else city_df.head(10))
                    else:
                        print("\n📊 Geographic Analysis Summary:")
                        print("Note: The data appears to be region-level rather than city-level.")
                        print("This is likely due to Google Trends API limitations or insufficient city-level data.")
                        print(f"Total regions with data: {len(city_df)}")
                        if len(city_df) > 0:
                            top_region = sorted_df.index[0] if city_keyword[0] in city_df.columns else city_df.index[0]
                            print(f"Top region: {top_region}")
                            print("\nTop 10 regions:")
                            print(sorted_df.head(10) if city_keyword[0] in city_df.columns else city_df.head(10))
            else:
                print("\n⚠️ No city data available. Skipping city analysis.")
        except Exception as e:
            print(f"\n❌ Error during city data retrieval: {str(e)}")
            print("Skipping city analysis.")
    
    # Add a longer delay between different types of requests
    # Skip this delay if we're in state-only or city-only mode
    if continue_analysis and not (analysis_options.get('state_only') or analysis_options.get('city_only')):
        print("\nWaiting before next request...")
        time.sleep(15)
    
    # 4. Fetch related queries (skip for state-only and city-only modes)
    if continue_analysis and analysis_options['include_related_queries'] and not (analysis_options.get('state_only') or analysis_options.get('city_only')):
        try:
            print("\n🔍 Fetching related queries...")
            related_queries = get_related_queries(pytrends, user_keywords, user_timeframe, user_geo)
            trends_data['related_queries'] = related_queries
        except Exception as e:
            print(f"\n❌ Error during related queries retrieval: {str(e)}")
            print("Skipping related queries analysis.")
    
    # Generate visualizations
    print("\n📊 Generating visualizations...")
    
    # Track if we've generated any visualizations
    visualizations_generated = False
    
    # 1. Plot time trends
    if 'time_trends' in trends_data and trends_data['time_trends'] is not None and not trends_data['time_trends'].empty:
        try:
            success = plot_time_trends(trends_data['time_trends'], user_keywords, user_timeframe, user_geo)
            visualizations_generated = visualizations_generated or success
        except Exception as e:
            print(f"\n❌ Error generating time trends visualization: {str(e)}")
    
    # 2. Plot region trends
    if 'region_data' in trends_data and trends_data['region_data'] is not None and not trends_data['region_data'].empty:
        try:
            success = plot_region_trends(trends_data['region_data'], user_keywords, user_geo)
            visualizations_generated = visualizations_generated or success
        except Exception as e:
            print(f"\n❌ Error generating region trends visualization: {str(e)}")
    
    # 3. Plot city trends
    if 'city_data' in trends_data and trends_data['city_data'] is not None and not trends_data['city_data'].empty:
        try:
            success = plot_city_trends(trends_data['city_data'], user_keywords, user_geo)
            visualizations_generated = visualizations_generated or success
        except Exception as e:
            print(f"\n❌ Error generating city trends visualization: {str(e)}")
    
    # 4. Display related queries
    if 'related_queries' in trends_data and trends_data['related_queries'] is not None:
        try:
            success = display_related_queries(trends_data['related_queries'], user_keywords)
            visualizations_generated = visualizations_generated or success
        except Exception as e:
            print(f"\n❌ Error displaying related queries: {str(e)}")
    
    # Save all data to JSON format
    json_file = save_trends_to_json(trends_data, user_keywords, user_timeframe, user_geo)
    
    # Special completion message for state-only and city-only modes
    if analysis_options.get('state_only'):
        print("\n✅ State/Province-only analysis complete!")
        if visualizations_generated:
            print("Charts have been saved.")
        print("This focused analysis mode is optimized for faster and more reliable results.")
    elif analysis_options.get('city_only'):
        print("\n✅ City-only analysis complete!")
        if visualizations_generated:
            print("Charts have been saved.")
        print("This focused analysis mode is optimized for faster and more reliable results.")
    # Standard completion message for other modes
    elif visualizations_generated:
        print("\n✅ Analysis complete! Charts have been saved.")
    else:
        print("\n⚠️ No visualizations could be generated. Please try again later or with different parameters.")
        print("\nTips to avoid rate limiting:")
        print("1. Try fewer keywords at once")
        print("2. Use a longer timeframe (e.g., 'Last 12 months' instead of 'Last 24 hours')")
        print("3. Try options 5 or 6 for faster, more focused analysis")
        print("4. Wait a few hours before trying again")
        print("5. Try using a VPN or different network connection")
    
    # Return the JSON data path
    if json_file:
        print(f"\n🔄 All trend data is available in JSON format at: {json_file}")
        print("You can use this JSON file for further analysis or integration with other applications.")

# Function to convert pandas DataFrame to JSON-compatible format
def dataframe_to_json(df):
    if df is None or df.empty:
        return None
    
    try:
        # Handle NaN values and convert to JSON-compatible format
        df_copy = df.copy()
        
        # Replace NaN values with None for proper JSON serialization
        df_copy = df_copy.where(pd.notnull(df_copy), None)
        
        # Handle datetime objects in the DataFrame
        for col in df_copy.select_dtypes(include=['datetime64']).columns:
            df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Sanitize string columns by removing control characters and ensuring proper escaping
        for col in df_copy.select_dtypes(include=['object']).columns:
            # Skip None values
            mask = df_copy[col].notna()
            if mask.any():
                # Replace control characters with empty string
                df_copy.loc[mask, col] = df_copy.loc[mask, col].str.replace(
                    r'[\x00-\x1F\x7F-\x9F]', '', regex=True
                )
                # Ensure strings have proper encoding
                df_copy.loc[mask, col] = df_copy.loc[mask, col].apply(
                    lambda x: x.encode('utf-8', errors='ignore').decode('utf-8') if isinstance(x, str) else x
                )
        
        # Convert DataFrame to dictionary
        # Handle index properly by making it a column
        result = df_copy.reset_index().to_dict(orient='records')
        
        # Additional safety check: recursively sanitize all string values
        def sanitize_dict(obj):
            if isinstance(obj, dict):
                return {k: sanitize_dict(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [sanitize_dict(item) for item in obj]
            elif isinstance(obj, str):
                # Remove control characters that can break JSON
                return re.sub(r'[\x00-\x1F\x7F-\x9F]', '', obj)
            else:
                return obj
        
        return sanitize_dict(result)
    except Exception as e:
        # Log the error but return a safe, empty list rather than failing
        print(f"Error in dataframe_to_json: {str(e)}")
        logger.error(f"Error converting DataFrame to JSON: {str(e)}", exc_info=True)
        return []

# Function to save trends data to JSON file
def save_trends_to_json(trends_data, user_keywords, user_timeframe, user_geo):
    """
    Convert trends data to JSON format and save to file
    
    Parameters:
    - trends_data: Dictionary containing all trends data
    - user_keywords: List of keywords searched
    - user_timeframe: Timeframe used for the search
    - user_geo: Geographic region code
    
    Returns:
    - Path to the saved JSON file
    """
    try:
        # Create a JSON-compatible dictionary
        json_data = {
            "metadata": {
                "keywords": user_keywords,
                "timeframe": user_timeframe,
                "region": user_geo if user_geo else "Worldwide",
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "data": {}
        }
        
        # Convert each data type to JSON-compatible format
        if 'time_trends' in trends_data and trends_data['time_trends'] is not None:
            # For time trends, we need to handle the datetime index
            time_df = trends_data['time_trends'].copy()
            # Convert datetime index to string
            time_df.index = time_df.index.strftime('%Y-%m-%d %H:%M:%S')
            json_data['data']['time_trends'] = dataframe_to_json(time_df)
        
        if 'region_data' in trends_data and trends_data['region_data'] is not None:
            json_data['data']['region_data'] = dataframe_to_json(trends_data['region_data'])
        
        if 'city_data' in trends_data and trends_data['city_data'] is not None:
            json_data['data']['city_data'] = dataframe_to_json(trends_data['city_data'])
        
        if 'related_queries' in trends_data and trends_data['related_queries'] is not None:
            # Related queries has a more complex structure
            related_json = {}
            for keyword in trends_data['related_queries']:
                related_json[keyword] = {}
                if 'top' in trends_data['related_queries'][keyword]:
                    related_json[keyword]['top'] = dataframe_to_json(trends_data['related_queries'][keyword]['top'])
                if 'rising' in trends_data['related_queries'][keyword]:
                    related_json[keyword]['rising'] = dataframe_to_json(trends_data['related_queries'][keyword]['rising'])
            
            json_data['data']['related_queries'] = related_json
        
        # Save to file
        output_dir = "trend_data"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Create filename with timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        keywords_text = "_".join([k.replace(" ", "-") for k in user_keywords])[:30]
        json_filename = f"{output_dir}/trends_{keywords_text}_{user_geo}_{timestamp}.json"
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ All trends data saved to JSON file: {json_filename}")
        return json_filename
    
    except Exception as e:
        print(f"\n❌ Error saving trends data to JSON: {str(e)}")
        return None

# Execute the main function
if __name__ == "__main__":
    main()

# --------- Django Integration Functions ---------

def prepare_trends_data_for_django(keywords_list, timeframe, geo='', analysis_options=None, proxy_info=None):
    """
    Function to be called from Django views to get Google Trends data
    
    Parameters:
    - keywords_list: List of keywords to analyze
    - timeframe: Time period to analyze (e.g., 'now 1-d', 'today 5-y')
    - geo: Geographic region code (e.g., 'US', 'IN', or '' for worldwide)
    - analysis_options: Dictionary with analysis options
    - proxy_info: Dictionary with proxy configuration
    
    Returns:
    - Dictionary with JSON-ready data for frontend charts
    """
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
    
    # Validate inputs
    if not keywords_list:
        keywords_list = ["Artificial Intelligence"]
    
    # Limit keywords to reduce rate limiting
    if len(keywords_list) > 3:
        keywords_list = keywords_list[:3]
        logger.warning(f"Limited keywords to first 3: {keywords_list}")
    
    # Initialize PyTrends
    try:
        # Create a custom session with retry strategy
        session = create_retry_session()
        
        # Add proxy to session if provided
        if proxy_info:
            session.proxies.update(proxy_info)
            logger.info("Using proxy for requests")
        
        # Get fresh Google cookies to help avoid rate limiting
        cookies = get_google_cookies()
        
        # Configure PyTrends
        if cookies:
            pytrends = TrendReq(hl='en-US', tz=330)
            pytrends.cookies = cookies
            logger.info("Using custom cookies for Google Trends requests")
        else:
            pytrends = TrendReq(hl='en-US', tz=330)
    except Exception as e:
        logger.error(f"Error initializing PyTrends: {str(e)}")
        try:
            # Fallback to simpler initialization
            pytrends = TrendReq()
        except Exception as e:
            logger.error(f"Failed to initialize PyTrends: {str(e)}")
            return {
                "error": "Failed to initialize Google Trends API",
                "details": str(e)
            }
    
    # Dictionary to store all data
    trends_data = {}
    
    # Flag to track if we should continue with additional requests
    continue_analysis = True
    
    # 1. Fetch time trends data
    if analysis_options['include_time_trends'] and not (analysis_options.get('state_only') or analysis_options.get('city_only')):
        try:
            logger.info(f"Fetching time trends data for {keywords_list}")
            interest_df = get_trends_data(pytrends, keywords_list, timeframe, geo)
            trends_data['time_trends'] = interest_df
            
            if interest_df is None or interest_df.empty:
                logger.warning("Failed to retrieve time trends data")
                continue_analysis = False
        except Exception as e:
            logger.error(f"Error during time trends retrieval: {str(e)}")
            continue_analysis = False
    
    # 2. Fetch region (state/province) data
    if (continue_analysis and analysis_options['include_state_analysis'] and geo) or analysis_options.get('state_only'):
        try:
            # For better performance, use just the first keyword
            region_keywords = [keywords_list[0]] if len(keywords_list) > 0 else keywords_list
            
            # Get region data
            if analysis_options.get('state_only'):
                region_df = get_interest_by_region(pytrends, region_keywords, timeframe, geo, resolution='REGION', max_retries=7)
            else:
                region_df = get_interest_by_region(pytrends, region_keywords, timeframe, geo, resolution='REGION')
            
            trends_data['region_data'] = region_df
            
            if region_df is None or region_df.empty:
                logger.warning("No region data available")
        except Exception as e:
            logger.error(f"Error during region data retrieval: {str(e)}")
    
    # 3. Fetch city data
    if (continue_analysis and analysis_options['include_city_analysis'] and geo) or analysis_options.get('city_only'):
        try:
            # For city data, always use just the first keyword
            city_keyword = [keywords_list[0]] if len(keywords_list) > 0 else keywords_list
            
            # Use a specialized function for city data
            def get_city_data(kw, tf, geo_code, max_retry=5):
                for attempt in range(max_retry):
                    try:
                        if attempt > 0:
                            add_random_delay(15, 30)
                        
                        pytrends.build_payload(kw, cat=0, timeframe=tf, geo=geo_code, gprop='')
                        
                        city_data = pytrends.interest_by_region(
                            resolution='CITY',
                            inc_low_vol=True,
                            inc_geo_code=True
                        )
                        
                        if city_data is not None and not city_data.empty:
                            city_data_detected = any(',' in str(idx) for idx in city_data.index)
                            if city_data_detected:
                                logger.info(f"Successfully retrieved city data on attempt {attempt+1}")
                                return city_data
                    except Exception as e:
                        logger.error(f"Error during city data retrieval (attempt {attempt+1}): {str(e)}")
                
                # Final attempt with fresh session
                try:
                    fresh_pytrends = TrendReq(hl='en-US', tz=330)
                    add_random_delay(30, 60)
                    fresh_pytrends.build_payload(kw, cat=0, timeframe=tf, geo=geo_code, gprop='')
                    final_data = fresh_pytrends.interest_by_region(
                        resolution='CITY',
                        inc_low_vol=True,
                        inc_geo_code=True
                    )
                    return final_data
                except Exception as final_error:
                    logger.error(f"Final city data attempt failed: {str(final_error)}")
                    return None
            
            # Use more retries for city-only mode
            if analysis_options.get('city_only'):
                city_df = get_city_data(city_keyword, timeframe, geo, max_retry=7)
            else:
                city_df = get_city_data(city_keyword, timeframe, geo, max_retry=5)
            
            trends_data['city_data'] = city_df
            
            if city_df is None or city_df.empty:
                logger.warning("No city data available")
        except Exception as e:
            logger.error(f"Error during city data retrieval: {str(e)}")
    
    # 4. Fetch related queries
    if continue_analysis and analysis_options['include_related_queries'] and not (analysis_options.get('state_only') or analysis_options.get('city_only')):
        try:
            logger.info("Fetching related queries")
            related_queries = get_related_queries(pytrends, keywords_list, timeframe, geo)
            trends_data['related_queries'] = related_queries
        except Exception as e:
            logger.error(f"Error during related queries retrieval: {str(e)}")
    
    # Prepare JSON response
    try:
        # Create a JSON-compatible dictionary
        json_data = {
            "metadata": {
                "keywords": keywords_list,
                "timeframe": timeframe,
                "region": geo if geo else "Worldwide",
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "data": {}
        }
        
        # Convert each data type to JSON-compatible format
        if 'time_trends' in trends_data and trends_data['time_trends'] is not None:
            # For time trends, handle the datetime index
            time_df = trends_data['time_trends'].copy()
            # Convert datetime index to string
            time_df.index = time_df.index.strftime('%Y-%m-%d %H:%M:%S')
            json_data['data']['time_trends'] = dataframe_to_json(time_df)
        
        if 'region_data' in trends_data and trends_data['region_data'] is not None:
            json_data['data']['region_data'] = dataframe_to_json(trends_data['region_data'])
        
        if 'city_data' in trends_data and trends_data['city_data'] is not None:
            json_data['data']['city_data'] = dataframe_to_json(trends_data['city_data'])
        
        if 'related_queries' in trends_data and trends_data['related_queries'] is not None:
            # Related queries has a more complex structure
            related_json = {}
            for keyword in trends_data['related_queries']:
                related_json[keyword] = {}
                if 'top' in trends_data['related_queries'][keyword]:
                    related_json[keyword]['top'] = dataframe_to_json(trends_data['related_queries'][keyword]['top'])
                if 'rising' in trends_data['related_queries'][keyword]:
                    related_json[keyword]['rising'] = dataframe_to_json(trends_data['related_queries'][keyword]['rising'])
            
            json_data['data']['related_queries'] = related_json
        
        return json_data
    
    except Exception as e:
        logger.error(f"Error preparing JSON response: {str(e)}")
        return {
            "error": "Failed to prepare trends data",
            "details": str(e)
        }

@csrf_exempt
def trends_api_view(request):
    """
    Django view function to handle Google Trends API requests
    
    Accepts both GET and POST requests:
    - GET: Parameters in query string
    - POST: Parameters in request body (JSON)
    
    Parameters:
    - keywords: Comma-separated list of keywords or JSON array
    - timeframe: Time period (e.g., 'now 1-d', 'today 5-y')
    - geo: Geographic region code (e.g., 'US', 'IN')
    - analysis_type: Integer 1-6 corresponding to analysis options
    
    Returns:
    - JsonResponse with trends data
    """
    try:
        # Get parameters from request
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                keywords = data.get('keywords', '')
                timeframe = data.get('timeframe', 'today 5-y')
                geo = data.get('geo', '')
                analysis_type = data.get('analysis_type', '1')
            except json.JSONDecodeError:
                return JsonResponse({
                    "error": "Invalid JSON in request body"
                }, status=400)
        else:  # GET
            keywords = request.GET.get('keywords', '')
            timeframe = request.GET.get('timeframe', 'today 5-y')
            geo = request.GET.get('geo', '')
            analysis_type = request.GET.get('analysis_type', '1')
        
        # Process keywords
        if isinstance(keywords, list):
            keywords_list = keywords
        else:
            keywords_list = [k.strip() for k in keywords.split(',') if k.strip()]
        
        # Map timeframe code to actual timeframe
        timeframe_map = {
            "1": "now 1-d",
            "2": "now 7-d",
            "3": "today 1-m",
            "4": "today 3-m",
            "5": "today 12-m",
            "6": "today 5-y"
        }
        
        if timeframe in timeframe_map:
            timeframe = timeframe_map[timeframe]
        
        # Map analysis type to options
        analysis_options = {
            "include_time_trends": analysis_type in ["1", "2", "3", "4"],
            "include_state_analysis": analysis_type in ["2", "4", "5"],
            "include_city_analysis": analysis_type in ["3", "4", "6"],
            "include_related_queries": analysis_type == "4",
            "state_only": analysis_type == "5",
            "city_only": analysis_type == "6"
        }
        
        # Get trends data
        result = prepare_trends_data_for_django(keywords_list, timeframe, geo, analysis_options)
        
        # Return JSON response
        return JsonResponse(result, safe=False)
    
    except Exception as e:
        logger.error(f"Error in trends_api_view: {str(e)}")
        return JsonResponse({
            "error": "Failed to process request",
            "details": str(e)
        }, status=500)

# trends_fetcher.py

from pytrends.request import TrendReq
import pandas as pd
import matplotlib.pyplot as plt
import datetime
import time
import random
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import requests

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
    
    # Get region from user (with default option)
    geo_input = input("\nEnter region code (e.g., 'US' for USA, 'IN' for India) or leave blank for worldwide: ").strip()
    geo = geo_input.upper() if geo_input else ''
    
    return keywords_list, timeframe, geo

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

def get_trends_data(pytrends, keywords, timeframe, geo, max_retries=3):
    for attempt in range(max_retries):
        try:
            # Add random delay between 5-15 seconds to avoid rate limiting
            delay = random.uniform(5, 15)
            print(f"Waiting {delay:.2f} seconds before request...")
            time.sleep(delay)
            
            # Build the payload for the request
            pytrends.build_payload(keywords, cat=0, timeframe=timeframe, geo=geo, gprop='')
            
            # Get the interest over time data
            df = pytrends.interest_over_time()
            
            # Check if we got data
            if df is not None and not df.empty:
                print(f"✅ Successfully retrieved data with {len(df)} data points")
                
                # For real-time data (24h), verify it's actually recent
                if timeframe == 'now 1-d':
                    latest_timestamp = df.index[-1]
                    time_diff = datetime.datetime.now() - latest_timestamp
                    if time_diff.total_seconds() > 3600:  # If data is more than 1 hour old
                        print("⚠️ Warning: Data might not be real-time. Retrying...")
                        continue
                
                # For 5-year data, check if we have enough data points
                if timeframe == 'today 5-y' and len(df) < 200:  # Expecting weekly data for 5 years
                    print("⚠️ Warning: Incomplete data for 5-year period. Retrying...")
                    continue
                    
                return df
            else:
                print("⚠️ No data returned from Google Trends API")
                return df
            
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 30  # Exponential backoff
                print(f"⚠️ Rate limited. Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                continue
            elif "quota" in error_msg.lower() and attempt < max_retries - 1:
                wait_time = (attempt + 1) * 60  # Longer wait for quota issues
                print(f"⚠️ Quota exceeded. Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
                continue
            else:
                print(f"❌ Error during data retrieval: {error_msg}")
                raise e

# --------- Main Function ---------
def main():
    # Get user input
    user_keywords, user_timeframe, user_geo = get_user_input()
    
    # --------- Initialize PyTrends ---------
    session = create_retry_session()
    pytrends = TrendReq(hl='en-US', tz=330, requests_args={'verify': True})
    
    try:
        # Show what we're searching for
        print(f"\n🔍 Searching for: {', '.join(user_keywords)}")
        print(f"📅 Timeframe: {user_timeframe}")
        print(f"🌎 Region: {user_geo if user_geo else 'Worldwide'}")
        
        # Initial delay before first request
        print("\nInitial delay before starting...")
        time.sleep(5)
        
        # Fetch data with retry logic
        interest_df = get_trends_data(pytrends, user_keywords, user_timeframe, user_geo)
        
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
    
        if interest_df is not None and not interest_df.empty:
            print("\n🔹 Google Trends Data:")
            print(interest_df.head())
    
            # --------- Plotting ---------
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
                return
    
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
            filename = f"trends_{keywords_text}_{current_time}.png"
            plt.savefig(filename)
            plt.show()
    
            print(f"\n✅ Trend chart saved as: {filename}")
        else:
            print("\n❌ No data returned. This could be due to:")
            print("  - Low search volume for the keyword(s)")
            print("  - Restricted access from your location")
            print("  - Network connectivity issues")
            print("\nTry different keywords, a different timeframe, or check your internet connection.")
    
    except Exception as e:
        print(f"\n❌ Error occurred: {str(e)}")
        if "429" in str(e):
            print("You've been rate limited by Google. Please try again in a few hours or use a VPN/proxy.")
        elif "quota" in str(e).lower():
            print("You've exceeded your quota. Try again later or use a different IP address.")
        else:
            print("An unexpected error occurred. Please check your internet connection and try again.")

# Execute the main function
if __name__ == "__main__":
    main()

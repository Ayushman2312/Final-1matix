from django.http import JsonResponse
from django.views.generic import TemplateView
import logging
import json
import pandas as pd
import numpy as np
from datetime import datetime
import re
import requests
from .models import TrendSearch
from .trends import get_trends_json
import os
from google.generativeai import GenerativeModel
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, InvalidArgument, ServiceUnavailable
from .utils import get_google_api_key, check_api_configuration, EnhancedJSONEncoder, safe_json_dumps
from django.conf import settings
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.shortcuts import render
from django.views.decorators.http import require_http_methods
# from .trends_handler import analyze_trends

logger = logging.getLogger(__name__)

# Configure Google Generative AI API
try:
    GOOGLE_API_KEY = get_google_api_key()
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    logger.error(f"Error configuring Google Generative AI: {str(e)}")
    GOOGLE_API_KEY = None

class TrendsView(TemplateView):
    """
    Main view to display the trends analysis page with interactive charts
    """
    template_name = 'aitrends/trends.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check API configuration status
        api_status = check_api_configuration()
        
        # Get recent searches for display
        try:
            recent_searches = TrendSearch.objects.all().order_by('-created_at')[:5]
        except Exception as e:
            logger.error(f"Error fetching recent searches: {str(e)}")
            recent_searches = []
        
        # Initialize context with default values
        context.update({
            'recent_searches': recent_searches,
            'searched': False,
            'keyword': '',
            'should_auto_fetch': False,  # Default to no auto-fetching
            'analysis_option': '1',  # Default to time trends only
            'google_api_configured': api_status['google_api_configured'],
            'error_message': None  # For displaying any errors
        })
        
        return context
    
    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        # Handle GET request with query parameters (for direct links)
        if 'keyword' in request.GET:
            try:
                keyword = request.GET.get('keyword', '').strip()
                analysis_option = request.GET.get('analysis_option', '1')
                
                if keyword:
                    logger.info(f"GET request with keyword parameter: {keyword}")
                    context['keyword'] = keyword
                    context['searched'] = True
                    context['should_auto_fetch'] = True  # Enable auto-fetch to load charts automatically
                    context['analysis_option'] = analysis_option
                    
                    # Save search to history
                    try:
                        TrendSearch.objects.create(keyword=keyword, country='IN')
                    except Exception as e:
                        logger.error(f"Error saving search to history from GET request: {str(e)}")
            
            except Exception as e:
                logger.error(f"Error processing GET request with keyword: {str(e)}")
        
        # Additional debug logging
        logger.info(f"Rendering trends template with context: searched={context['searched']}, should_auto_fetch={context['should_auto_fetch']}, keyword='{context['keyword']}'")
        
        return self.render_to_response(context)
    
    def post(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        
        try:
            # Get form data
            keyword = request.POST.get('keyword', '').strip()
            analysis_option = request.POST.get('analysis_option', '1')
            direct_submit = request.POST.get('direct_submit', 'false')
            
            logger.info(f"POST request received with keyword='{keyword}', analysis_option='{analysis_option}', direct_submit='{direct_submit}'")
            
            if not keyword:
                logger.warning("Empty keyword submitted")
                context['error_message'] = "Please enter a search term to analyze."
                return self.render_to_response(context)
            
            # Update context with form data
            context['keyword'] = keyword
            context['searched'] = True
            context['should_auto_fetch'] = True  # Enable auto-fetch to load charts automatically
            context['analysis_option'] = analysis_option
            
            # Save search to history
            try:
                TrendSearch.objects.create(keyword=keyword, country='IN')
                logger.info(f"Search saved to history: {keyword}")
            except Exception as e:
                logger.error(f"Error saving search to history: {str(e)}")
            
            # Add debug logging
            logger.info(f"Search submitted for keyword: {keyword}, setting auto_fetch to True, direct_submit={direct_submit}")
            
            # Pre-fetch data for faster rendering if direct_submit is true
            if direct_submit.lower() == 'true':
                logger.info(f"Direct submit detected, pre-fetching data for keyword: {keyword}")
                # Ensure the auto-fetch flag is set to True to trigger chart loading
                context['should_auto_fetch'] = True
        
        except Exception as e:
            logger.error(f"Error processing form submission: {str(e)}", exc_info=True)
            context['error_message'] = "An error occurred while processing your request. Please try again."
        
        return self.render_to_response(context)

from django.views import View

class TrendsApiView(View):
    """
    API endpoint to fetch trends data in JSON format
    """
    def get(self, request, *args, **kwargs):
        keyword = request.GET.get('keyword', '').strip()
        analysis_option = request.GET.get('analysis_option', '1')
        
        # Add a flag parameter to prevent recursive API calls
        auto_triggered_param = request.GET.get('auto_triggered', 'false')
        auto_triggered = auto_triggered_param.lower() in ['true', '1', 'yes']
        
        # Log incoming request
        logger.info(f"trends_api called with keyword='{keyword}', analysis_option='{analysis_option}', auto_triggered={auto_triggered} (raw value: {auto_triggered_param})")
        
        if not keyword:
            logger.warning("API call missing keyword parameter")
            return JsonResponse({
                'error': 'Missing keyword parameter',
                'status': 'error',
                'data': {
                    'time_trends': []
                }
            }, status=400)
        
        # To prevent recursive calls, check if this is manually triggered
        if not auto_triggered:
            try:
                TrendSearch.objects.get_or_create(keyword=keyword, country='IN')
                logger.info(f"Saved search history for keyword: {keyword}")
            except Exception as e:
                logger.error(f"Error saving search history: {str(e)}")
        
        try:
            # Configure analysis options based on user selection
            analysis_options = {
                "include_time_trends": analysis_option in ["1", "2", "3", "4"],
                "include_state_analysis": analysis_option in ["2", "4", "5"],
                "include_city_analysis": analysis_option in ["3", "4", "6"],
                "include_related_queries": analysis_option == "4",
                "state_only": analysis_option == "5",
                "city_only": analysis_option == "6"
            }
            
            # Log the request for debugging
            logger.info(f"Fetching trends for keyword: {keyword}, analysis option: {analysis_option}, options: {analysis_options}")
            
            try:
                # Get trends data using the imported function - explicitly set geo to 'IN' for India
                trends_data = get_trends_json(
                    keywords=[keyword],
                    timeframe='today 5-y',  # Always use 5 years
                    geo='IN',  # Always use India
                    analysis_options=analysis_options  # Pass user-selected options
                )
                
                # Add diagnostic logging for data format
                if trends_data:
                    logger.info(f"Received trends data with keys: {list(trends_data.keys() if trends_data else [])}")
                    
                    if 'data' in trends_data:
                        data_keys = list(trends_data['data'].keys() if trends_data['data'] else [])
                        logger.info(f"Trends data contains data keys: {data_keys}")
                        
                        # Check if we have time_trends data (most important for visualization)
                        if 'time_trends' in data_keys:
                            time_trends_data = trends_data['data']['time_trends']
                            logger.info(f"Time trends data has {len(time_trends_data) if time_trends_data else 0} records")
                        else:
                            logger.warning("No time_trends data in response")
                else:
                    logger.error("get_trends_json returned empty or None response")
                    trends_data = {
                        'status': 'error',
                        'errors': ['Failed to retrieve trends data'],
                        'data': {
                            'time_trends': []
                        }
                    }
                
                # Ensure we have a valid JSON response structure, even if some data is missing
                if not trends_data.get('data'):
                    trends_data['data'] = {}
                
                # Make sure we have the minimum required data structure for the frontend
                for key in ['time_trends', 'region_data', 'city_data', 'related_queries']:
                    if key not in trends_data['data']:
                        if key == 'related_queries':
                            trends_data['data'][key] = {}
                        else:
                            trends_data['data'][key] = []
                
                # Set the status based on whether we have valid data
                has_valid_data = bool(trends_data['data'].get('time_trends')) or \
                                 bool(trends_data['data'].get('region_data')) or \
                                 bool(trends_data['data'].get('city_data'))
                
                if not has_valid_data:
                    trends_data['status'] = 'error'
                    if not trends_data.get('errors'):
                        trends_data['errors'] = ['No valid data retrieved from Google Trends']
                
                # Return the JSON response
                return JsonResponse(trends_data, encoder=EnhancedJSONEncoder)
            
            except Exception as e:
                # Log the detailed error
                logger.error(f"Error fetching trends data: {str(e)}", exc_info=True)
                
                # Return a structured error response
                return JsonResponse({
                    'status': 'error',
                    'errors': [f"Failed to fetch trends data: {str(e)}"],
                    'data': {
                        'time_trends': [],
                        'region_data': [],
                        'city_data': [],
                        'related_queries': {}
                    }
                })
        
        except Exception as e:
            # Catch-all for any unexpected errors
            logger.error(f"Unexpected error in trends API: {str(e)}", exc_info=True)
            
            return JsonResponse({
                'status': 'error',
                'errors': [f"Unexpected error: {str(e)}"],
                'data': {
                    'time_trends': [],
                    'region_data': [],
                    'city_data': [],
                    'related_queries': {}
                }
            })

def get_analysis_info(analysis_option):
    """
    Returns information about what was analyzed based on the selected option
    """
    options = {
        '1': {
            'title': 'Time Trends Analysis',
            'description': 'Time trends data showing search interest over time.',
            'components': ['Time trends']
        },
        '2': {
            'title': 'Regional Analysis',
            'description': 'Time trends data plus state/province level analysis.',
            'components': ['Time trends', 'State/Province analysis']
        },
        '3': {
            'title': 'City-Level Analysis',
            'description': 'Time trends data plus city level analysis.',
            'components': ['Time trends', 'City analysis']
        },
        '4': {
            'title': 'Complete Analysis',
            'description': 'Comprehensive analysis including time trends, regional data, and related queries.',
            'components': ['Time trends', 'State/Province analysis', 'City analysis', 'Related queries']
        },
        '5': {
            'title': 'State/Province Analysis',
            'description': 'Focused analysis of state/province level data without time trends.',
            'components': ['State/Province analysis']
        },
        '6': {
            'title': 'City Analysis',
            'description': 'Focused analysis of city level data without time trends.',
            'components': ['City analysis']
        }
    }
    
    return options.get(analysis_option, options['1'])

class InsightsView(TemplateView):
    """
    View to display AI-generated insights for a specific keyword
    """
    template_name = 'aitrends/insights.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        keyword = kwargs.get('keyword', '')
        analysis_option = self.request.GET.get('analysis_option', '1')
        
        # Get API configuration status
        api_status = check_api_configuration()
        
        context.update({
            'keyword': keyword,
            'insights': None,
            'error': None,
            'analysis_option': analysis_option,
            'google_api_configured': api_status['google_api_configured']
        })
        
        try:
            # Configure analysis options based on user selection
            analysis_options = {
                "include_time_trends": analysis_option in ["1", "2", "3", "4"],
                "include_state_analysis": analysis_option in ["2", "4", "5"],
                "include_city_analysis": analysis_option in ["3", "4", "6"],
                "include_related_queries": analysis_option == "4",
                "state_only": analysis_option == "5",
                "city_only": analysis_option == "6"
            }
            
            # Get trends data for insights
            trends_data = get_trends_json(
                keywords=[keyword],
                timeframe='today 5-y',
                geo='IN',
                analysis_options=analysis_options
            )
            
            if trends_data and 'data' in trends_data and 'time_trends' in trends_data['data']:
                processed_data = process_trends_data(trends_data)
                
                # Check if we have enough data for meaningful insights
                time_series = processed_data.get('time_series', [])
                if len(time_series) < 5:  # Minimum number of data points for insights
                    context['error'] = 'Not enough data points for meaningful insights'
                    return context
                
                # Try to generate insights using AI or fallback to rule-based
                try:
                    insights = generate_insights(processed_data, keyword)
                    
                    # Add source information - whether insights are AI-generated or rule-based
                    if api_status['google_api_configured']:
                        insights['source'] = 'Google AI-powered analysis'
                    else:
                        insights['source'] = 'Statistical analysis'
                    
                    context['insights'] = insights
                    context['analysis_info'] = get_analysis_info(analysis_option)
                except Exception as insight_error:
                    logger.error(f"Error generating insights: {str(insight_error)}")
                    context['error'] = 'Failed to generate insights from trend data'
            else:
                logger.warning(f"No trend data available for keyword: {keyword}")
                context['error'] = 'No data available for this keyword'
        
        except Exception as e:
            logger.error(f"Error in insights_view: {str(e)}", exc_info=True)
            context['error'] = 'An unexpected error occurred while analyzing trends data'
        
        return context

def process_trends_data(trends_data):
    """
    Process the trends data for visualization
    """
    logger.info("Starting trends data processing")
    
    processed = {
        'time_series': [],
        'moving_average': [],
        'trend_line': [],
        'seasonal_pattern': {},
        'year_over_year': {},
        'peak_points': [],
        'region_data': [],  # For state/province data
        'city_data': [],    # For city data
        'metadata': trends_data.get('metadata', {'keywords': ['Unknown'], 'timeframe': 'Unknown', 'region': 'Unknown'})
    }
    
    # Get time series data
    if not trends_data or 'data' not in trends_data:
        logger.warning("Missing data in the response")
        return processed
    
    # Debug info about input data
    logger.info(f"Processing trends data with keys: {list(trends_data.keys())}")
    logger.info(f"Data section contains keys: {list(trends_data['data'].keys())}")
    
    # Process time trends data if available
    if 'time_trends' in trends_data['data'] and trends_data['data']['time_trends']:
        time_data = trends_data['data']['time_trends']
        logger.info(f"Processing {len(time_data)} time trend data points")
        
        try:
            dates = []
            values = []
            keyword = trends_data['metadata']['keywords'][0] if 'metadata' in trends_data and 'keywords' in trends_data['metadata'] and trends_data['metadata']['keywords'] else 'Unknown'
            logger.info(f"Using keyword '{keyword}' for time series processing")
            
            for point in time_data:
                # Check for either 'index' or 'date' field in the data point
                date_field = None
                if 'index' in point:
                    date_field = 'index'
                elif 'date' in point:
                    date_field = 'date'
                
                if not date_field:
                    logger.warning(f"Missing date/index field in data point: {point}")
                    continue
                
                if keyword not in point:
                    logger.warning(f"Missing keyword '{keyword}' in data point: {point}")
                    continue
                
                try:
                    # Convert the date string to a timestamp
                    try:
                        # Try the standard format first
                        date_obj = datetime.strptime(point[date_field], '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        try:
                            # Try alternate format (just date)
                            date_obj = datetime.strptime(point[date_field], '%Y-%m-%d')
                        except ValueError:
                            # Try with a more flexible approach
                            logger.warning(f"Non-standard date format: {point[date_field]}, trying to parse with flexible format")
                            # Try to extract just the date part if it contains date-like patterns
                            date_match = re.search(r'(\d{4}-\d{1,2}-\d{1,2})', str(point[date_field]))
                            if date_match:
                                date_obj = datetime.strptime(date_match.group(1), '%Y-%m-%d')
                            else:
                                raise ValueError(f"Could not parse date: {point[date_field]}")
                    
                    date_str = date_obj.strftime('%Y-%m-%d')
                    value = point[keyword]
                    
                    # Ensure value is numeric
                    if not isinstance(value, (int, float)):
                        try:
                            # Try to convert to float if it's a string
                            value = float(value)
                        except (ValueError, TypeError):
                            logger.warning(f"Non-numeric value in data that couldn't be converted: {value}")
                            continue
                    
                    dates.append(date_str)
                    values.append(value)
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error processing date {point.get(date_field)}: {str(e)}")
            
            # Skip processing if we don't have enough data points
            if len(dates) < 2:
                logger.warning(f"Not enough valid data points: {len(dates)}")
                return processed
            
            # Create the time series data
            processed['time_series'] = [
                {"date": date, "value": value} 
                for date, value in zip(dates, values)
            ]
            
            logger.info(f"Created time series with {len(processed['time_series'])} data points")
            
            # Calculate moving average (13-week window which is ~quarterly)
            if len(values) >= 13:
                try:
                    moving_avg = calculate_moving_average(values, 13)
                    processed['moving_average'] = [
                        {"date": date, "value": avg} 
                        for date, avg in zip(dates[6:-6], moving_avg)
                    ]
                    logger.info(f"Calculated moving average with {len(processed['moving_average'])} data points")
                except Exception as e:
                    logger.error(f"Error calculating moving average: {str(e)}")
            else:
                logger.warning(f"Not enough data points for moving average: {len(values)}")
            
            # Calculate linear trend
            if len(values) >= 2:
                try:
                    trend = calculate_trend_line(values)
                    processed['trend_line'] = [
                        {"date": date, "value": trend_val} 
                        for date, trend_val in zip(dates, trend)
                    ]
                    logger.info(f"Calculated trend line with {len(processed['trend_line'])} data points")
                except Exception as e:
                    logger.error(f"Error calculating trend line: {str(e)}")
            
            # Find peaks (local maxima)
            if len(values) >= 3:
                try:
                    peaks = find_peaks(values, dates)
                    processed['peak_points'] = peaks
                    logger.info(f"Found {len(processed['peak_points'])} peak points")
                except Exception as e:
                    logger.error(f"Error finding peaks: {str(e)}")
            
            # Calculate seasonal patterns
            if len(dates) >= 52:  # At least a year of data
                try:
                    processed['seasonal_pattern'] = calculate_seasonal_pattern(dates, values)
                    logger.info(f"Calculated seasonal pattern data")
                except Exception as e:
                    logger.error(f"Error calculating seasonal pattern: {str(e)}")
            else:
                logger.warning(f"Not enough data for seasonal pattern: {len(dates)} points")
            
            # Calculate year-over-year comparison
            if len(dates) >= 104:  # At least two years of data
                try:
                    processed['year_over_year'] = calculate_year_over_year(dates, values)
                    logger.info(f"Calculated year-over-year comparison data")
                except Exception as e:
                    logger.error(f"Error calculating year-over-year comparison: {str(e)}")
            else:
                logger.warning(f"Not enough data for year-over-year comparison: {len(dates)} points")
        
        except Exception as e:
            logger.error(f"Error processing time trends: {str(e)}", exc_info=True)
    
    # Process regional data if available - check both regions and region_data
    if 'region_data' in trends_data['data'] and trends_data['data']['region_data']:
        try:
            regions = trends_data['data']['region_data']
            processed_regions = []
            
            # Check the format of the data
            if regions and isinstance(regions[0], dict) and 'geoName' in regions[0] and 'values' in regions[0]:
                # New format - already properly structured for bar chart
                processed['region_data'] = regions
                logger.info(f"Processed {len(processed['region_data'])} regions in new format")
            else:
                # Old format with name/value pairs
                for region in regions:
                    if 'name' in region and 'value' in region:
                        processed_regions.append({
                            'name': region['name'],
                            'value': region['value']
                        })
                
                # Sort by value in descending order
                processed['region_data'] = sorted(processed_regions, key=lambda x: x['value'], reverse=True)
                logger.info(f"Processed {len(processed['region_data'])} regions in old format")
            
        except Exception as e:
            logger.error(f"Error processing region data: {str(e)}")
    
    # Process city data if available - check both cities and city_data
    if 'city_data' in trends_data['data'] and trends_data['data']['city_data']:
        try:
            cities = trends_data['data']['city_data']
            processed_cities = []
            
            # Check the format of the data
            if cities and isinstance(cities[0], dict) and 'geoName' in cities[0] and 'values' in cities[0]:
                # New format - already properly structured for bar chart
                processed['city_data'] = cities
                logger.info(f"Processed {len(processed['city_data'])} cities in new format")
            else:
                # Old format with name/value pairs
                for city in cities:
                    if 'name' in city and 'value' in city:
                        processed_cities.append({
                            'name': city['name'],
                            'value': city['value']
                        })
                
                # Sort by value in descending order
                processed['city_data'] = sorted(processed_cities, key=lambda x: x['value'], reverse=True)
                logger.info(f"Processed {len(processed['city_data'])} cities in old format")
            
        except Exception as e:
            logger.error(f"Error processing city data: {str(e)}")
    
    logger.info(f"Completed processing trends data, returning processed data with keys: {list(processed.keys())}")
    return processed

def calculate_moving_average(values, window):
    """Calculate the moving average with the given window size"""
    if len(values) < window:
        return []
    
    # We need to convert to numpy array for efficient calculation
    values_array = np.array(values)
    moving_avg = []
    
    for i in range(window//2, len(values_array) - window//2):
        # Extract the window
        window_data = values_array[i - window//2:i + window//2 + 1]
        # Calculate the average
        avg = np.mean(window_data)
        moving_avg.append(float(avg))
    
    return moving_avg

def calculate_trend_line(values):
    """Calculate a simple linear trend line"""
    x = np.arange(len(values))
    y = np.array(values)
    
    # Calculate the linear trend coefficients (slope and intercept)
    slope, intercept = np.polyfit(x, y, 1)
    
    # Generate the trend line values
    trend_line = slope * x + intercept
    
    return trend_line.tolist()

def find_peaks(values, dates, min_distance=4):
    """Find peak values in the trend data"""
    peaks = []
    
    # Simple peak detection algorithm
    for i in range(1, len(values) - 1):
        if (values[i] > values[i - 1] and 
            values[i] > values[i + 1] and 
            values[i] > np.mean(values) + 0.5 * np.std(values)):
            
            # Check if this peak is far enough from already detected peaks
            if not peaks or min([abs(i - p_idx) for p_idx, _, _ in peaks]) >= min_distance:
                peaks.append((i, dates[i], values[i]))
    
    # Format the peaks data
    formatted_peaks = [
        {"date": date, "value": value, "index": idx}
        for idx, date, value in peaks
    ]
    
    # Limit to top 10 peaks by value
    return sorted(formatted_peaks, key=lambda x: x["value"], reverse=True)[:10]

def calculate_seasonal_pattern(dates, values):
    """Calculate seasonal patterns by month and day of week"""
    months = {}
    weekdays = {}
    
    for i, date_str in enumerate(dates):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        month = date_obj.strftime('%b')  # Jan, Feb, etc.
        weekday = date_obj.strftime('%a')  # Mon, Tue, etc.
        
        if month not in months:
            months[month] = []
        if weekday not in weekdays:
            weekdays[weekday] = []
        
        months[month].append(values[i])
        weekdays[weekday].append(values[i])
    
    # Calculate average for each month and weekday
    month_avg = {month: np.mean(vals) for month, vals in months.items()}
    weekday_avg = {day: np.mean(vals) for day, vals in weekdays.items()}
    
    return {
        "monthly": [{"month": m, "value": v} for m, v in month_avg.items()],
        "weekly": [{"day": d, "value": v} for d, v in weekday_avg.items()]
    }

def calculate_year_over_year(dates, values):
    """Calculate year-over-year comparison"""
    years = {}
    
    for i, date_str in enumerate(dates):
        year = date_str[:4]  # Extract year from date string
        
        if year not in years:
            years[year] = []
        
        years[year].append(values[i])
    
    # Calculate average for each year
    year_avg = {year: np.mean(vals) for year, vals in years.items()}
    
    # Calculate year-over-year growth
    growth = {}
    prev_year = None
    prev_value = None
    
    for year in sorted(year_avg.keys()):
        if prev_year is not None:
            growth[year] = ((year_avg[year] - prev_value) / prev_value) * 100
        
        prev_year = year
        prev_value = year_avg[year]
    
    return {
        "yearly_average": [{"year": yr, "value": val} for yr, val in year_avg.items()],
        "growth": [{"year": yr, "growth": gro} for yr, gro in growth.items()]
    }

def analyze_with_genai(processed_data, keyword):
    """
    Use Google's Generative AI to analyze trends data and generate insights
    """
    api_key = get_google_api_key()
    if not api_key:
        logger.warning("Google Generative AI API key not found. Using fallback analysis.")
        return None
        
    try:
        # Ensure the API is properly configured
        genai.configure(api_key=api_key)
        
        # Extract data for the AI analysis
        time_series = processed_data.get('time_series', [])
        
        if not time_series:
            return None
            
        # Prepare data for AI analysis
        summary_data = {
            "keyword": keyword,
            "time_period": f"from {time_series[0]['date']} to {time_series[-1]['date']}",
            "current_value": time_series[-1]['value'],
            "peak_value": max([point['value'] for point in time_series]),
            "data_points": len(time_series)
        }
        
        # Add trend patterns
        if 'moving_average' in processed_data and processed_data['moving_average']:
            # Check if moving_average contains dictionaries with 'value' key
            if isinstance(processed_data['moving_average'][0], dict) and 'value' in processed_data['moving_average'][0]:
                first_value = processed_data['moving_average'][0]['value']
                last_value = processed_data['moving_average'][-1]['value']
                summary_data["trend_pattern"] = "The trend shows a " + (
                    "consistent upward direction" if last_value > first_value 
                    else "consistent downward direction" if last_value < first_value
                    else "relatively stable pattern"
                )
            # Handle case where moving_average is a list of numeric values
            elif processed_data['moving_average']:
                first_value = processed_data['moving_average'][0]
                last_value = processed_data['moving_average'][-1]
                summary_data["trend_pattern"] = "The trend shows a " + (
                    "consistent upward direction" if last_value > first_value 
                    else "consistent downward direction" if last_value < first_value
                    else "relatively stable pattern"
                )
            
        # Add seasonal information if available
        if 'seasonal_pattern' in processed_data and processed_data['seasonal_pattern']:
            monthly_data = processed_data['seasonal_pattern'].get('monthly', [])
            if monthly_data:
                high_months = sorted(monthly_data, key=lambda x: x['value'], reverse=True)[:3]
                low_months = sorted(monthly_data, key=lambda x: x['value'])[:3]
                
                summary_data["seasonal_peaks"] = [m['month'] for m in high_months]
                summary_data["seasonal_lows"] = [m['month'] for m in low_months]
        
        # Add year-over-year growth information
        if 'year_over_year' in processed_data and processed_data['year_over_year']:
            growth_data = processed_data['year_over_year'].get('growth', [])
            if growth_data:
                summary_data["recent_growth"] = growth_data[-1]['growth']
                
        # Prepare prompt for the AI
        prompt = f"""
        Analyze the following Google Trends data for "{keyword}" in India:
        
        Time period: {summary_data['time_period']}
        Current interest value: {summary_data['current_value']:.2f} (relative to 100 max)
        Peak interest value: {summary_data['peak_value']:.2f}
        
        {summary_data.get('trend_pattern', '')}
        
        {f"Months with highest interest: {', '.join(summary_data.get('seasonal_peaks', []))}" if 'seasonal_peaks' in summary_data else ''}
        {f"Months with lowest interest: {', '.join(summary_data.get('seasonal_lows', []))}" if 'seasonal_lows' in summary_data else ''}
        
        {f"Year-over-year growth: {summary_data.get('recent_growth', 0):.2f}%" if 'recent_growth' in summary_data else ''}
        
        Please provide the following analysis:
        1. A concise summary of the overall trend (2-3 sentences)
        2. 4-5 key insights or observations from the data
        3. An analysis of any seasonal patterns or notable fluctuations
        4. A detailed interpretation of what these trends mean (3-4 paragraphs)
        5. Strategic recommendations based on these trends (3-4 bullet points)
        
        Format the response as structured JSON data with the following keys: 
        "summary", "key_points" (as an array), "seasonal_insights", "trend_analysis", "recommendations" (as an array)
        """
        
        # Call Google's Generative AI
        model = GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        
        # Process the response
        if response and response.text:
            try:
                # Try to extract JSON from the response
                json_text = response.text
                
                # If the response is wrapped in markdown code fences, extract just the JSON part
                json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', json_text, re.DOTALL)
                if json_match:
                    json_text = json_match.group(1)
                
                # Parse the JSON response
                ai_insights = json.loads(json_text)
                
                # Validate the response structure
                required_keys = ["summary", "key_points", "seasonal_insights", "trend_analysis", "recommendations"]
                if all(key in ai_insights for key in required_keys):
                    return ai_insights
                else:
                    missing_keys = [key for key in required_keys if key not in ai_insights]
                    logger.warning(f"AI response missing required keys: {missing_keys}")
                    return None
            
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Error parsing AI response as JSON: {str(e)}")
                return None
    
    except (ResourceExhausted, InvalidArgument, ServiceUnavailable) as api_error:
        logger.error(f"Google Generative AI API error: {str(api_error)}")
        return None
    except Exception as e:
        logger.error(f"Error using Google Generative AI: {str(e)}")
        return None
    
    return None

def generate_insights(processed_data, keyword):
    """
    Generate insights from the trends data using AI analysis
    """
    # First try to get insights from Google Generative AI
    ai_insights = analyze_with_genai(processed_data, keyword)
    
    if ai_insights:
        # Successfully got AI-generated insights
        logger.info("Using AI-generated insights for trends analysis")
        return ai_insights
    
    # Fallback to traditional analysis if AI generation fails
    logger.info("Falling back to rule-based insights generation")
    
    insights = {
        "summary": f"Analysis of search trends for '{keyword}' in India from 2020-2025",
        "key_points": [],
        "trend_analysis": "",
        "seasonal_insights": "",
        "recommendations": []
    }
    
    try:
        # Extract data for analysis
        time_series = processed_data.get('time_series', [])
        
        if not time_series:
            return insights
            
        values = [point['value'] for point in time_series]
        dates = [point['date'] for point in time_series]
        
        # Basic statistics
        current_value = values[-1] if values else 0
        max_value = max(values) if values else 0
        min_value = min(values) if values else 0
        avg_value = np.mean(values) if values else 0
        
        # Trend direction (using last 12 points)
        recent_trend = "upward" if len(values) >= 12 and np.mean(values[-12:]) > np.mean(values[-24:-12]) else "downward"
        
        # Volatility
        volatility = np.std(values) if values else 0
        volatility_level = "high" if volatility > 15 else "moderate" if volatility > 10 else "low"
        
        # Find date of highest interest
        max_index = values.index(max_value) if values else 0
        max_date = dates[max_index] if dates and max_index < len(dates) else "unknown"
        
        # Find seasonality
        seasonal_pattern = processed_data.get('seasonal_pattern', {})
        monthly_pattern = seasonal_pattern.get('monthly', [])
        
        high_months = [item['month'] for item in sorted(monthly_pattern, key=lambda x: x['value'], reverse=True)[:3]] if monthly_pattern else []
        low_months = [item['month'] for item in sorted(monthly_pattern, key=lambda x: x['value'])[:3]] if monthly_pattern else []
        
        # Year-over-year growth
        yoy = processed_data.get('year_over_year', {})
        growth_data = yoy.get('growth', [])
        
        latest_growth = growth_data[-1]['growth'] if growth_data else None
        growth_trend = "increasing" if latest_growth and latest_growth > 0 else "decreasing"
        
        # Compile insights
        insights["key_points"] = [
            f"Current search interest is at {current_value:.1f}% relative to peak interest (100%).",
            f"Peak interest was observed on {max_date}.",
            f"The search trend has been {recent_trend} in recent months.",
            f"Search interest volatility is {volatility_level} (standard deviation: {volatility:.1f})."
        ]
        
        if high_months:
            insights["key_points"].append(f"Highest interest typically occurs in {', '.join(high_months)}.")
        
        if latest_growth is not None:
            insights["key_points"].append(f"Year-over-year search interest is {growth_trend} ({abs(latest_growth):.1f}%).")
        
        # Trend analysis
        insights["trend_analysis"] = f"The search interest for '{keyword}' shows a {recent_trend} trend over the past year. "
        
        if current_value > 80:
            insights["trend_analysis"] += f"Currently, the interest is very high at {current_value:.1f}% relative to the peak. "
        elif current_value > 50:
            insights["trend_analysis"] += f"Currently, the interest is moderate at {current_value:.1f}% relative to the peak. "
        else:
            insights["trend_analysis"] += f"Currently, the interest is relatively low at {current_value:.1f}% relative to the peak. "
        
        # Seasonal insights
        if high_months and low_months:
            insights["seasonal_insights"] = f"There is a clear seasonal pattern with highest interest in {', '.join(high_months)} and lowest interest in {', '.join(low_months)}. "
            
            if volatility_level == "high":
                insights["seasonal_insights"] += "The search interest shows significant fluctuations throughout the year."
            else:
                insights["seasonal_insights"] += "The search interest remains relatively stable throughout the year with some seasonal variation."
        
        # Recommendations
        if recent_trend == "upward":
            insights["recommendations"] = [
                f"Consider increasing marketing efforts for '{keyword}' to capitalize on growing interest.",
                "Analyze what's driving the increased interest and create content addressing those specific topics.",
                "Monitor competitors to see if they're also experiencing increased visibility in this area."
            ]
        else:
            insights["recommendations"] = [
                f"Diversify content strategy beyond just '{keyword}' to offset the declining interest.",
                "Consider creating innovative content to revitalize interest in this topic.",
                "Research related rising keywords that might be replacing this term."
            ]
        
        if high_months:
            insights["recommendations"].append(f"Plan major campaigns or content releases around {', '.join(high_months)} when interest typically peaks.")
        
        return insights
    
    except Exception as e:
        logger.error(f"Error generating insights: {str(e)}")
        insights["summary"] += " (Error generating detailed insights)"
        return insights 

@method_decorator(csrf_exempt, name='dispatch')
class AiInsightsApiView(View):
    """
    API endpoint to generate AI-powered insights from trend data
    """
    def post(self, request, *args, **kwargs):
        try:
            # Parse JSON request body
            data = json.loads(request.body)
            keyword = data.get('keyword', '')
            trend_data = data.get('trend_data', {})
            
            logger.info(f"AI insights requested for keyword: {keyword}")
            
            if not keyword:
                return JsonResponse({
                    'error': 'Missing keyword parameter',
                    'status': 'error'
                }, status=400)
                
            if not trend_data:
                return JsonResponse({
                    'error': 'Missing trend data',
                    'status': 'error'
                }, status=400)
                
            # Get API configuration status
            api_status = check_api_configuration()
            
            if not api_status['google_api_configured']:
                return JsonResponse({
                    'error': 'Google API is not configured',
                    'status': 'error',
                    'insights': {
                        'trend_analysis': 'AI-powered insights not available. Google API is not configured.',
                        'future_scope': 'Feature unavailable without Google API configuration.',
                        'ad_recommendations': 'Feature unavailable without Google API configuration.',
                        'keyword_tips': 'Feature unavailable without Google API configuration.'
                    }
                }, encoder=EnhancedJSONEncoder, status=200)  # Return 200 with minimal insights
                
            # Generate insights using Google Generative AI
            insights = self.generate_comprehensive_insights(keyword, trend_data)
            
            return JsonResponse({
                'status': 'success',
                'insights': insights
            }, encoder=EnhancedJSONEncoder, json_dumps_params={'ensure_ascii': False})
            
        except json.JSONDecodeError:
            return JsonResponse({
                'error': 'Invalid JSON in request body',
                'status': 'error'
            }, status=400)
        except Exception as e:
            logger.error(f"Error generating AI insights: {str(e)}", exc_info=True)
            return JsonResponse({
                'error': f'Failed to generate insights: {str(e)}',
                'status': 'error'
            }, encoder=EnhancedJSONEncoder, status=500)
            
    def generate_comprehensive_insights(self, keyword, trend_data):
        """
        Generate comprehensive insights using Google Generative AI
        """
        try:
            # Configure Google Generative AI
            api_key = get_google_api_key()
            if not api_key:
                return {
                    'trend_analysis': 'AI-powered insights not available. Google API key not found.',
                    'future_scope': 'Feature unavailable.',
                    'ad_recommendations': 'Feature unavailable.',
                    'keyword_tips': 'Feature unavailable.'
                }
                
            genai.configure(api_key=api_key)
            
            # Extract relevant trend information
            try:
                # Format the trend data information
                trend_stats = trend_data.get('trendStats', {})
                
                peak_interest = trend_stats.get('peakInterest', {})
                peak_value = peak_interest.get('value', 0)
                peak_date = peak_interest.get('date', 'unknown')
                
                lowest_interest = trend_stats.get('lowestInterest', {})
                lowest_value = lowest_interest.get('value', 0)
                lowest_date = lowest_interest.get('date', 'unknown')
                
                overall_trend = trend_stats.get('overallTrend', {})
                trend_direction = overall_trend.get('direction', 'stable')
                trend_percentage = overall_trend.get('percentage', '0')
                
                seasonality = trend_stats.get('seasonality', {})
                highest_month = seasonality.get('highestMonth', 'unknown')
                lowest_month = seasonality.get('lowestMonth', 'unknown')
                
                recent_trend = trend_stats.get('recentTrend', 'mixed')
                
                # Prepare prompt for the AI to generate insights
                prompt = f"""
                Analyze the following Google Trends data for "{keyword}" in India:
                
                Peak Interest: {peak_value} on {peak_date}
                Lowest Interest: {lowest_value} on {lowest_date}
                Overall Trend: Interest is {trend_direction} by {trend_percentage}% over the analyzed period
                Seasonal Pattern: Interest tends to be highest in {highest_month} and lowest in {lowest_month}
                Recent Trend: {recent_trend}
                
                I need a comprehensive analysis with EXACTLY these four sections:
                
                1. TREND ANALYSIS: Provide a detailed analysis of the search trend patterns. What does the data tell us about user interest over time? What factors might be influencing these patterns? (2-3 paragraphs)
                
                2. FUTURE SCOPE: Based on the trend data, assess the future potential and scope of success for this keyword. Is interest growing or declining? Is this a promising area to focus on? (1-2 paragraphs)
                
                3. ADVERTISING RECOMMENDATIONS: Provide specific recommendations for creating effective ads targeting this keyword. Include suggestions on ad timing (based on seasonal patterns), messaging approach, and targeting strategy. (2-3 paragraphs)
                
                4. KEYWORD USAGE TIPS: Offer practical tips for using this keyword effectively for selling or marketing purposes. Include suggestions on related keywords, content strategy, and optimizing for this particular search term. (1-2 paragraphs)
                
                Format your response as a JSON object with these exact keys: trend_analysis, future_scope, ad_recommendations, keyword_tips. Each value should be a string containing only the relevant analysis text with no headings, introductions or formatting.
                """
                
                # Call Google's Generative AI model
                model = GenerativeModel('gemini-pro')
                response = model.generate_content(prompt)
                
                # Parse the JSON response
                if response and response.text:
                    # Extract JSON from the response text if needed
                    json_text = response.text
                    
                    # Check if the response is wrapped in markdown code fences and extract
                    json_match = re.search(r'```(?:json)?\s*(.*?)\s*```', json_text, re.DOTALL)
                    if json_match:
                        json_text = json_match.group(1)
                    
                    # Parse the JSON
                    insights = json.loads(json_text)
                    
                    # Validate that all required sections are present
                    required_keys = ['trend_analysis', 'future_scope', 'ad_recommendations', 'keyword_tips']
                    for key in required_keys:
                        if key not in insights:
                            insights[key] = f"No {key.replace('_', ' ')} available."
                    
                    return insights
                
            except Exception as parsing_error:
                logger.error(f"Error parsing AI response: {str(parsing_error)}")
                
                # Fallback to direct text extraction if JSON parsing fails
                if response and response.text:
                    text = response.text
                    
                    # Attempt to extract sections using regex
                    trend_analysis = re.search(r'trend analysis:?\s*(.*?)(?:future scope|$)', text, re.IGNORECASE | re.DOTALL)
                    future_scope = re.search(r'future scope:?\s*(.*?)(?:advertising recommendations|$)', text, re.IGNORECASE | re.DOTALL)
                    ad_recommendations = re.search(r'advertising recommendations:?\s*(.*?)(?:keyword usage tips|$)', text, re.IGNORECASE | re.DOTALL)
                    keyword_tips = re.search(r'keyword usage tips:?\s*(.*?)(?:$)', text, re.IGNORECASE | re.DOTALL)
                    
                    return {
                        'trend_analysis': trend_analysis.group(1).strip() if trend_analysis else 'Trend analysis not available.',
                        'future_scope': future_scope.group(1).strip() if future_scope else 'Future scope analysis not available.',
                        'ad_recommendations': ad_recommendations.group(1).strip() if ad_recommendations else 'Advertising recommendations not available.',
                        'keyword_tips': keyword_tips.group(1).strip() if keyword_tips else 'Keyword usage tips not available.'
                    }
            
            # Fallback if all else fails
            return {
                'trend_analysis': 'Unable to generate trend analysis.',
                'future_scope': 'Unable to assess future scope.',
                'ad_recommendations': 'Unable to provide advertising recommendations.',
                'keyword_tips': 'Unable to offer keyword usage tips.'
            }
            
        except Exception as e:
            logger.error(f"Error generating comprehensive insights: {str(e)}", exc_info=True)
            return {
                'trend_analysis': f'Error generating insights: {str(e)}',
                'future_scope': 'Analysis failed.',
                'ad_recommendations': 'Analysis failed.',
                'keyword_tips': 'Analysis failed.'
            }

def trends_view(request):
    """Render the trends analysis page."""
    return render(request, 'trends/trends.html')

@csrf_exempt
@require_http_methods(["GET", "POST"])
def trends_api(request):
    """Handle trends analysis API requests."""
    try:
        if request.method == "POST":
            try:
                data = json.loads(request.body)
                logger.info(f"Received POST data: {data}")
            except json.JSONDecodeError:
                logger.error("Invalid JSON data in POST request")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Invalid JSON data'
                }, status=400)

            # Get keyword and analysis_type from request data
            keyword = data.get('keyword', '').strip()
            timeframe = data.get('timeframe', 'today 5-y')  # Default: 5 years
            geo = data.get('geo', 'IN')  # Default: India
            analysis_type = data.get('analysis_type', '1')  # Default: basic time trends

            if not keyword:
                logger.warning("Missing keyword in trends API request")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Keyword is required'
                }, status=400)

            logger.info(f"Processing trends API request for keyword: {keyword}, analysis_type: {analysis_type}")
            
            # Convert analysis_type to analysis_options dictionary
            analysis_options = {
                "include_time_trends": analysis_type in ["1", "2", "3", "4"],
                "include_state_analysis": analysis_type in ["2", "4", "5"],
                "include_city_analysis": analysis_type in ["3", "4", "6"],
                "include_related_queries": analysis_type == "4",
                "state_only": analysis_type == "5",
                "city_only": analysis_type == "6"
            }
            
            # Get trends data
            try:
                trends_data = get_trends_json(
                    keywords=keyword,
                    timeframe=timeframe,
                    geo=geo,
                    analysis_options=analysis_options
                )
                
                logger.info(f"Successfully retrieved trends data for {keyword}")
                
                if not trends_data:
                    logger.error(f"Failed to retrieve trends data for {keyword}")
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Failed to retrieve trends data. Please try again later.'
                    }, status=500)
                
                return JsonResponse({
                    'status': 'success',
                    'data': trends_data
                })
            except Exception as e:
                logger.error(f"Error retrieving trends data: {str(e)}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'Error retrieving trends data: {str(e)}'
                }, status=500)

        else:  # GET request
            keyword = request.GET.get('keyword', '').strip()
            timeframe = request.GET.get('timeframe', 'today 5-y')
            geo = request.GET.get('geo', 'IN')
            analysis_type = request.GET.get('analysis_type', '1')

            if not keyword:
                logger.warning("Missing keyword in trends API GET request")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Keyword is required'
                }, status=400)

            logger.info(f"Processing trends API GET request for keyword: {keyword}")
            
            # Convert analysis_type to analysis_options dictionary
            analysis_options = {
                "include_time_trends": analysis_type in ["1", "2", "3", "4"],
                "include_state_analysis": analysis_type in ["2", "4", "5"],
                "include_city_analysis": analysis_type in ["3", "4", "6"],
                "include_related_queries": analysis_type == "4",
                "state_only": analysis_type == "5",
                "city_only": analysis_type == "6"
            }
                
            # Get trends data
            try:
                trends_data = get_trends_json(
                    keywords=keyword,
                    timeframe=timeframe,
                    geo=geo,
                    analysis_options=analysis_options
                )
                
                if not trends_data:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Failed to retrieve trends data. Please try again later.'
                    }, status=500)
                print(trends_data)
                
                return JsonResponse({
                    'status': 'success',
                    'data': trends_data
                })
            except Exception as e:
                logger.error(f"Error retrieving trends data: {str(e)}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'Error retrieving trends data: {str(e)}'
                }, status=500)
    except Exception as e:
        logger.error(f"Error in trends_api: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def insights_view(request, keyword=None):
    """Render the insights page for a specific keyword."""
    if not keyword:
        return render(request, 'trends/insights.html')
    return render(request, 'trends/insights.html', {'keyword': keyword})

@csrf_exempt
@require_http_methods(["POST"])
def ai_insights_api(request):
    """Handle AI-powered insights API requests."""
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON data in AI insights API request")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
            
        keyword = data.get('keyword')
        trend_data = data.get('trend_data')

        if not keyword or not trend_data:
            logger.warning("Missing required data in AI insights API request")
            return JsonResponse({
                'status': 'error',
                'message': 'Both keyword and trend data are required'
            }, status=400)

        # TODO: Implement AI insights generation
        logger.info(f"AI insights requested for keyword: {keyword}")
        return JsonResponse({
            'status': 'success',
            'message': 'AI insights generation coming soon'
        })

    except Exception as e:
        logger.error(f"Error in ai_insights_api: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500) 
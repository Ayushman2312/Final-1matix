from ast import arg
from doctest import Example
from string import digits
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
from trends.serp import fetch_serp_trends

logger = logging.getLogger(__name__)

# Configure Google Generative AI API
try:
    GOOGLE_API_KEY = get_google_api_key()
    if GOOGLE_API_KEY:
        genai.configure(api_key=GOOGLE_API_KEY)
except Exception as e:
    logger.error(f"Error configuring Google Generative AI: {str(e)}")
    GOOGLE_API_KEY = None

# PageSpeed Insights API key (you can use API_KEY from GOOGLE_API_KEY or set a separate one)
PAGESPEED_API_KEY = "AIzaSyCtlv3d3rD8C2E5YDDJl1ozNWwcNyrcTYE"

def analyze_website_with_pagespeed(website_url):
    """
    Analyze a website using Google PageSpeed Insights API with a simplified approach
    
    Args:
        website_url: The URL of the website to analyze
        
    Returns:
        Dictionary with pagespeed insights data or None if error
    """
    if not website_url:
        logger.warning("No website URL provided for PageSpeed analysis")
        return None
        
    # Ensure URL has proper format
    if not website_url.startswith('http'):
        website_url = f"https://{website_url}"
    
    try:
        # Remove trailing slashes for consistency
        website_url = website_url.rstrip('/')
        
        # Use the simplified function
        result = get_pagespeed_insights(website_url, PAGESPEED_API_KEY)
        
        # Check if we got an error response from the API
        if result and 'error' in result:
            logger.warning(f"Error analyzing {website_url} with PageSpeed: {result['error']}")
            
            # Check specifically for quota exceeded errors
            if '429' in str(result['error']):
                logger.warning("PageSpeed API quota exceeded, generating mock data instead")
                return generate_mock_pagespeed_data(website_url)
                
            return result
            
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing {website_url} with PageSpeed: {str(e)}")
        return {"error": str(e), "url": website_url}

def get_pagespeed_insights(url, api_key):
    """
    Simplified function to get PageSpeed Insights data
    
    Args:
        url: The URL to analyze
        api_key: Google API key
        
    Returns:
        Dictionary with pagespeed insights data
    """
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {
        "url": url,
        "key": api_key,
        "strategy": "mobile",  # You can also call with "desktop"
    }

    try:
        response = requests.get(endpoint, params=params, timeout=15)
        
        # Handle quota exceeded errors explicitly
        if response.status_code == 429:
            logger.warning(f"PageSpeed API quota exceeded for {url}")
            return {"error": "HTTP error! status: 429 - Quota exceeded", "url": url}
            
        if not response.ok:
            return {"error": f"HTTP error! status: {response.status_code}", "url": url}
            
        data = response.json()

        lighthouse = data.get('lighthouseResult', {})
        categories = lighthouse.get('categories', {})

        performance_score = categories.get('performance', {}).get('score', 0) * 100
        seo_score = categories.get('seo', {}).get('score', 0) * 100
        accessibility_score = categories.get('accessibility', {}).get('score', 0) * 100
        best_practices_score = categories.get('best-practices', {}).get('score', 0) * 100

        # First Contentful Paint
        fcp = lighthouse.get('audits', {}).get('first-contentful-paint', {}).get('displayValue', 'N/A')
        
        # Get additional metrics for completeness
        lcp = lighthouse.get('audits', {}).get('largest-contentful-paint', {}).get('displayValue', 'N/A')
        cls = lighthouse.get('audits', {}).get('cumulative-layout-shift', {}).get('displayValue', 'N/A')
        tbt = lighthouse.get('audits', {}).get('total-blocking-time', {}).get('displayValue', 'N/A')
        si = lighthouse.get('audits', {}).get('speed-index', {}).get('displayValue', 'N/A')
        tti = lighthouse.get('audits', {}).get('interactive', {}).get('displayValue', 'N/A')
        
        # Extract opportunities (potential improvements)
        opportunities = []
        passed_audits = []
        audits = lighthouse.get('audits', {})
        for audit_id, audit in audits.items():
            if audit.get('details', {}).get('type') == 'opportunity' and audit.get('score', 1) < 1:
                opportunities.append(audit.get('title', ''))
            elif audit.get('score', 0) == 1:
                passed_audits.append(audit.get('title', ''))
        
        # Format the response to match what our code expects
        return {
            "scores": {
                "performance": performance_score,
                "seo": seo_score,
                "accessibility": accessibility_score,
                "best-practices": best_practices_score
            },
            "metrics": {
                "first-contentful-paint": {"display_value": fcp},
                "largest-contentful-paint": {"display_value": lcp},
                "cumulative-layout-shift": {"display_value": cls},
                "total-blocking-time": {"display_value": tbt},
                "speed-index": {"display_value": si},
                "interactive": {"display_value": tti}
            },
            "opportunities": opportunities[:5],  # Top 5 opportunities
            "passed_audits": passed_audits[:5],  # Top 5 passed audits
            "summary": f"Performance: {performance_score:.0f}%, SEO: {seo_score:.0f}%, Accessibility: {accessibility_score:.0f}%, Best Practices: {best_practices_score:.0f}%",
            "url": url,
            "analyzed_at": datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error in get_pagespeed_insights: {str(e)}")
        return {"error": str(e), "url": url}

class TrendsView(TemplateView):
    """
    Main view to display the trends analysis page with interactive charts
    """
    template_name = 'aitrends/trends.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check API configuration status
        api_status = check_api_configuration()
        
        # Get recent searches for display - filter by user if authenticated
        try:
            if self.request.user.is_authenticated:
                recent_searches = TrendSearch.objects.filter(user=self.request.user).order_by('-timestamp')[:5]
                logger.info(f"Fetched user-specific recent searches for user {self.request.user.id}")
            else:
                # For anonymous users, show only anonymous searches
                recent_searches = TrendSearch.objects.filter(user__isnull=True).order_by('-timestamp')[:5]
                logger.info("Fetched anonymous recent searches")
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
                    
                    # Save search to history with user association if authenticated
                    try:
                        if request.user.is_authenticated:
                            TrendSearch.objects.create(keyword=keyword, country='IN', user=request.user)
                            logger.info(f"Saved search with user association: User {request.user.id}, Keyword: {keyword}")
                        else:
                            TrendSearch.objects.create(keyword=keyword, country='IN')
                            logger.info(f"Saved anonymous search: {keyword}")
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
            
            # Save search to history with user association if authenticated
            try:
                if request.user.is_authenticated:
                    TrendSearch.objects.create(keyword=keyword, country='IN', user=request.user)
                    logger.info(f"Search saved to history for user {request.user.id}: {keyword}")
                else:
                    TrendSearch.objects.create(keyword=keyword, country='IN')
                    logger.info(f"Anonymous search saved to history: {keyword}")
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
                # Associate search with user if authenticated
                if request.user.is_authenticated:
                    TrendSearch.objects.get_or_create(keyword=keyword, country='IN', user=request.user)
                    logger.info(f"Saved search history for user {request.user.id}, keyword: {keyword}")
                else:
                    TrendSearch.objects.get_or_create(keyword=keyword, country='IN')
                    logger.info(f"Saved anonymous search history for keyword: {keyword}")
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
            # Save this keyword to the user's search history if not already there
            if keyword and self.request.user.is_authenticated:
                TrendSearch.objects.get_or_create(
                    keyword=keyword, 
                    country='IN',
                    user=self.request.user
                )
                logger.info(f"Saved insight view for user {self.request.user.id}, keyword: {keyword}")
            elif keyword:
                # For anonymous users
                TrendSearch.objects.get_or_create(keyword=keyword, country='IN')
                logger.info(f"Saved anonymous insight view for keyword: {keyword}")
            
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
    api_key = "AIzaSyDsXH-_ftI5xn4aWfkwpw__4ixUMs7a7fM"
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
        model = genai.GenerativeModel('gemini-2.0-flash')
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
            use_serp_api = data.get('use_serp_api', False)  # Special flag to force SERP API usage

            if not keyword:
                logger.warning("Missing keyword in trends API request")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Keyword is required'
                }, status=400)

            logger.info(f"Processing trends API request for keyword: {keyword}, analysis_type: {analysis_type}, use_serp_api: {use_serp_api}")
            
            # Save search to history with user association if authenticated
            try:
                if request.user.is_authenticated:
                    TrendSearch.objects.get_or_create(keyword=keyword, country=geo, user=request.user)
                    logger.info(f"Saved API search for user {request.user.id}, keyword: {keyword}")
                else:
                    TrendSearch.objects.get_or_create(keyword=keyword, country=geo)
                    logger.info(f"Saved anonymous API search for keyword: {keyword}")
            except Exception as e:
                logger.error(f"Error saving search history from API: {str(e)}")
            
            # Convert analysis_type to analysis_options dictionary
            if analysis_type == '2':  # Regional Analysis
                analysis_options = {
                    "include_time_trends": False,
                    "include_state_analysis": True,
                    "include_city_analysis": False,
                    "include_related_queries": False,
                    "state_only": True,
                    "city_only": False,
                    "analysis_type": analysis_type
                }
                logger.info(f"Using Regional Analysis options: include_time_trends=False, state_only=True")
            elif analysis_type == '6':  # City Analysis
                analysis_options = {
                    "include_time_trends": False,
                    "include_state_analysis": False,
                    "include_city_analysis": True,
                    "include_related_queries": False, 
                    "state_only": False,
                    "city_only": True,
                    "analysis_type": analysis_type
                }
                logger.info(f"Using City Analysis options: include_time_trends=False, city_only=True")
            elif analysis_type == '7':  # Complete Analysis
                analysis_options = {
                    "include_time_trends": True,
                    "include_state_analysis": True,
                    "include_city_analysis": True,
                    "include_related_queries": True,
                    "state_only": False,
                    "city_only": False,
                    "analysis_type": analysis_type
                }
                logger.info(f"Using Complete Analysis options: include_time_trends=True, include_state_analysis=True")
            else:  # Default Time Trends Analysis
                analysis_options = {
                    "include_time_trends": True,
                    "include_state_analysis": False,
                    "include_city_analysis": False,
                    "include_related_queries": False,
                    "state_only": False,
                    "city_only": False,
                    "analysis_type": analysis_type
                }
                logger.info(f"Using Time Trends Analysis options: include_time_trends=True")
            
            # Add use_serp_api flag to analysis_options if specified
            if use_serp_api:
                analysis_options["use_serp_api"] = True
                logger.info("Force using SERP API for this request")
            
            # Get trends data
            try:
                if use_serp_api and analysis_type == '2':
                    # Direct SERP API call for regional data
                    logger.info(f"Making direct SERP API call for regional data for keyword: {keyword}")
                    serp_result = fetch_serp_trends(
                        keyword=keyword,
                        timeframe=timeframe,
                        geo=geo,
                        analysis_options=analysis_options
                    )
                    
                    if serp_result:
                        logger.info(f"Successfully retrieved SERP API regional data for {keyword}")
                        return JsonResponse(serp_result)
                    else:
                        logger.error(f"Failed to retrieve SERP API regional data for {keyword}")
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Failed to retrieve regional data from SERP API. Please try again later.'
                        }, status=500)
                
                # Normal flow using get_trends_json
                trends_data = get_trends_json(
                    keywords=keyword,
                    timeframe=timeframe,
                    geo=geo,
                    analysis_options=analysis_options
                )
                print(trends_data)
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
            
            # Save search to history with user association if authenticated
            try:
                if request.user.is_authenticated:
                    TrendSearch.objects.get_or_create(keyword=keyword, country=geo, user=request.user)
                    logger.info(f"Saved API GET search for user {request.user.id}, keyword: {keyword}")
                else:
                    TrendSearch.objects.get_or_create(keyword=keyword, country=geo)
                    logger.info(f"Saved anonymous API GET search for keyword: {keyword}")
            except Exception as e:
                logger.error(f"Error saving search history from API GET: {str(e)}")
            
            # Convert analysis_type to analysis_options dictionary
            if analysis_type == '2':  # Regional Analysis
                analysis_options = {
                    "include_time_trends": False,
                    "include_state_analysis": True,
                    "include_city_analysis": False,
                    "include_related_queries": False,
                    "state_only": True,
                    "city_only": False,
                    "analysis_type": analysis_type
                }
                logger.info(f"Using Regional Analysis options: include_time_trends=False, state_only=True")
            elif analysis_type == '6':  # City Analysis
                analysis_options = {
                    "include_time_trends": False,
                    "include_state_analysis": False,
                    "include_city_analysis": True,
                    "include_related_queries": False, 
                    "state_only": False,
                    "city_only": True,
                    "analysis_type": analysis_type
                }
                logger.info(f"Using City Analysis options: include_time_trends=False, city_only=True")
            elif analysis_type == '7':  # Complete Analysis
                analysis_options = {
                    "include_time_trends": True,
                    "include_state_analysis": True,
                    "include_city_analysis": True,
                    "include_related_queries": True,
                    "state_only": False,
                    "city_only": False,
                    "analysis_type": analysis_type
                }
                logger.info(f"Using Complete Analysis options: include_time_trends=True, include_state_analysis=True")
            else:  # Default Time Trends Analysis
                analysis_options = {
                    "include_time_trends": True,
                    "include_state_analysis": False,
                    "include_city_analysis": False,
                    "include_related_queries": False,
                    "state_only": False,
                    "city_only": False,
                    "analysis_type": analysis_type
                }
                logger.info(f"Using Time Trends Analysis options: include_time_trends=True")
                
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
    
    # Save this keyword to the user's search history
    try:
        if keyword and request.user.is_authenticated:
            TrendSearch.objects.get_or_create(keyword=keyword, country='IN', user=request.user)
            logger.info(f"Saved insights view for user {request.user.id}, keyword: {keyword}")
        elif keyword:
            TrendSearch.objects.get_or_create(keyword=keyword, country='IN')
            logger.info(f"Saved anonymous insights view for keyword: {keyword}")
    except Exception as e:
        logger.error(f"Error saving search history from insights view: {str(e)}")
    
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

@csrf_exempt
@require_http_methods(["POST"])
def ai_analysis_api(request):
    """
    API endpoint for generating AI analysis and recommendations for trends data.
    Takes a keyword and trend data as input and returns analysis and recommendations.
    """
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON data in AI analysis API request")
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid JSON data'
            }, status=400)
            
        keyword = data.get('keyword')
        trend_data = data.get('data')
        business_intent = data.get('business_intent', '')  # Get the business_intent value
        
        # Extract additional variables from the request
        brand_name = data.get('brand_name', '')
        user_website = data.get('user_website', '')
        marketplaces_selected = data.get('marketplaces_selected', '')
        
        # Extract PageSpeed Insights data if available
        pagespeed_data = data.get('pagespeed_insights')
        
        # Normalize pagespeed_data if it's a string (some clients might send JSON string)
        if pagespeed_data and isinstance(pagespeed_data, str):
            try:
                pagespeed_data = json.loads(pagespeed_data)
                logger.info("Parsed pagespeed_data from string format")
            except json.JSONDecodeError:
                logger.warning("Received pagespeed_data as string but couldn't parse as JSON")
                pagespeed_data = None
                
        # Improved logging to diagnose the issue
        has_pagespeed = pagespeed_data is not None
        pagespeed_keys = list(pagespeed_data.keys()) if has_pagespeed and isinstance(pagespeed_data, dict) else []
        
        logger.info(
            f"Received AI analysis request for keyword: {keyword} with business_intent: {business_intent}, "
            f"brand_name: {brand_name}, website: {user_website}, "
            f"pagespeed_data: {has_pagespeed}, keys: {pagespeed_keys}"
        )

        if not keyword:
            logger.warning("Missing keyword in AI analysis API request")
            return JsonResponse({
                'status': 'error',
                'message': 'Keyword is required'
            }, status=400)

        if not trend_data:
            logger.warning("Missing trend data in AI analysis API request")
            return JsonResponse({
                'status': 'error',
                'message': 'Trend data is required'
            }, status=400)

        # Save this keyword to the user's search history
        try:
            if request.user.is_authenticated:
                TrendSearch.objects.get_or_create(keyword=keyword, country='IN', user=request.user)
                logger.info(f"Saved AI analysis search for user {request.user.id}, keyword: {keyword}")
            else:
                TrendSearch.objects.get_or_create(keyword=keyword, country='IN')
                logger.info(f"Saved anonymous AI analysis search for keyword: {keyword}")
        except Exception as e:
            logger.error(f"Error saving search history from AI analysis: {str(e)}")

        logger.info(f"Generating AI analysis for keyword: {keyword}")
        
        # Process the trend data to extract insights
        try:
            # Extract key metrics for analysis
            metrics = extract_trend_metrics(trend_data, keyword)
            
            # Use Google Generative AI for analysis when API key is available
            if GOOGLE_API_KEY:
                try:
                    # Generate analysis using AI, including business_intent and additional variables
                    analysis, recommendations = analyze_with_generative_ai(
                        keyword, 
                        metrics, 
                        trend_data, 
                        business_intent,
                        brand_name,
                        user_website,
                        marketplaces_selected,
                        pagespeed_data
                    )
                    
                    return JsonResponse({
                        'status': 'success',
                        'analysis': analysis,
                        'recommendations': recommendations,
                        'isAi': True
                    })
                except Exception as gen_err:
                    logger.error(f"Error using generative AI for trend analysis: {str(gen_err)}", exc_info=True)
                    logger.info("Falling back to algorithmic analysis")
                    
                    # Fall back to algorithmic analysis if AI fails
                    analysis = generate_trend_analysis(keyword, metrics)
                    recommendations = generate_trend_recommendations(keyword, metrics)
                    
                    return JsonResponse({
                        'status': 'success',
                        'analysis': analysis,
                        'recommendations': recommendations
                    })
            else:
                # If no API key, use algorithmic analysis
                logger.info("No Google API key configured, using algorithmic analysis")
                analysis = generate_trend_analysis(keyword, metrics)
                recommendations = generate_trend_recommendations(keyword, metrics)
                
                return JsonResponse({
                    'status': 'success',
                    'analysis': analysis,
                    'recommendations': recommendations
                })
                
        except Exception as e:
            logger.error(f"Error generating AI analysis: {str(e)}", exc_info=True)
            return JsonResponse({
                'status': 'error',
                'message': f'Error generating analysis: {str(e)}'
            }, status=500)

    except Exception as e:
        logger.error(f"Error in ai_analysis_api: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)

def analyze_with_generative_ai(keyword, metrics, trend_data, business_intent='', brand_name='', user_website='', marketplaces_selected='', pagespeed_data=None):
    """
    Use Google's Generative AI model to analyze trends data and provide recommendations.
    
    Args:
        keyword: The search keyword
        metrics: Dictionary of metrics extracted from trend data
        trend_data: The original trend data
        business_intent: Optional string indicating if user wants to start a business ('yes', 'no', 'not_sure')
        brand_name: Optional string indicating the brand name
        user_website: Optional string indicating the user's website
        marketplaces_selected: Optional string indicating the marketplaces selected
        pagespeed_data: Optional PageSpeed Insights data for website audit
        
    Returns:
        Tuple of (analysis, recommendations) strings
    """
    try:
        # More detailed logging of received PageSpeed data
        if pagespeed_data:
            print(pagespeed_data)
            if isinstance(pagespeed_data, dict):
                logger.info(f"PageSpeed data received for analysis as dictionary with keys: {list(pagespeed_data.keys())}")
                # Check for mock data flag
                if pagespeed_data.get('is_mock_data', False):
                    logger.info("Using mock PageSpeed data for analysis (API quota exceeded)")
            elif isinstance(pagespeed_data, str):
                logger.info(f"PageSpeed data received for analysis as string of length: {len(pagespeed_data)}")
                try:
                    # Try to parse if it's a JSON string
                    parsed_data = json.loads(pagespeed_data)
                    logger.info(f"Successfully parsed PageSpeed string data with keys: {list(parsed_data.keys())}")
                    pagespeed_data = parsed_data
                except json.JSONDecodeError:
                    logger.warning("Received PageSpeed data as string but couldn't parse as JSON")
            else:
                logger.info(f"PageSpeed data received for analysis with type: {type(pagespeed_data)}")
        else:
            logger.info("No PageSpeed data received for analysis")
            
        # Initialize the generative model
        model = genai.GenerativeModel(model_name="gemini-2.0-flash")
        
        # Format the data for analysis
        formatted_metrics = {
            "keyword": keyword,
            "overall_trend": metrics["overall_trend"],
            "growth_rate": metrics["growth_rate"],
            "volatility": metrics["volatility"],
            "volatility_value": metrics["volatility_value"],
            "peak_periods": [{"date": p["date"], "value": p["value"]} for p in metrics["peak_periods"]],
            "trough_periods": [{"date": p["date"], "value": p["value"]} for p in metrics["trough_periods"]],
            "seasonal": metrics["seasonal"],
            "recent_direction": metrics["recent_direction"],
            "business_intent": business_intent,  # Add business intent to metrics
            "brand_name": brand_name,
            "user_website": user_website,
            "marketplaces_selected": marketplaces_selected
        }
        
        # Create a concise data summary to send to the API
        data_summary = safe_json_dumps(formatted_metrics)
        
        # Create the analysis prompt
        analysis_prompt = f"""
            You are a search trend analyst working for TrendIQ. You are analyzing market demand data for the keyword: "{keyword}"

            Here is the raw data and pattern summary:
            {data_summary}

            Your task is to give a clean, factual, easy-to-understand analysis of the search pattern for this keyword.

            Use this structure for your analysis:
            1. Explain clearly if the trend is growing, falling, or staying flat over the last 5 years.
            2. Tell how many strong spikes (peaks) are there, and when did the last big peak happen.
            3. Mention if these spikes are random or repeat in specific months (seasonality).
            4. Point out if there are months with very low or zero interest (dead periods).
            5. Tell if the graph looks stable or unpredictable (volatility).
            6. Talk briefly about the last 3 months: Is the interest going up, down, or stable?

            Rules to follow:
            - Use **simple and clean English** that a 5th grade Indian student can understand.
            - Use bullet points for 60–70% of your output.
            - **Do not suggest anything.** No tips, no advice, no opinions. Just tell what the graph is showing.
            - Keep it honest, to the point, and specific to this keyword. Don't talk like a research report.

            Do not use fancy words. Focus on what the trend is doing — not what people should do.

            Your tone should be clear and helpful, like you're explaining the graph to a normal Indian shopkeeper or new-age seller who wants straight answers."""
        
        # Generate the analysis
        analysis_response = model.generate_content(analysis_prompt)
        analysis = analysis_response.text

        # Create recommendations prompt based on business intent
        recommendations_prompt = ""
        
        if business_intent == 'yes':
            # For users who want to START a new business
            recommendations_prompt = f"""You are a search trend analyst and expert digital marketer working for TrendIQ. You are analyzing market demand data for the keyword: "{keyword}"

Here is the analysis:
{analysis}

The user is planning to start a business in this space. Your job is to analyze the trend clearly, then give them a step-by-step action plan — simple, practical, and based on actual data.

---

**Search Trend Analysis**
1. Is the trend growing, falling, or staying flat over the last 5 years?
2. How many strong spikes (peaks) are there? When was the last big peak?
3. Are the spikes seasonal or random?
4. Are there months with very low or zero interest (dead periods)?
5. Is the graph stable or unpredictable (volatility)?
6. What happened in the last 3 months — going up, down, or flat?

Rules:
- Use very simple English (talk like a beginner Indian seller)
- Bullet points for most of your answer
- No mention of Google Trends or TikTok
- Never tailor analysis based on marketplaces selected unless clearly visible in trend

---

**Startup Action Plan**

1. Is this the right time to enter?
- Based on trend strength, recent rise/fall, and seasonality
- Mention if competition looks high or low

2. Step-by-Step Market Entry Plan
- Based on niche: suggest content-first, marketplace-first, or direct funnel
- Choose YouTube / Reels / Blogs based on category needs (not blindly all)

3. Mistakes to Avoid
- Say what the user should not do, based on timing or saturation

4. Keyword Suggestions
- Give 10–15 low competition, relevant keywords to start with

5. Content Strategy Plan
- Give 25 blog/video topics
- Must be specific to the niche and mix educational, SEO and trust-building content

6. Bonus: Awareness Building
- Suggest PR, guest blogs, influencers only if they make sense
- Mention Example (if you know any legit ones in this space)"""

        elif business_intent == 'no':
            # For users who are ALREADY IN BUSINESS
            # Prepare business details section with conditional formatting for optional fields
            business_details = f"- Brand Name: {brand_name}\n"
            
            if user_website:
                business_details += f"- Website: {user_website}\n"
                
            # Format marketplaces more clearly for multiple selections
            if marketplaces_selected:
                business_details += f"- Marketplaces Selected: {marketplaces_selected}"
            else:
                business_details += "- No marketplaces specified"
                
            # Create a pagespeed insights summary if available
            pagespeed_summary = ""
            
            # Use PageSpeed data from frontend or from backend (whichever is available)
            website_analysis = None
            if pagespeed_data:
                # If we got PageSpeed data directly from frontend, use it
                website_analysis = pagespeed_data
                logger.info(f"Using frontend PageSpeed data for analysis with keys: {list(pagespeed_data.keys()) if isinstance(pagespeed_data, dict) else 'N/A'}")
            elif user_website:
                # Otherwise try to get it from backend analysis
                logger.info(f"Frontend PageSpeed data not available, attempting backend analysis for: {user_website}")
                website_analysis = analyze_website_with_pagespeed(user_website)
                
            # Format PageSpeed insights for the prompt if available
            if website_analysis and isinstance(website_analysis, dict) and 'error' not in website_analysis:
                try:
                    # Get summary if available, otherwise construct it from scores
                    summary = website_analysis.get('summary', '')
                    if not summary and 'scores' in website_analysis:
                        scores = website_analysis.get('scores', {})
                        perf = scores.get('performance', 0)
                        seo = scores.get('seo', 0)
                        acc = scores.get('accessibility', 0)
                        bp = scores.get('best-practices', 0)
                        summary = f"Performance: {perf:.0f}%, SEO: {seo:.0f}%, Accessibility: {acc:.0f}%, Best Practices: {bp:.0f}%"
                    
                    # Format PageSpeed insights as part of the input
                    pagespeed_summary = f"""
Website Analysis from PageSpeed Insights:

{summary}

Key Metrics:
"""
                    # Add metrics if available
                    metrics_data = website_analysis.get('metrics', {})
                    for metric_name, metric_info in metrics_data.items():
                        display_value = "N/A"
                        if isinstance(metric_info, dict) and 'display_value' in metric_info:
                            display_value = metric_info['display_value']
                        elif isinstance(metric_info, str):
                            display_value = metric_info
                            
                        # Format metric name for display
                        formatted_name = metric_name.replace('-', ' ').title()
                        pagespeed_summary += f"- {formatted_name}: {display_value}\n"
                    
                    pagespeed_summary += "\nTop Issues:\n"
                    
                    # Add opportunities
                    opportunities = website_analysis.get('opportunities', [])
                    if opportunities:
                        for i, opp in enumerate(opportunities[:5]):
                            if isinstance(opp, str):
                                pagespeed_summary += f"- {opp}\n"
                            elif isinstance(opp, dict) and 'title' in opp:
                                pagespeed_summary += f"- {opp['title']}\n"
                    else:
                        pagespeed_summary += "- No significant issues identified\n"
                        
                    logger.info("Successfully formatted PageSpeed insights for AI prompt")
                        
                except Exception as e:
                    logger.error(f"Error formatting PageSpeed insights: {str(e)}")
                    pagespeed_summary = "PageSpeed insights analysis failed. Error: " + str(e)
            elif website_analysis and isinstance(website_analysis, dict) and 'error' in website_analysis:
                pagespeed_summary = f"PageSpeed insights analysis failed: {website_analysis['error']}"
            else:
                logger.warning(f"Invalid website_analysis data: {type(website_analysis)}")
                pagespeed_summary = "PageSpeed insights analysis could not be performed."
            
            recommendations_prompt = f"""You are a search trend analyst and digital marketing expert at TrendIQ. Your job is to analyze market demand for the keyword: "{keyword}"

                Trend Summary:
                {data_summary}

                User details:
                - Website: {user_website}
                - Brand: {brand_name}
                - Marketplaces: {marketplaces_selected}

                {pagespeed_summary}

                ---

                🔍 Search Trend Analysis (Explain in simple language):
                1. Is the trend growing, flat, or declining in 5 years?
                2. How many spikes? When was the last one?
                3. Are spikes seasonal or random?
                4. Any low/zero-interest months?
                5. Is the trend stable or volatile?
                6. What's happening in the last 3 months?

                Rules:
                - No TikTok. No Google Trends mention.
                - Use clean English + bullet points.
                - Do NOT assume platform-specific results unless trend shows it clearly.
                - No opinions. Only describe what the graph shows.

                ---

                📊 6-Month Action Plan:

                1. ✅ Website Analysis & Optimization:
                Based on the PageSpeed Insights data provided, thoroughly analyze the technical performance, SEO health, user experience, and content quality of the website {user_website}. Specifically:
                - Evaluate performance issues (loading speed, render-blocking resources, image optimization)
                - Identify critical SEO problems (crawlability, indexing issues, meta data, structured data)
                - Assess content relevance and optimization for the keyword "{keyword}"
                - Review mobile responsiveness and accessibility
                - Directly flag **PageSpeed issues** (e.g., FCP > 3s = major problem)
                - Call out if **structured data/schema** is missing — say: "You're not AI-ready"
                - If blog is missing or dead, say: "No blog = no organic traffic. Start one now"
                - If mobile UX fails audit, say so and why (e.g., "Text too small, buttons overlap on mobile")
                - Prioritize only **what's broken or missing** based on impact and difficulty. No compliments.

                2. 🛒 Marketplace Audit:
                - Check all listed marketplaces. If any **don't have listings**, say: "Not listed on Flipkart — missed opportunity"
                - If **A+ content is missing**, don't suggest — command: "Upload A+ content now — you're bleeding trust"
                - If **review count is low**, say: "Only 3 reviews on Amazon? That's killing your conversion."
                - If listing title or bullets are weak, point it out like: "Title lacks material & use-case. Fix it."
                - Flag **wrong categories**, **bad images**, or **lack of search term indexing**

                3. 🎯 Channel Strategy:
                - Suggest best content platforms (YouTube, Blogs, etc.) based on niche
                - Fashion, beauty → Reels, Shorts, YouTube, Blog  
                - Tools, B2B, industrial → YouTube + Blog only

                4. 🔍 Keywords:
                - Suggest 10–15 low competition, high-intent keywords for this niche

                5. 🧠 Content Calendar:
                - Give 25 blog/video ideas (how-to, myth-busting, comparison, FAQs)

                6. 📰 PR & Influencers:
                - Suggest 3–5 guest post or PR websites
                - Mention real influencer or site if competitor was featured"""
        else:
            # Default case for 'not_sure' or any other value
            recommendations_prompt = f"""You are a search trend analyst working for TrendIQ. You are analyzing Trends data for the keyword: "{keyword}"

                Here is the analysis:
                {analysis}

                The user is exploring this keyword and hasn't decided if they want to start a business or not.

                Generate a balanced recommendation that includes:

                1. General Analysis
                - Is the trend growing, declining, or stable?
                - Is there seasonality or predictable patterns?
                - Is now a good time to consider this market?

                2. Opportunity Assessment
                - What are the potential opportunities in this space?
                - Are there specific segments or niches that look promising?
                - What platforms or channels might work best?

                3. Action Steps
                - Suggest 5-7 practical steps for further research
                - Include keyword ideas and content suggestions
                - Give marketplace-specific tips if relevant

                Rules:
                - Use simple, clear English
                - Organize with bullet points
                - Be factual and data-driven
                - No mention of TikTok or Google Trends
                - Keep suggestions practical for a beginner
                """
        
        # Generate recommendations
        recommendations_response = model.generate_content(recommendations_prompt)
        recommendations = recommendations_response.text
        print(recommendations)
        logger.info(f"Successfully generated AI analysis for {keyword} with business_intent: {business_intent}")
        return analysis, recommendations
        
    except (ResourceExhausted, InvalidArgument, ServiceUnavailable) as api_err:
        logger.error(f"Google GenerativeAI API error: {str(api_err)}")
        raise
    except Exception as e:
        logger.error(f"Error in analyze_with_generative_ai: {str(e)}", exc_info=True)
        raise
        
def extract_trend_metrics(trend_data, keyword):
    """
    Extract key metrics from trend data for analysis.
    
    Args:
        trend_data: The trends data object
        keyword: The search keyword
        
    Returns:
        Dictionary of metrics
    """
    metrics = {
        'keyword': keyword,
        'overall_trend': 'stable',  # Default values
        'growth_rate': 0,
        'volatility': 'low',
        'volatility_value': 0,
        'peak_periods': [],
        'trough_periods': [],
        'seasonal': False,
        'seasonal_pattern': None,
        'recent_direction': 'stable'
    }
    
    try:
        # Process time series data if available
        time_series = None
        
        # Try to extract time series data from different possible formats
        if isinstance(trend_data, list) and len(trend_data) > 0:
            # Direct array of time points
            time_series = trend_data
        elif isinstance(trend_data, dict):
            # Look for timeSeriesData in the object
            if 'timeSeriesData' in trend_data:
                time_series = trend_data['timeSeriesData']
            elif 'trends' in trend_data and 'timeSeriesData' in trend_data['trends']:
                time_series = trend_data['trends']['timeSeriesData']
        
        if not time_series:
            logger.warning(f"Could not extract time series data for {keyword}")
            return metrics
            
        # Extract values and dates from time series
        values = []
        dates = []
        
        for point in time_series:
            date_val = None
            value_val = None
            
            # Extract date based on available properties
            if 'date' in point:
                date_val = point['date']
            elif 'time' in point:
                date_val = point['time']
            elif 'formattedTime' in point:
                date_val = point['formattedTime']
            
            # Extract value based on available properties
            if keyword in point:
                value_val = point[keyword]
            elif 'value' in point:
                if isinstance(point['value'], list):
                    value_val = point['value'][0]
                else:
                    value_val = point['value']
            
            if date_val and value_val is not None:
                try:
                    # Convert to numeric value if needed
                    if not isinstance(value_val, (int, float)):
                        value_val = float(value_val)
                    
                    values.append(value_val)
                    dates.append(date_val)
                except (ValueError, TypeError):
                    pass
        
        if len(values) < 2:
            logger.warning(f"Insufficient data points for analysis for {keyword}")
            return metrics
            
        # Calculate overall growth rate
        first_val = values[0]
        last_val = values[-1]
        if first_val > 0:
            growth_rate = ((last_val - first_val) / first_val) * 100
            metrics['growth_rate'] = round(growth_rate, 2)
            
            if growth_rate > 10:
                metrics['overall_trend'] = 'strongly increasing'
            elif growth_rate > 5:
                metrics['overall_trend'] = 'increasing'
            elif growth_rate > -5:
                metrics['overall_trend'] = 'stable'
            elif growth_rate > -10:
                metrics['overall_trend'] = 'decreasing'
            else:
                metrics['overall_trend'] = 'strongly decreasing'
        
        # Calculate volatility (standard deviation / mean)
        if len(values) > 0:
            mean = sum(values) / len(values)
            if mean > 0:
                variance = sum((x - mean) ** 2 for x in values) / len(values)
                std_dev = variance ** 0.5
                volatility = (std_dev / mean) * 100
                metrics['volatility_value'] = round(volatility, 2)
                
                if volatility < 15:
                    metrics['volatility'] = 'very low'
                elif volatility < 30:
                    metrics['volatility'] = 'low'
                elif volatility < 50:
                    metrics['volatility'] = 'moderate'
                elif volatility < 75:
                    metrics['volatility'] = 'high'
                else:
                    metrics['volatility'] = 'very high'
        
        # Identify peaks and troughs
        if len(values) > 2:
            peak_indices = []
            trough_indices = []
            
            for i in range(1, len(values) - 1):
                if values[i] > values[i-1] and values[i] > values[i+1]:
                    peak_indices.append(i)
                if values[i] < values[i-1] and values[i] < values[i+1]:
                    trough_indices.append(i)
            
            # Get top 3 peaks and troughs
            peak_indices.sort(key=lambda i: values[i], reverse=True)
            trough_indices.sort(key=lambda i: values[i])
            
            # Format peak periods
            for idx in peak_indices[:3]:
                if isinstance(dates[idx], str):
                    metrics['peak_periods'].append({
                        'date': dates[idx],
                        'value': values[idx]
                    })
            
            # Format trough periods
            for idx in trough_indices[:3]:
                if isinstance(dates[idx], str):
                    metrics['trough_periods'].append({
                        'date': dates[idx],
                        'value': values[idx]
                    })
        
        # Check for seasonality (simplified approach)
        if len(values) >= 12:
            # Simple check for repeating patterns using autocorrelation
            metrics['seasonal'] = check_seasonality(values)
            
        # Recent trend direction (last 20% of the data)
        if len(values) > 5:
            last_segment = values[int(-len(values) * 0.2):]
            if last_segment[-1] > last_segment[0] * 1.05:
                metrics['recent_direction'] = 'upward'
            elif last_segment[-1] < last_segment[0] * 0.95:
                metrics['recent_direction'] = 'downward'
            else:
                metrics['recent_direction'] = 'stable'
        
        return metrics
    
    except Exception as e:
        logger.error(f"Error extracting metrics from trend data: {str(e)}", exc_info=True)
        return metrics

def check_seasonality(values, threshold=0.5):
    """
    Simple method to check for seasonality in time series data.
    
    Args:
        values: List of numeric values
        threshold: Correlation threshold to determine seasonality
        
    Returns:
        Boolean indicating if the data shows seasonal patterns
    """
    # Needs at least 24 data points for meaningful seasonality check
    if len(values) < 24:
        return False
    
    try:
        # Try quarterly seasonality (period = 4)
        if len(values) >= 12:
            quarterly_corr = autocorrelation(values, 4)
            if quarterly_corr > threshold:
                return True
        
        # Try annual seasonality (period = 12)
        if len(values) >= 24:
            yearly_corr = autocorrelation(values, 12)
            if yearly_corr > threshold:
                return True
        
        return False
    except:
        return False

def autocorrelation(values, lag):
    """Calculate autocorrelation of a time series with specified lag."""
    n = len(values)
    if lag >= n:
        return 0
    
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    
    if variance == 0:
        return 0
    
    correlation = 0
    for i in range(n - lag):
        correlation += (values[i] - mean) * (values[i + lag] - mean)
    
    return correlation / (n * variance)

def generate_trend_analysis(keyword, metrics):
    """
    Generate a human-readable analysis of trends data.
    
    Args:
        keyword: The search keyword
        metrics: Dictionary of metrics extracted from trend data
        
    Returns:
        String containing the analysis
    """
    analysis = f"Analysis of search interest for \"{keyword}\":\n\n"
    
    # Overall trend
    analysis += f"The overall trend for \"{keyword}\" is {metrics['overall_trend']}"
    if metrics.get('growth_rate') is not None:
        if metrics['growth_rate'] > 0:
            analysis += f" with a {abs(metrics['growth_rate']):.1f}% increase over the analyzed period."
        elif metrics['growth_rate'] < 0:
            analysis += f" with a {abs(metrics['growth_rate']):.1f}% decrease over the analyzed period."
        else:
            analysis += " with no significant change over the analyzed period."
    else:
        analysis += "."
    analysis += "\n\n"
    
    # Volatility
    analysis += f"The search interest shows {metrics['volatility']} volatility"
    if metrics.get('volatility_value') is not None:
        analysis += f" ({metrics['volatility_value']:.1f}%)"
    analysis += ", indicating "
    
    if metrics['volatility'] == 'very low':
        analysis += "an extremely consistent and stable interest pattern."
    elif metrics['volatility'] == 'low':
        analysis += "a consistent interest pattern with minimal fluctuations."
    elif metrics['volatility'] == 'moderate':
        analysis += "some noticeable fluctuations in interest over time."
    elif metrics['volatility'] == 'high':
        analysis += "significant fluctuations in interest, suggesting a topic sensitive to external factors."
    else:  # very high
        analysis += "extreme fluctuations, likely driven by specific events or strong seasonality."
    analysis += "\n\n"
    
    # Peak periods
    if metrics['peak_periods']:
        analysis += "Notable peak(s) in interest occurred during: "
        peak_descriptions = []
        for peak in metrics['peak_periods']:
            peak_descriptions.append(f"{peak['date']} (value: {peak['value']:.1f})")
        analysis += ", ".join(peak_descriptions) + "."
        analysis += "\n\n"
    
    # Seasonality
    if metrics['seasonal']:
        analysis += "The data shows evidence of seasonal patterns, suggesting recurring interest at regular intervals."
    else:
        if metrics['volatility'] in ['high', 'very high']:
            analysis += "Despite the high volatility, no clear seasonal pattern was detected, suggesting that interest spikes are driven by specific events rather than predictable cycles."
        else:
            analysis += "No significant seasonal pattern was detected in the data."
    analysis += "\n\n"
    
    # Recent direction
    analysis += f"The most recent trend is {metrics['recent_direction']}, "
    if metrics['recent_direction'] == 'upward':
        analysis += "indicating growing interest that may continue in the near future."
    elif metrics['recent_direction'] == 'downward':
        analysis += "suggesting declining interest that may continue in the near future."
    else:
        analysis += "showing a relatively stable interest level in the most recent period."
    
    return analysis

def generate_trend_recommendations(keyword, metrics):
    """
    Generate recommendations based on trends data.
    
    Args:
        keyword: The search keyword
        metrics: Dictionary of metrics extracted from trend data
        
    Returns:
        String containing recommendations
    """
    recommendations = f"Recommendations for \"{keyword}\":\n\n"
    
    # Based on overall trend
    if metrics['overall_trend'] in ['strongly increasing', 'increasing']:
        recommendations += "1. Growth Strategy: With increasing interest, consider expanding content, products, or services related to this topic. This is an opportunity to capitalize on growing market interest.\n\n"
        recommendations += "2. Investment Prioritization: Allocate more resources to this area due to its positive growth trajectory. Consider increasing marketing budgets or development resources.\n\n"
    elif metrics['overall_trend'] == 'stable':
        recommendations += "1. Maintenance Strategy: With stable interest, focus on maintaining quality and optimizing existing offerings rather than major expansions.\n\n"
        recommendations += "2. Differentiation: In a stable market, focus on differentiating your offerings from competitors to gain market share without relying on overall market growth.\n\n"
    else:  # decreasing or strongly decreasing
        recommendations += "1. Pivot Consideration: With decreasing interest, consider diversifying or pivoting to related areas with more growth potential.\n\n"
        recommendations += "2. Efficiency Focus: Optimize costs and operations to maintain profitability despite declining interest. Look for ways to serve the core audience more efficiently.\n\n"
    
    # Based on volatility
    if metrics['volatility'] in ['high', 'very high']:
        recommendations += "3. Agile Planning: High volatility requires flexible planning and quick response capabilities. Develop contingency plans for both surges and drops in interest.\n\n"
        recommendations += "4. Event Monitoring: Set up monitoring systems for events or factors that might trigger interest spikes, allowing you to react quickly to opportunities.\n\n"
    else:
        recommendations += "3. Consistent Engagement: The relatively stable interest pattern allows for more predictable planning. Develop a consistent content or product release schedule.\n\n"
        recommendations += "4. Long-term Investment: Lower volatility supports longer-term investments, as the risk of sudden market changes is reduced.\n\n"
    
    # Based on seasonality
    if metrics['seasonal']:
        recommendations += "5. Seasonal Planning: Prepare campaigns, content, or inventory according to the identified seasonal patterns. Increase efforts before anticipated peaks.\n\n"
        recommendations += "6. Off-Season Strategy: Develop strategies to maintain engagement during predicted low periods, such as diversifying topics or offering special promotions.\n\n"
    else:
        recommendations += "5. Consistent Distribution: Without clear seasonality, distribute your efforts evenly throughout the year rather than concentrating on specific periods.\n\n"
    
    # Based on recent direction
    if metrics['recent_direction'] == 'upward':
        recommendations += "7. Momentum Capitalization: The recent upward trend presents an immediate opportunity. Increase short-term marketing efforts to capitalize on growing interest.\n\n"
    elif metrics['recent_direction'] == 'downward':
        recommendations += "7. Trend Reversal Tactics: Consider fresh approaches or repositioning to address the recent downward trend. Explore what might be causing the decline.\n\n"
    else:
        recommendations += "7. Incremental Improvement: With stable recent performance, focus on incremental improvements to gradually enhance engagement and interest.\n\n"
    
    return recommendations 



    # Prompt used for Analysis:
    """
    Analyze the following Google Trends data for [keyword]:
    - Overall trend direction and strength over the full time period
    - Volatility levels and pattern changes
    - Presence of seasonal patterns or cycles
    - Recent trend direction (last 3 months)
    - Key spikes or drops and potential causes
    - Geographic distribution of interest
    - Related topics and queries
    
    Provide a detailed analysis covering:
    1. Overall trend assessment
    2. Pattern identification
    3. Geographic insights
    4. Related topics analysis
    5. Key events correlation
    6. Future trajectory prediction
    """

    # Prompt used for Recommendations:
    """
    Based on the trends analysis for [keyword], provide strategic recommendations covering:
    1. Growth/Maintenance Strategy based on overall trend
    2. Resource allocation and investment priorities
    3. Risk management approach based on volatility
    4. Event response planning
    5. Seasonal planning if applicable
    6. Geographic targeting suggestions
    7. Content/Product development direction
    8. Marketing and positioning strategy
    
    Consider:
    - Overall trend direction (increasing/stable/decreasing)
    - Volatility levels
    - Seasonal patterns
    - Recent direction changes
    - Geographic opportunities
    - Related topics potential
    
    Provide actionable recommendations with clear rationale and implementation guidance.
    """

@csrf_exempt
@require_http_methods(["POST"])
def pagespeed_test_api(request):
    """
    Test endpoint for PageSpeed Insights API
    """
    try:
        data = json.loads(request.body)
        website_url = data.get('website_url', '')
        
        if not website_url:
            return JsonResponse({
                'status': 'error',
                'message': 'Website URL is required'
            }, status=400)
            
        # Analyze the website
        insights = analyze_website_with_pagespeed(website_url)
        
        if not insights:
            # Generate mock data if analysis fails
            logger.warning(f"PageSpeed analysis failed for {website_url}, generating mock data")
            insights = generate_mock_pagespeed_data(website_url)
            
        # Check for error in the insights
        if 'error' in insights:
            logger.warning(f"PageSpeed analysis returned error: {insights['error']}, generating mock data")
            insights = generate_mock_pagespeed_data(website_url)
            
        # Convert opportunities to the expected format
        formatted_opportunities = []
        for opportunity in insights.get('opportunities', []):
            if isinstance(opportunity, str):
                formatted_opportunities.append({
                    'title': opportunity
                })
            else:
                # If already in object format, keep as is
                formatted_opportunities.append(opportunity)
                
        insights['opportunities'] = formatted_opportunities
            
        return JsonResponse({
            'status': 'success',
            'data': insights
        }, encoder=EnhancedJSONEncoder)
        
    except Exception as e:
        logger.error(f"Error in pagespeed_test_api: {str(e)}", exc_info=True)
        # Generate mock data on exception
        mock_data = generate_mock_pagespeed_data(data.get('website_url', 'unknown'))
        return JsonResponse({
            'status': 'success',
            'data': mock_data,
            'note': 'Using mock data due to API error'
        }, encoder=EnhancedJSONEncoder)

def generate_mock_pagespeed_data(url):
    """
    Generate mock PageSpeed data when the API fails
    
    Args:
        url: Website URL
        
    Returns:
        Dictionary with mock PageSpeed data
    """
    import random
    
    logger.info(f"Generating mock PageSpeed data for {url}")
    
    # Generate random scores between 60-95
    performance = random.randint(60, 95)
    seo = random.randint(60, 95)
    accessibility = random.randint(60, 95)
    best_practices = random.randint(60, 95)
    
    # Standard opportunities for improvement
    opportunities = [
        "Properly size images",
        "Eliminate render-blocking resources",
        "Remove unused JavaScript",
        "Efficiently encode images",
        "Serve images in next-gen formats"
    ]
    
    # Create mock metrics
    fcp = f"{round(random.uniform(1.0, 3.0), 1)} s"
    lcp = f"{round(random.uniform(2.0, 5.0), 1)} s"
    cls = f"{round(random.uniform(0.01, 0.3), 2)}"
    tbt = f"{random.randint(50, 500)} ms"
    si = f"{round(random.uniform(3.0, 8.0), 1)} s"
    tti = f"{round(random.uniform(3.0, 7.0), 1)} s"
    
    mock_data = {
        "url": url,
        "analyzed_at": datetime.now().isoformat(),
        "scores": {
            "performance": performance,
            "seo": seo,
            "accessibility": accessibility,
            "best-practices": best_practices
        },
        "metrics": {
            "first-contentful-paint": {
                "display_value": fcp
            },
            "largest-contentful-paint": {
                "display_value": lcp
            },
            "cumulative-layout-shift": {
                "display_value": cls
            },
            "total-blocking-time": {
                "display_value": tbt
            },
            "speed-index": {
                "display_value": si
            },
            "interactive": {
                "display_value": tti
            }
        },
        "opportunities": opportunities,
        "summary": f"Performance: {performance}%, SEO: {seo}%, Accessibility: {accessibility}%, Best Practices: {best_practices}%",
        "is_mock_data": True
    }
    
    return mock_data

def pagespeed_test_view(request):
    """
    Render the PageSpeed Insights test page
    """
    return render(request, 'trends/pagespeed_test.html')

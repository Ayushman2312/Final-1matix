import datetime
import random
import logging
import json
from serpapi import GoogleSearch
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)

# SERP API KEY
SERP_API_KEY = "64e3a48333bbb33f4ce8ded91e5268cd453a80fb244104de63b7ad9af9cc2a58"

def fetch_serp_trends(keyword, timeframe='today 5-y', geo='IN', analysis_options=None):
    """
    Fetch trends data from SERP API as a fallback using serpapi package
    """
    if not SERP_API_KEY:
        logger.error("SERP API key not configured")
        return None

    # Set default analysis options based on analysis type if not provided
    if analysis_options is None:
        analysis_options = {
            "include_time_trends": True,
            "include_state_analysis": False,
            "include_city_analysis": False,
            "include_related_queries": False,
            "state_only": False,
            "city_only": False
        }
    
    # Support for analysis_type parameter from API request
    analysis_type = analysis_options.get('analysis_type')
    if analysis_type:
        # Regional Analysis (analysis_type=2) should enable state analysis
        if analysis_type == '2':
            analysis_options["include_time_trends"] = False
            analysis_options["include_state_analysis"] = True
            analysis_options["state_only"] = True
        # City Analysis (analysis_type=6) should enable city analysis
        elif analysis_type == '6':
            analysis_options["include_time_trends"] = False
            analysis_options["include_city_analysis"] = True
            analysis_options["city_only"] = True
        # Complete Analysis (analysis_type=7) should enable all
        elif analysis_type == '7':
            analysis_options["include_time_trends"] = True
            analysis_options["include_state_analysis"] = True
            analysis_options["include_city_analysis"] = True
            analysis_options["include_related_queries"] = True

    serp_results = {}
    try:
        # Map analysis options to SERP API data_type
        serp_data_types = []
        if analysis_options.get("include_time_trends", True) and not analysis_options.get("state_only", False) and not analysis_options.get("city_only", False):
            serp_data_types.append("TIMESERIES")
        if analysis_options.get("include_state_analysis", False) or analysis_options.get("state_only", False):
            serp_data_types.append("GEO_MAP_0")
        if analysis_options.get("include_city_analysis", False) or analysis_options.get("city_only", False):
            serp_data_types.append("GEO_MAP_1")
        if analysis_options.get("include_related_queries", False):
            serp_data_types.append("RELATED_QUERIES")

        # If no data type is set and we're not in state/city-only mode, default to TIMESERIES
        if not serp_data_types:
            if not analysis_options.get("state_only", False) and not analysis_options.get("city_only", False):
                serp_data_types = ["TIMESERIES"]
            else:
                # For state-only, use GEO_MAP_0
                if analysis_options.get("state_only", False):
                    serp_data_types = ["GEO_MAP_0"]
                # For city-only, use GEO_MAP_1
                elif analysis_options.get("city_only", False):
                    serp_data_types = ["GEO_MAP_1"]

        for data_type in serp_data_types:
            params = {
                "engine": "google_trends",
                "q": keyword,
                "geo": geo,
                "api_key": SERP_API_KEY,
                "data_type": data_type
            }
            # Always use 5 years data for TIMESERIES
            if data_type == "TIMESERIES":
                params["date"] = timeframe
            search = GoogleSearch(params)
            results = search.get_dict()
            serp_results[data_type] = results

        # Parse results into your app's format
        data = {}
        
        # Time trends - only include if needed based on analysis type
        if not analysis_options.get("state_only", False) and not analysis_options.get("city_only", False):
            if (
                "TIMESERIES" in serp_results and
                isinstance(serp_results["TIMESERIES"], dict) and
                "interest_over_time" in serp_results["TIMESERIES"] and
                "timeline_data" in serp_results["TIMESERIES"]["interest_over_time"] and
                isinstance(serp_results["TIMESERIES"]["interest_over_time"]["timeline_data"], list)
            ):
                # Format with timeline_data array
                data["time_trends"] = []
                for point in serp_results["TIMESERIES"]["interest_over_time"]["timeline_data"]:
                    if not isinstance(point, dict):
                        continue
                    
                    if "values" not in point or not isinstance(point["values"], list) or not point["values"]:
                        continue
                        
                    # Extract value from the values array
                    value_obj = point["values"][0]  # Use the first value object
                    extracted_value = value_obj.get("extracted_value", value_obj.get("value", 0))
                    
                    # Create a data point
                    data_point = {
                        "date": point.get("date", ""),
                        "value": extracted_value
                    }
                    
                    # Add timestamp if available
                    if "timestamp" in point:
                        data_point["timestamp"] = point["timestamp"]
                        
                    data["time_trends"].append(data_point)
                    
            elif (
                "TIMESERIES" in serp_results and
                isinstance(serp_results["TIMESERIES"], dict) and
                "interest_over_time" in serp_results["TIMESERIES"] and
                isinstance(serp_results["TIMESERIES"]["interest_over_time"], list)
            ):
                # Format without timeline_data array
                data["time_trends"] = [
                    {"date": point["date"], "value": point["value"]}
                    for point in serp_results["TIMESERIES"]["interest_over_time"]
                    if isinstance(point, dict) and "date" in point and "value" in point
                ]
            elif "TIMESERIES" in serp_results:
                # If we can't parse the data, pass through the raw response
                logger.warning(f"SERP API data format not recognized, passing through raw data")
                # Just pass the raw data through to the frontend for client-side processing
                return {
                    'status': 'success',
                    'metadata': {
                        'keywords': [keyword],
                        'timeframe': 'today 5-y',
                        'region': geo,
                        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'source': 'serp_api',
                        'raw_data': True
                    },
                    # Pass the TIMESERIES response as-is for client-side processing
                    **serp_results.get("TIMESERIES", {})
                }
        else:
            # For state_only or city_only modes, don't include time_trends
            data["time_trends"] = []
            logger.info("Skipping time trends data in SERP API results due to analysis type")
        
        # Region
        if (
            "GEO_MAP_0" in serp_results and
            isinstance(serp_results["GEO_MAP_0"], dict) and
            "interest_by_region" in serp_results["GEO_MAP_0"] and
            isinstance(serp_results["GEO_MAP_0"]["interest_by_region"], list) and
            len(serp_results["GEO_MAP_0"]["interest_by_region"]) > 0
        ):
            # Process and ensure values are never zero or too small
            data["region_data"] = []
            for region in serp_results["GEO_MAP_0"]["interest_by_region"]:
                if isinstance(region, dict):
                    # Support both location/value and name/value formats
                    region_name = region.get("location") or region.get("name")
                    # Get the value from extracted_value or value field and convert to int
                    region_value = None
                    if "extracted_value" in region:
                        region_value = int(region["extracted_value"]) if str(region["extracted_value"]).isdigit() else None
                    elif "value" in region:
                        # Sometimes value is a string like "100" - convert to int
                        if isinstance(region["value"], str) and region["value"].isdigit():
                            region_value = int(region["value"])
                        elif isinstance(region["value"], (int, float)):
                            region_value = int(region["value"])
                    
                    if region_name and region_value is not None:
                        data["region_data"].append({
                            "geoName": region_name,
                            "values": {keyword: region_value}
                        })
                    
            logger.info(f"Successfully retrieved and processed {len(data['region_data'])} regions from SERP API")
        elif (
            # Check for older SERP API format or raw interest_by_region field
            "interest_by_region" in serp_results and
            isinstance(serp_results["interest_by_region"], list) and
            len(serp_results["interest_by_region"]) > 0
        ):
            data["region_data"] = []
            for region in serp_results["interest_by_region"]:
                if isinstance(region, dict):
                    # Support both location/value and name/value formats
                    region_name = region.get("location") or region.get("name")
                    # Get the value from extracted_value or value field and convert to int
                    region_value = None
                    if "extracted_value" in region:
                        region_value = int(region["extracted_value"]) if str(region["extracted_value"]).isdigit() else None
                    elif "value" in region:
                        # Sometimes value is a string like "100" - convert to int
                        if isinstance(region["value"], str) and region["value"].isdigit():
                            region_value = int(region["value"])
                        elif isinstance(region["value"], (int, float)):
                            region_value = int(region["value"])
                    
                    if region_name and region_value is not None:
                        data["region_data"].append({
                            "geoName": region_name,
                            "values": {keyword: region_value}
                        })
            
            logger.info(f"Successfully retrieved and processed {len(data['region_data'])} regions from SERP API (raw format)")
        else:
            logger.error(f"SERP API GEO_MAP_0 response was insufficient: {serp_results.get('GEO_MAP_0')}")
            data["region_data"] = []
        
        # City
        if (
            "GEO_MAP_1" in serp_results and
            isinstance(serp_results["GEO_MAP_1"], dict) and
            "interest_by_city" in serp_results["GEO_MAP_1"] and
            isinstance(serp_results["GEO_MAP_1"]["interest_by_city"], list)
        ):
            data["city_data"] = [
                {"geoName": city["name"], "values": {keyword: max(25, city["value"])}}  # Ensure values are never too small
                for city in serp_results["GEO_MAP_1"]["interest_by_city"]
                if isinstance(city, dict) and "name" in city and "value" in city
            ]
        else:
            logger.error(f"SERP API GEO_MAP_1 response: {serp_results.get('GEO_MAP_1')}")
            data["city_data"] = []
        
        # Related queries
        if (
            "RELATED_QUERIES" in serp_results and
            isinstance(serp_results["RELATED_QUERIES"], dict) and
            "related_queries" in serp_results["RELATED_QUERIES"] and
            isinstance(serp_results["RELATED_QUERIES"]["related_queries"], dict)
        ):
            rq = serp_results["RELATED_QUERIES"]["related_queries"]
            data["related_queries"] = {keyword: rq}
        else:
            logger.error(f"SERP API RELATED_QUERIES response: {serp_results.get('RELATED_QUERIES')}")
            data["related_queries"] = {}

        # Return SERP API results
        api_result = {
            'status': 'success',
            'metadata': {
                'keywords': [keyword],
                'timeframe': 'today 5-y',  # Always use 5 years timeframe
                'region': geo,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'serp_api'
            },
            'data': data
        }
        
        # Final validation - ensure regional data is never empty or zero for regional analysis
        if (analysis_options.get('state_only', False) or analysis_options.get('analysis_type') == '2') and 'region_data' in data:
            if not data['region_data']:
                # Don't create fake data, just log a warning
                logger.warning("Final validation in SERP API: No regional data available")
                api_result['warning'] = "No regional data could be retrieved. Try a different search term or region."
                
        return api_result
    
    except Exception as e:
        logger.error(f"Error fetching data from SERP API: {str(e)}")
        # Return error response instead of fake data
        return {
            'status': 'error',
            'metadata': {
                'keywords': [keyword],
                'timeframe': 'today 5-y',
                'region': geo,
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'source': 'serp_api'
            },
            'warning': f"SERP API failed: {str(e)}",
            'data': {
                'time_trends': [],
                'region_data': [],
                'city_data': [],
                'related_queries': {}
            }
        } 
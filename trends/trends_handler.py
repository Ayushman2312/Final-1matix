from trends.trends import get_trends_json
import json
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import logging

logger = logging.getLogger(__name__)

def analyze_trends(keyword, timeframe='today 5-y', geo='IN', analysis_type='1'):
    """
    Analyze trends for a given keyword and return JSON data for chart rendering
    
    Parameters:
    - keyword: The search keyword
    - timeframe: Time period to analyze (default: 'today 5-y')
    - geo: Geographic region code (default: 'IN' for India)
    - analysis_type: Type of analysis to perform (default: '1' for time trends only)
    
    Returns:
    - Dictionary containing the trends data in JSON format
    """
    try:
        # Convert keyword to list if it's a string
        if isinstance(keyword, str):
            keywords = [keyword]
        else:
            keywords = keyword
            
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
        trends_data = get_trends_json(
            keywords=keywords,
            timeframe=timeframe,
            geo=geo,
            analysis_options=analysis_options
        )
        
        # Save the data to a JSON file for reference
        output_dir = "trend_data"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        timestamp = trends_data['metadata']['timestamp'].replace(':', '-').replace(' ', '_')
        json_filename = f"{output_dir}/trends_{keywords[0]}_{geo}_{timestamp}.json"
        
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(trends_data, f, ensure_ascii=False, indent=2)
            
        return trends_data
        
    except Exception as e:
        logger.error(f"Error analyzing trends: {str(e)}")
        return {
            "error": "Failed to analyze trends",
            "details": str(e)
        }

@csrf_exempt
def trends_api(request):
    """
    Django view function to handle trends analysis requests
    
    Accepts both GET and POST requests:
    - GET: Parameters in query string
    - POST: Parameters in request body (JSON)
    
    Parameters:
    - keyword: Search keyword
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
                keyword = data.get('keyword', '')
                timeframe = data.get('timeframe', 'today 5-y')
                geo = data.get('geo', 'IN')
                analysis_type = data.get('analysis_type', '1')
            except json.JSONDecodeError:
                return JsonResponse({
                    "error": "Invalid JSON in request body"
                }, status=400)
        else:  # GET
            keyword = request.GET.get('keyword', '')
            timeframe = request.GET.get('timeframe', 'today 5-y')
            geo = request.GET.get('geo', 'IN')
            analysis_type = request.GET.get('analysis_type', '1')
            
        # Validate keyword
        if not keyword:
            return JsonResponse({
                "error": "No keyword provided"
            }, status=400)
            
        # Get trends data
        trends_data = analyze_trends(keyword, timeframe, geo, analysis_type)
        
        # Return JSON response
        return JsonResponse(trends_data, safe=False)
        
    except Exception as e:
        logger.error(f"Error in trends_api: {str(e)}")
        return JsonResponse({
            "error": "Failed to process request",
            "details": str(e)
        }, status=500) 
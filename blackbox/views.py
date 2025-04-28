# views.py
import logging
import os
import requests
import json
from django.views.generic import TemplateView, View
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from datetime import datetime, timedelta
from django.conf import settings

# Configure logging
logger = logging.getLogger(__name__)

class BlackBoxSearchView(TemplateView):
    template_name = 'blackbox/blackbox.html'
    
    def get(self, request, *args, **kwargs):
        """Handle GET requests, display the search form."""
        logger.info("Rendering BlackBox search form")
        return render(request, self.template_name, {})

@method_decorator(csrf_exempt, name='dispatch')
class BlackBoxApiView(View):
    """API endpoint to handle AJAX requests for product data."""
    
    def post(self, request, *args, **kwargs):
        """Handle POST requests from AJAX."""
        logger.info("=== Starting API request processing ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request headers: {dict(request.headers)}")
        logger.info(f"Request body: {request.body.decode('utf-8')}")
        
        try:
            # Parse JSON data from request body
            data = json.loads(request.body)
            logger.info(f"Parsed JSON data: {data}")
            
            # Extract form data
            marketplace = data.get('marketplace', 'amazon.com')
            category = data.get('category', '')
            improvement = data.get('improvement', '')
            competition = data.get('competition', '')
            price_range = data.get('price_range', '')
            monthly_revenue = data.get('monthly_revenue', '')
            
            logger.info(f"Extracted form data: marketplace={marketplace}, category={category}")
            
            # For sample purposes, using a fixed ASIN
            asin = 'B09XKS4236'  # This is from the image
            
            # Call the Rainforest API to get product results
            logger.info(f"Calling Rainforest API for ASIN: {asin}")
            api_response = self._fetch_from_rainforest(
                marketplace=marketplace,
                asin=asin
            )
            
            logger.info(f"Rainforest API response received: {bool(api_response)}")
            
            # Process the response and extract product details dynamically
            formatted_results = []
            if api_response and 'product' in api_response:
                product = api_response['product']
                logger.info("Processing product data from API response")
                
                # Get the category name from the categories list
                category_name = 'Beauty'
                if product.get('categories') and len(product.get('categories')) > 0:
                    category_name = product.get('categories', [{}])[0].get('name', 'Beauty')
                
                # Calculate dimensions string
                dimensions = "N/A"
                if product.get('dimensions'):
                    length = product.get('dimensions', {}).get('length', '')
                    width = product.get('dimensions', {}).get('width', '')
                    height = product.get('dimensions', {}).get('height', '')
                    unit = product.get('dimensions', {}).get('unit', '')
                    if length and width and height:
                        dimensions = f"{length}\" x {width}\" x {height}\" {unit}"
                
                # Calculate weight
                weight = "N/A"
                if product.get('weight'):
                    weight_value = product.get('weight', {}).get('value', '')
                    weight_unit = product.get('weight', {}).get('unit', 'lbs')
                    if weight_value:
                        weight = f"{weight_value} {weight_unit}"
                
                # Extract other data or use defaults
                formatted_result = {
                    'image': product.get('main_image', {}).get('link', ''),
                    'asin': product.get('asin', asin),
                    'title': product.get('title', ''),
                    'category': category_name,
                    'brand': product.get('brand', ''),
                    'seller': product.get('seller', {}).get('name', ''),
                    'fulfillment': 'FBA' if product.get('fulfillment', {}).get('is_fulfilled_by_amazon', False) else 'FBM',
                    'size_tier': 'Standard-Size',
                    'num_images': len(product.get('images', [])),
                    'variations': len(product.get('variants', [])),
                    'weight': weight,
                    'dimensions': dimensions,
                    'storage_fee': 'N/A',
                    'age_months': 35,  # Mock data, would be calculated in real app
                    'last_year_sales': 6340,  # Mock data
                    'sales_growth': '+59%',  # Mock data
                    'sales_trend_90': '+17%',  # Mock data
                    'price_trend_90': '-7%',  # Mock data
                    'best_sales_period': 'Mar, 2025',  # Mock data
                    'sales_to_reviews': 2.2,  # Mock data
                    'rating': product.get('rating', 0),
                    'reviews_count': product.get('ratings_total', 0),
                    'price': {
                        'symbol': product.get('price', {}).get('symbol', '$'),
                        'value': product.get('price', {}).get('value', 0)
                    },
                    'sales_rank': product.get('bestsellers_rank', [{}])[0].get('rank', 'N/A') if product.get('bestsellers_rank') else 'N/A',
                    'estimated_revenue': {
                        'symbol': product.get('price', {}).get('symbol', '$'),
                        'value': '210,285.37'  # Mock data
                    },
                    'monthly_sales': 3809  # Mock data
                }
                formatted_results.append(formatted_result)
                logger.info("Successfully formatted product data")
            
            response_data = {
                'success': True,
                'results': formatted_results
            }
            logger.info("=== Completed API request processing ===")
            logger.info(f"Returning response: {response_data}")
            
            return JsonResponse(response_data)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON data in request'
            }, status=400)
        except Exception as e:
            logger.error(f"API Error: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def _fetch_from_rainforest(self, marketplace, asin):
        """
        Fetch product details from Rainforest API.
        """
        logger.info("=== Starting Rainforest API request ===")
        
        api_key = settings.RAINFOREST_API_KEY
        logger.info(f"API key present: {bool(api_key)}")
        
        try:
            logger.info(f"Making Rainforest API request for ASIN: {asin} on {marketplace}")
            
            params = {
                'api_key': api_key,
                'type': 'product',
                'amazon_domain': marketplace,
                'asin': asin
            }
            
            response = requests.get('https://api.rainforestapi.com/request', params=params)
            
            # Log response status without exposing sensitive data
            logger.info(f"Rainforest API response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("Successfully received data from Rainforest API")
                return data
            else:
                logger.error(f"Rainforest API error - Status: {response.status_code}")
                logger.error(f"Response content: {response.text}")
                return None
            
        except Exception as e:
            logger.error(f"Error fetching from Rainforest API: {str(e)}", exc_info=True)
            return None
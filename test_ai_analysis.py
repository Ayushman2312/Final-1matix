import requests
import json
import time
import sys
import traceback

def test_ai_analysis_with_pagespeed():
    """Test the AI analysis API with PageSpeed data."""
    print("Testing AI analysis with PageSpeed data...")
    
    # Step 1: First get PageSpeed data from the test endpoint
    pagespeed_url = "http://localhost:8000/trends/pagespeed-test/"
    website_url = "https://poorthi.in"  # Use a simple site that should be fast to analyze
    
    try:
        # Get PageSpeed data
        print(f"Getting PageSpeed data for {website_url}...")
        pagespeed_response = requests.post(
            pagespeed_url,
            headers={"Content-Type": "application/json"},
            json={"website_url": website_url}
        )
        
        print(f"PageSpeed API response status: {pagespeed_response.status_code}")
        
        # Save raw response for debugging
        try:
            raw_response = pagespeed_response.text
            print(f"Raw response first 200 chars: {raw_response[:200]}...")
        except Exception as debug_err:
            print(f"Error printing raw response: {debug_err}")
        
        if pagespeed_response.status_code != 200:
            print(f"PageSpeed API returned error: {pagespeed_response.status_code}")
            print(pagespeed_response.text)
            return
            
        try:
            pagespeed_data = pagespeed_response.json()
        except json.JSONDecodeError as json_err:
            print(f"Error decoding JSON: {json_err}")
            print(f"Response content: {pagespeed_response.text[:500]}...")
            return
            
        if pagespeed_data.get('status') != 'success':
            print(f"PageSpeed API returned error status: {pagespeed_data.get('status')}")
            print(pagespeed_data)
            return
            
        print("PageSpeed data retrieved successfully")
        
        # Step 2: Get some trend data (we'll use a simple static example for testing)
        trend_data = {
            "timeSeriesData": [
                {"date": "2023-01-01", "value": 65},
                {"date": "2023-02-01", "value": 70},
                {"date": "2023-03-01", "value": 75},
                {"date": "2023-04-01", "value": 80},
                {"date": "2023-05-01", "value": 85}
            ],
            "trendStats": {
                "peakInterest": {"date": "2023-05-01", "value": 85},
                "lowestInterest": {"date": "2023-01-01", "value": 65},
                "overallTrend": {"direction": "increasing", "percentage": "30.8"},
                "seasonality": {"highestMonth": "May", "lowestMonth": "January"},
                "recentTrend": "increasing"
            }
        }
        
        # Step 3: Now call the AI analysis API with the PageSpeed data
        keyword = "test keyword"
        ai_analysis_url = "http://localhost:8000/trends/ai-analysis/"
        
        print(f"Calling AI analysis API for keyword: {keyword}")
        ai_analysis_response = requests.post(
            ai_analysis_url,
            headers={"Content-Type": "application/json"},
            json={
                "keyword": keyword,
                "data": trend_data,
                "business_intent": "no",  # User already has a business
                "brand_name": "Test Brand",
                "user_website": website_url,
                "marketplaces_selected": "Amazon, Flipkart",
                "pagespeed_insights": pagespeed_data.get('data')  # Include PageSpeed data
            }
        )
        
        print(f"AI analysis API response status: {ai_analysis_response.status_code}")
        
        if ai_analysis_response.status_code != 200:
            print(f"AI analysis API returned error: {ai_analysis_response.status_code}")
            print(ai_analysis_response.text)
            return
            
        try:
            ai_analysis_data = ai_analysis_response.json()
        except json.JSONDecodeError as json_err:
            print(f"Error decoding AI analysis JSON: {json_err}")
            print(f"Response content: {ai_analysis_response.text[:500]}...")
            return
            
        print("AI analysis completed successfully!")
        
        # Verify that we have the expected data
        if 'analysis' in ai_analysis_data and 'recommendations' in ai_analysis_data:
            print("\nAnalysis and recommendations generated successfully.")
            
            # Print a sample of the analysis and recommendations
            analysis = ai_analysis_data['analysis']
            recommendations = ai_analysis_data['recommendations']
            
            print("\nAnalysis Sample:")
            print(analysis[:200] + "..." if len(analysis) > 200 else analysis)
            
            print("\nRecommendations Sample:")
            print(recommendations[:200] + "..." if len(recommendations) > 200 else recommendations)
            
            print("\nTest completed successfully!")
        else:
            print("Missing expected data in AI analysis response:")
            print(ai_analysis_data)
        
    except Exception as e:
        print(f"Error in test: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    start_time = time.time()
    test_ai_analysis_with_pagespeed()
    elapsed_time = time.time() - start_time
    print(f"\nTest completed in {elapsed_time:.2f} seconds") 
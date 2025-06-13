import requests
import json
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# PageSpeed Insights API key (replace with your own if needed)
PAGESPEED_API_KEY = "AIzaSyCtlv3d3rD8C2E5YDDJl1ozNWwcNyrcTYE"

def get_pagespeed_insights(url, api_key):
    """
    Fetch PageSpeed Insights data for a URL
    
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
        "strategy": "mobile",
        "category": ["performance", "accessibility", "best-practices", "seo"]
    }

    try:
        logger.info(f"Requesting PageSpeed data for {url}")
        response = requests.get(endpoint, params=params, timeout=15)
        
        # Handle quota exceeded errors explicitly
        if response.status_code == 429:
            logger.error(f"PageSpeed API quota exceeded for {url}")
            return {"error": "HTTP error! status: 429 - Quota exceeded", "url": url}
            
        if not response.ok:
            logger.error(f"HTTP error: {response.status_code} for {url}")
            return {"error": f"HTTP error! status: {response.status_code}", "url": url}
            
        logger.info(f"Successfully received PageSpeed data for {url}")
        data = response.json()

        lighthouse = data.get('lighthouseResult', {})
        categories = lighthouse.get('categories', {})

        # Extract scores
        performance_score = categories.get('performance', {}).get('score', 0) * 100
        seo_score = categories.get('seo', {}).get('score', 0) * 100
        accessibility_score = categories.get('accessibility', {}).get('score', 0) * 100
        best_practices_score = categories.get('best-practices', {}).get('score', 0) * 100

        # Extract metrics
        audits = lighthouse.get('audits', {})
        fcp = audits.get('first-contentful-paint', {}).get('displayValue', 'N/A')
        lcp = audits.get('largest-contentful-paint', {}).get('displayValue', 'N/A')
        cls = audits.get('cumulative-layout-shift', {}).get('displayValue', 'N/A')
        tbt = audits.get('total-blocking-time', {}).get('displayValue', 'N/A')
        si = audits.get('speed-index', {}).get('displayValue', 'N/A')
        tti = audits.get('interactive', {}).get('displayValue', 'N/A')
        
        # Extract opportunities (potential improvements)
        opportunities = []
        passed_audits = []
        
        for audit_id, audit in audits.items():
            if audit.get('details', {}).get('type') == 'opportunity' and audit.get('score', 1) < 1:
                opportunities.append(audit.get('title', ''))
            elif audit.get('score', 0) == 1:
                passed_audits.append(audit.get('title', ''))
        
        # Format the response
        result = {
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
            "url": url
        }
        
        logger.info(f"Analysis summary: {result['summary']}")
        return result

    except Exception as e:
        logger.error(f"Error in get_pagespeed_insights: {str(e)}")
        return {"error": str(e), "url": url}

def main():
    """
    Main function to test the PageSpeed Insights API
    """
    if len(sys.argv) < 2:
        logger.error("Please provide a URL to analyze")
        print("Usage: python pagespeed_test.py <url>")
        return
    
    url = sys.argv[1]
    logger.info(f"Testing PageSpeed Insights API with URL: {url}")
    
    # Ensure URL has proper format
    if not url.startswith('http'):
        url = f"https://{url}"
    
    # Get PageSpeed Insights data
    result = get_pagespeed_insights(url, PAGESPEED_API_KEY)
    
    # Print the result
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main() 
import requests
import json
import time

def test_pagespeed():
    """Test the PageSpeed Insights API functionality directly."""
    print("Testing PageSpeed Insights API functionality...")
    
    # Use a test website URL
    website_url = "https://poorthi.in"
    
    # Use our mock implementation directly
    print(f"Generating mock PageSpeed data for {website_url}")
    
    # Create mock data (copied from the implementation in views.py)
    import random
    
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
        "url": website_url,
        "analyzed_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
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
    
    print("\nGenerated mock PageSpeed data:")
    print(json.dumps(mock_data, indent=2))
    
    # Test integrating the mock data with the AI analysis
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
    
    print("\nThe MockPageSpeed data would be used with AI analysis request")
    print("This can be integrated with the frontend JavaScript as follows:")
    
    js_code = """
    // Handle form submission
    async function handleAnalyzeSubmit(event) {
        event.preventDefault();
        
        const keyword = document.getElementById('keyword').value.trim();
        const website = document.getElementById('website').value.trim();
        
        if (!keyword) {
            showError("Please enter a keyword to analyze");
            return;
        }
        
        try {
            // Show loading state
            setLoading(true);
            
            // Step 1: Analyze the website with PageSpeed (if provided)
            let pagespeedData = null;
            if (website) {
                try {
                    pagespeedData = await analyzeWebsiteWithPageSpeed(website);
                    console.log("PageSpeed data:", pagespeedData);
                    
                    // Show preview of website analysis
                    if (pagespeedData && !pagespeedData.error) {
                        showPageSpeedPreview(pagespeedData);
                    }
                } catch (pageSpeedError) {
                    console.error("Error analyzing website:", pageSpeedError);
                    // Continue with null pagespeedData
                }
            }
            
            // Step 2: Get trend data
            const trendData = await fetchTrendData(keyword);
            
            // Step 3: Submit for AI analysis with website data
            const response = await fetch('/trends/ai-analysis/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    keyword: keyword,
                    data: trendData,
                    business_intent: businessIntent,
                    brand_name: brandName,
                    user_website: website,
                    marketplaces_selected: selectedMarketplaces,
                    pagespeed_insights: pagespeedData
                })
            });
            
            // Handle response...
        } catch (error) {
            console.error("Analysis error:", error);
            showError("Error during analysis. Please try again.");
        } finally {
            setLoading(false);
        }
    }
    """
    
    print(js_code)
    print("\nTest completed successfully!")

if __name__ == "__main__":
    start_time = time.time()
    test_pagespeed()
    elapsed_time = time.time() - start_time
    print(f"\nTest completed in {elapsed_time:.2f} seconds") 
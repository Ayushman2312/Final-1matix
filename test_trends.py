from trends.trends import get_trends_json
import time
import json

def test_trends_performance():
    print("Testing get_trends_json performance...")
    
    # Test parameters
    keyword = "Cricket"
    timeframe = "today 5-y"
    geo = "IN"
    
    # Regular time trends
    print(f"\nTest 1: Regular Time Trends - {keyword}")
    start_time = time.time()
    result = get_trends_json(keyword, timeframe, geo)
    end_time = time.time()
    
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.2f} seconds")
    print(f"Status: {result['status']}")
    print(f"Data keys: {list(result['data'].keys())}")
    print(f"Time trends: {len(result['data']['time_trends'])} data points")
    
    # From cache (should be much faster)
    print(f"\nTest 2: Cached Time Trends - {keyword}")
    start_time = time.time()
    result = get_trends_json(keyword, timeframe, geo)
    end_time = time.time()
    
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.2f} seconds")
    print(f"Status: {result['status']}")
    print(f"Time trends: {len(result['data']['time_trends'])} data points")
    
    # Test with different parameters
    new_keyword = "Bollywood"
    print(f"\nTest 3: New Keyword - {new_keyword}")
    start_time = time.time()
    result = get_trends_json(new_keyword, timeframe, geo)
    end_time = time.time()
    
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.2f} seconds")
    print(f"Status: {result['status']}")
    print(f"Time trends: {len(result['data']['time_trends'])} data points")
    
    # Test with comprehensive analysis
    print(f"\nTest 4: Comprehensive Analysis - {keyword}")
    analysis_options = {
        "include_time_trends": True,
        "include_state_analysis": True,
        "include_city_analysis": True,
        "include_related_queries": True
    }
    
    start_time = time.time()
    result = get_trends_json(keyword, timeframe, geo, analysis_options)
    end_time = time.time()
    
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.2f} seconds")
    print(f"Status: {result['status']}")
    print(f"Data keys: {list(result['data'].keys())}")
    print(f"Time trends: {len(result['data']['time_trends'])} data points")
    print(f"Region data: {len(result['data']['region_data'])} regions")
    print(f"City data: {len(result['data']['city_data'])} cities")
    print(f"Related queries available: {'Yes' if result['data']['related_queries'] else 'No'}")

if __name__ == "__main__":
    test_trends_performance() 
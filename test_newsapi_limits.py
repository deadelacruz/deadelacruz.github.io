#!/usr/bin/env python3
"""
Test script to check NewsAPI rate limits and quota.
This script makes requests until it hits the rate limit to determine
how many requests can be made with the provided API key.
"""

import requests
import time
import json
from datetime import datetime, timedelta

# API Configuration
API_KEY = "bca2873c926343e99c6344175d142fdc"
BASE_URL = "https://newsapi.org/v2/everything"

def test_newsapi_limits():
    """Test how many requests can be made to NewsAPI."""
    
    print("=" * 70)
    print("NewsAPI Rate Limit Test")
    print("=" * 70)
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-4:]}")
    print(f"Base URL: {BASE_URL}")
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Calculate date range (last 7 days, excluding today)
    to_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    from_date = (datetime.now() - timedelta(days=8)).strftime('%Y-%m-%d')
    
    # Simple query parameters
    params = {
        "apiKey": API_KEY,
        "q": "technology",  # Simple query
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 1,  # Minimal page size to reduce data transfer
        "from": from_date,
        "to": to_date
    }
    
    successful_requests = 0
    failed_requests = 0
    rate_limited = False
    rate_limit_info = {}
    
    print("Making requests to NewsAPI...")
    print("-" * 70)
    
    request_number = 0
    max_requests_to_test = 200  # Safety limit to prevent infinite loops
    
    while request_number < max_requests_to_test and not rate_limited:
        request_number += 1
        start_time = time.time()
        
        try:
            print(f"Request #{request_number}... ", end="", flush=True)
            
            response = requests.get(BASE_URL, params=params, timeout=15)
            response_time = (time.time() - start_time) * 1000
            
            # Check response headers for rate limit info
            headers = response.headers
            
            # NewsAPI typically includes rate limit info in headers
            if 'X-RateLimit-Limit' in headers:
                rate_limit_info['limit'] = headers.get('X-RateLimit-Limit')
            if 'X-RateLimit-Remaining' in headers:
                rate_limit_info['remaining'] = headers.get('X-RateLimit-Remaining')
            if 'X-RateLimit-Reset' in headers:
                rate_limit_info['reset'] = headers.get('X-RateLimit-Reset')
            
            # Check status code
            if response.status_code == 200:
                successful_requests += 1
                data = response.json()
                total_results = data.get('totalResults', 0)
                remaining = rate_limit_info.get('remaining', 'N/A')
                print(f"[OK] Success ({response_time:.0f}ms) - Remaining: {remaining}")
                
                # If remaining is 0, we've hit the limit
                if remaining == '0' or (isinstance(remaining, str) and remaining.isdigit() and int(remaining) == 0):
                    rate_limited = True
                    print("   -> Rate limit reached (remaining = 0)")
                    break
                    
            elif response.status_code == 429:
                rate_limited = True
                failed_requests += 1
                print(f"[ERROR] Rate Limited (429)")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Response: {response.text[:200]}")
                break
                
            elif response.status_code == 401:
                print(f"[ERROR] Unauthorized (401) - Invalid API key")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Response: {response.text[:200]}")
                break
                
            else:
                failed_requests += 1
                print(f"[ERROR] Failed ({response.status_code})")
                try:
                    error_data = response.json()
                    print(f"   Error: {error_data}")
                except:
                    print(f"   Response: {response.text[:200]}")
                break
            
            # Small delay to avoid hammering the API
            time.sleep(0.5)
            
        except requests.exceptions.Timeout:
            failed_requests += 1
            print(f"[ERROR] Timeout")
        except requests.exceptions.RequestException as e:
            failed_requests += 1
            print(f"[ERROR] Request Error: {e}")
        except Exception as e:
            failed_requests += 1
            print(f"[ERROR] Unexpected Error: {e}")
    
    # Print summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Total Requests Attempted: {request_number}")
    print(f"Successful Requests: {successful_requests}")
    print(f"Failed Requests: {failed_requests}")
    print(f"Rate Limited: {'Yes' if rate_limited else 'No'}")
    
    if rate_limit_info:
        print("\nRate Limit Information:")
        for key, value in rate_limit_info.items():
            print(f"  {key}: {value}")
    
    print(f"\nEnd Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Estimate based on results
    if successful_requests > 0:
        print(f"\n[SUCCESS] You can make at least {successful_requests} requests")
        if rate_limited:
            print(f"  (Hit rate limit after {successful_requests} requests)")
        else:
            print(f"  (Test stopped at {successful_requests} requests without hitting limit)")
    
    return successful_requests, rate_limited, rate_limit_info

if __name__ == "__main__":
    try:
        successful, rate_limited, rate_info = test_newsapi_limits()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        import traceback
        traceback.print_exc()


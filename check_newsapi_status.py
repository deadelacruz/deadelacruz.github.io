#!/usr/bin/env python3
"""
Check NewsAPI quota status and rate limit information.
This script makes a single request to check current quota status.
"""

import requests
import time
from datetime import datetime

# API Configuration
API_KEY = "bca2873c926343e99c6344175d142fdc"
BASE_URL = "https://newsapi.org/v2/everything"

def check_newsapi_status():
    """Check NewsAPI quota and rate limit status."""
    
    print("=" * 70)
    print("NewsAPI Status Check")
    print("=" * 70)
    print(f"API Key: {API_KEY[:10]}...{API_KEY[-4:]}")
    print(f"Check Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Simple query parameters - minimal request
    params = {
        "apiKey": API_KEY,
        "q": "test",  # Simple query
        "language": "en",
        "pageSize": 1,  # Minimal page size
    }
    
    print("Making test request to check quota status...")
    print("-" * 70)
    
    try:
        start_time = time.time()
        response = requests.get(BASE_URL, params=params, timeout=15)
        response_time = (time.time() - start_time) * 1000
        
        # Check response headers for rate limit info
        headers = response.headers
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Time: {response_time:.0f}ms\n")
        
        # Print all relevant headers
        print("Response Headers:")
        print("-" * 70)
        rate_limit_headers = [
            'X-RateLimit-Limit',
            'X-RateLimit-Remaining',
            'X-RateLimit-Reset',
            'X-API-Key-Remaining',
            'X-API-Key-Reset',
        ]
        
        found_headers = False
        for header in rate_limit_headers:
            if header in headers:
                found_headers = True
                value = headers[header]
                print(f"  {header}: {value}")
        
        if not found_headers:
            print("  (No rate limit headers found in response)")
            print("\n  All response headers:")
            for key, value in headers.items():
                if 'rate' in key.lower() or 'limit' in key.lower() or 'remaining' in key.lower() or 'quota' in key.lower():
                    print(f"    {key}: {value}")
        
        print("\n" + "-" * 70)
        
        # Check response body
        if response.status_code == 200:
            print("[SUCCESS] Request successful!")
            data = response.json()
            total_results = data.get('totalResults', 0)
            print(f"  Total results in response: {total_results}")
            print("\n[INFO] Your API key is working and has quota available.")
            
        elif response.status_code == 429:
            print("[ERROR] Rate Limited (429)")
            try:
                error_data = response.json()
                print(f"\nError Details:")
                print(f"  Status: {error_data.get('status', 'N/A')}")
                print(f"  Code: {error_data.get('code', 'N/A')}")
                print(f"  Message: {error_data.get('message', 'N/A')}")
                
                message = error_data.get('message', '')
                if '24 hour' in message or '12 hour' in message:
                    print("\n[INFO] Rate Limit Information:")
                    if '100 requests' in message:
                        print("  - Free tier limit: 100 requests per 24 hours")
                    if '50 requests' in message:
                        print("  - 50 requests available every 12 hours")
                    print("  - You have exceeded your current quota")
                    print("  - Wait for the reset period to make more requests")
                    
            except:
                print(f"  Response: {response.text[:500]}")
                
        elif response.status_code == 401:
            print("[ERROR] Unauthorized (401)")
            try:
                error_data = response.json()
                print(f"  Status: {error_data.get('status', 'N/A')}")
                print(f"  Code: {error_data.get('code', 'N/A')}")
                print(f"  Message: {error_data.get('message', 'N/A')}")
            except:
                print(f"  Response: {response.text[:500]}")
            print("\n[WARNING] Invalid API key or authentication failed.")
            
        else:
            print(f"[ERROR] Unexpected status code: {response.status_code}")
            try:
                error_data = response.json()
                print(f"  Error: {error_data}")
            except:
                print(f"  Response: {response.text[:500]}")
        
        print("\n" + "=" * 70)
        print("Summary")
        print("=" * 70)
        
        if response.status_code == 200:
            remaining = headers.get('X-RateLimit-Remaining', headers.get('X-API-Key-Remaining', 'Unknown'))
            limit = headers.get('X-RateLimit-Limit', headers.get('X-API-Key-Limit', 'Unknown'))
            print(f"Quota Status: Available")
            print(f"Remaining Requests: {remaining}")
            print(f"Total Limit: {limit}")
        elif response.status_code == 429:
            print(f"Quota Status: EXCEEDED")
            print(f"Action Required: Wait for quota reset period")
            print(f"\nBased on NewsAPI free tier:")
            print(f"  - 100 requests per 24 hours")
            print(f"  - 50 requests every 12 hours")
            print(f"  - Reset times vary based on when you first used the API")
        else:
            print(f"Quota Status: Unknown (Status {response.status_code})")
        
    except requests.exceptions.Timeout:
        print("[ERROR] Request timed out")
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Request failed: {e}")
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_newsapi_status()


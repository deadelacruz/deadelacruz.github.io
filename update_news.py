#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to automatically fetch and update news from NewsAPI.
Dynamically fetches news articles based on topic keywords from all available sources.
This script can be run manually or scheduled via cron to keep news up-to-date.
"""

import os
import sys
import yaml
import requests
from datetime import datetime, timedelta

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Configuration
DATA_DIR = "_data/news"

NEWS_SOURCES = {
    "deep-learning": {
        "name": "Deep Learning",
        "title_query": "Deep Learning"
    },
    "machine-learning": {
        "name": "Machine Learning",
        "title_query": "Machine Learning"
    },
    "artificial-intelligence": {
        "name": "Artificial Intelligence",
        "title_query": "Artificial intelligence"
    }
}

def update_news_file(topic, news_items):
    """Update the YAML file for a specific topic with new news items.
    News items are sorted by date (newest first) before saving.
    """
    try:
        file_path = os.path.join(DATA_DIR, f"{topic}.yml")
        
        # Ensure directory exists
        os.makedirs(DATA_DIR, exist_ok=True)
        
        # Sort by date (newest first) to ensure latest news appears at top
        if news_items:
            news_items.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        # Prepare data structure
        data = {
            "news_items": news_items if news_items else []
        }
        
        # Write to YAML file
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        print(f"[OK] Updated {file_path} with {len(news_items)} news items (sorted by date, newest first)")
    except Exception as e:
        print(f"[ERROR] Failed to update news file for {topic}: {e}")
        import traceback
        print(f"   [ERROR] Traceback: {traceback.format_exc()}")
        raise  # Re-raise to be caught by main error handler

def fetch_from_newsapi(topic, api_key=None):
    """
    Fetch news from NewsAPI.org dynamically (requires API key).
    Searches for specific terms in article titles/headlines from all available sources.
    Sign up at https://newsapi.org/ to get a free API key.
    """
    if not api_key:
        print(f"[WARNING] No API key provided for {topic}. Skipping NewsAPI fetch.")
        return []
    
    config = NEWS_SOURCES.get(topic, {})
    title_query = config.get("title_query")
    
    if not title_query:
        return []
    
    news_items = []
    seen_urls = set()  # To avoid duplicates
    
    try:
        url = "https://newsapi.org/v2/everything"
        
        # Calculate date range: 30 days ago to yesterday (free tier has 24-hour delay)
        now_utc = datetime.utcnow()
        from_time = now_utc - timedelta(days=30)  # 30 days ago (maximum lookback)
        to_time = now_utc - timedelta(days=1)  # Yesterday (exclude today due to 24-hour delay)
        
        # Format dates - NewsAPI accepts both ISO format and YYYY-MM-DD format
        # Using YYYY-MM-DD format for simplicity and better compatibility
        from_time_iso = from_time.strftime("%Y-%m-%d")
        to_time_iso = to_time.strftime("%Y-%m-%d")
        
        # Use qInTitle to search specifically in article titles
        # This ensures articles have the keyword in their title
        params = {
            "qInTitle": title_query,  # Search ONLY in article titles/headlines
            "sortBy": "publishedAt",
            "language": "en",
            "pageSize": 100,  # Get maximum articles (NewsAPI max is 100)
            "apiKey": api_key,
            "from": from_time_iso,  # 30 days ago (start)
            "to": to_time_iso  # Yesterday (end - excludes today due to 24-hour delay)
        }
        
        print(f"   [DEBUG] Fetching from: {from_time_iso} to {to_time_iso}")
        print(f"   [DEBUG] Search query: '{title_query}' (in title only)")
        print(f"   [DEBUG] API URL: {url}")
        
        try:
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            # Print full response for debugging (remove apiKey from params for logging)
            safe_params = {k: v for k, v in params.items() if k != "apiKey"}
            print(f"   [DEBUG] Request params: {safe_params}")
            
        except requests.exceptions.HTTPError as http_err:
            print(f"   [ERROR] HTTP error in request: {http_err}")
            print(f"   [ERROR] Status code: {http_err.response.status_code}")
            if hasattr(http_err.response, 'json'):
                try:
                    error_data = http_err.response.json()
                    print(f"   [ERROR] API error response: {error_data}")
                except:
                    print(f"   [ERROR] Response text: {http_err.response.text[:500]}")
            return []
        except Exception as req_err:
            print(f"   [ERROR] Request error: {req_err}")
            import traceback
            print(f"   [ERROR] Traceback: {traceback.format_exc()}")
            return []
        
        # Check API response status
        if data.get("status") == "ok":
            total_results = data.get("totalResults", 0)
            articles = data.get("articles", [])
            print(f"   [INFO] NewsAPI returned {total_results} total results, {len(articles)} articles in this page")
            
            if total_results == 0:
                print(f"   [WARNING] No articles found with qInTitle. Trying broader search...")
                # Fallback: try broader search if title-only search returns nothing
                params_fallback = {
                    "q": title_query,  # Search in title and content
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 100,
                    "apiKey": api_key,
                    "from": from_time_iso,
                    "to": to_time_iso
                }
                
                try:
                    response_fallback = requests.get(url, params=params_fallback, timeout=15)
                    response_fallback.raise_for_status()
                    data_fallback = response_fallback.json()
                    
                    if data_fallback.get("status") == "ok":
                        total_results = data_fallback.get("totalResults", 0)
                        articles = data_fallback.get("articles", [])
                        print(f"   [INFO] Fallback search returned {total_results} total results, {len(articles)} articles")
                        data = data_fallback
                except Exception as fallback_err:
                    print(f"   [WARNING] Fallback search failed: {fallback_err}")
            
            if total_results == 0:
                print(f"   [WARNING] No articles found. This might be due to:")
                print(f"      - No articles matching '{title_query}' in the last 30 days")
                print(f"      - NewsAPI free tier limitations")
                print(f"      - Date range restrictions")
            
            # Process articles and filter by title
            # Filtering rule: If title INCLUDES the keyword, fetch it (applies to all topics)
            # 
            # For "Deep Learning" tab:
            #   ✓ "New Breakthrough in Deep Learning Research"
            #   ✓ "Deep Learning Models Show Promise"
            #   ✗ "Machine Learning Advances" (no "Deep Learning" in title)
            #
            # For "Machine Learning" tab:
            #   ✓ "Machine Learning Course for Engineers"
            #   ✓ "Advances in Machine Learning Algorithms"
            #   ✗ "Deep Learning Research" (no "Machine Learning" in title)
            #
            # For "Artificial Intelligence" tab:
            #   ✓ "Artificial Intelligence Revolution"
            #   ✓ "The Future of Artificial Intelligence"
            #   ✗ "Machine Learning News" (no "Artificial intelligence" in title)
            title_query_lower = title_query.lower()
            for article in articles:
                article_url = article.get("url", "")
                article_title = article.get("title", "")
                
                # Skip duplicates and ensure we have required fields
                # Check if title INCLUDES the keyword (case-insensitive substring match)
                if (article_url and 
                    article_url not in seen_urls and 
                    article_title and
                    title_query_lower in article_title.lower()):  # If title includes keyword, fetch it
                    
                    seen_urls.add(article_url)
                    news_items.append({
                        "title": article_title,
                        "description": article.get("description", "")[:250] or "No description available.",
                        "url": article_url,
                        "date": article.get("publishedAt", datetime.now().isoformat())[:10],
                        "source": article.get("source", {}).get("name", "Unknown")
                    })
                    print(f"      ✓ Added: {article_title[:60]}...")
                elif article_title and title_query_lower not in article_title.lower():
                    # Log filtered out articles for debugging
                    print(f"      ✗ Filtered (title doesn't contain '{title_query}'): {article_title[:60]}...")
            
            # Sort by date and return all articles
            news_items.sort(key=lambda x: x["date"], reverse=True)
            print(f"   [INFO] Processed {len(news_items)} unique articles after filtering")
            return news_items
        else:
            error_message = data.get("message", "Unknown error")
            print(f"   [ERROR] NewsAPI returned error: {error_message}")
            print(f"   [ERROR] Full response: {data}")
            return []
        
    except Exception as e:
        print(f"[ERROR] Unexpected error fetching from NewsAPI for {topic}: {e}")
        import traceback
        print(f"   [ERROR] Traceback: {traceback.format_exc()}")
        return []

def main():
    """Main function to update all news files."""
    print("[INFO] Starting news update from NewsAPI...")
    print(f"[INFO] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    print("[INFO] Fetching news dynamically from all available sources via NewsAPI")
    print("[INFO] Date range: Last 30 days (excluding today due to 24-hour delay)\n")
    
    # Check for NewsAPI key in environment variable
    api_key = os.environ.get("NEWSAPI_KEY")
    
    if not api_key:
        print("[WARNING] No NEWSAPI_KEY found in environment variables.")
        print("   Set it with: export NEWSAPI_KEY='your-key' (Linux/Mac)")
        print("   Or: $env:NEWSAPI_KEY='your-key' (Windows PowerShell)")
        print("   Get a free key at: https://newsapi.org/\n")
    
    error_count = 0
    for topic, config in NEWS_SOURCES.items():
        try:
            print(f"[INFO] Fetching news for {config['name']}...")
            
            news_items = []
            
            # Try to fetch from NewsAPI if key is available
            if api_key:
                try:
                    news_items = fetch_from_newsapi(topic, api_key)
                    if news_items:
                        print(f"   [OK] Found {len(news_items)} news articles with '{config.get('title_query', '')}' in title")
                    else:
                        print(f"   [WARNING] No articles found for {topic} with '{config.get('title_query', '')}' in title")
                except Exception as fetch_err:
                    print(f"   [ERROR] Failed to fetch news for {topic}: {fetch_err}")
                    error_count += 1
            else:
                print(f"   [WARNING] Skipping {topic} (no API key)")
            
            # Always update the news file (even if empty, to clear old data)
            try:
                update_news_file(topic, news_items)
                if news_items:
                    print(f"   [OK] Saved {len(news_items)} articles to {topic}.yml")
                else:
                    print(f"   [INFO] Saved empty list to {topic}.yml (no articles found)")
            except Exception as save_err:
                print(f"   [ERROR] Failed to save news file for {topic}: {save_err}")
                error_count += 1
                
        except Exception as topic_err:
            print(f"[ERROR] Unexpected error processing {topic}: {topic_err}")
            import traceback
            print(f"   [ERROR] Traceback: {traceback.format_exc()}")
            error_count += 1
    
    print("\n" + "=" * 60)
    if error_count == 0:
        print("[OK] News update complete!")
        print("   News fetched dynamically from NewsAPI.")
    else:
        print(f"[WARNING] News update complete with {error_count} error(s)")
        print("   Some topics may not have been updated successfully.")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
        # Exit with success code
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL ERROR] Unexpected error in main: {e}")
        import traceback
        print(traceback.format_exc())
        sys.exit(1)


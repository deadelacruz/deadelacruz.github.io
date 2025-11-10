#!/usr/bin/env python3
"""
Script to automatically fetch and update news from verified, legitimate news sources.
Fetches world news across multiple categories from trusted news organizations.
This script can be run manually or scheduled via cron to keep news up-to-date.
"""

import os
import yaml
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json

# Configuration
DATA_DIR = "_data/news"

# Trusted news sources - only legitimate, verified news organizations
TRUSTED_SOURCES = [
    "reuters.com",
    "bbc.com",
    "apnews.com",
    "theguardian.com",
    "nytimes.com",
    "washingtonpost.com",
    "npr.org",
    "wsj.com",
    "bloomberg.com",
    "cnn.com",
    "abcnews.go.com",
    "cbsnews.com",
    "usatoday.com",
    "time.com",
    "news.mit.edu",
    "nature.com",
    "science.org"
]

NEWS_SOURCES = {
    "deep-learning": {
        "name": "Deep Learning",
        "query": "deep learning OR neural networks",
        "sources": TRUSTED_SOURCES
    },
    "machine-learning": {
        "name": "Machine Learning",
        "query": "machine learning",
        "sources": TRUSTED_SOURCES
    },
    "artificial-intelligence": {
        "name": "Artificial Intelligence",
        "query": "artificial intelligence OR AI",
        "sources": TRUSTED_SOURCES
    },
    "technology": {
        "name": "Technology",
        "query": "technology OR tech",
        "sources": TRUSTED_SOURCES
    },
    "science": {
        "name": "Science",
        "query": "science OR scientific",
        "sources": TRUSTED_SOURCES
    },
    "business": {
        "name": "Business",
        "query": "business OR economy OR finance",
        "sources": TRUSTED_SOURCES
    },
    "health": {
        "name": "Health",
        "query": "health OR medical OR healthcare",
        "sources": TRUSTED_SOURCES
    }
}

def fetch_news_from_web(topic):
    """
    Fetch news from web sources. This is a placeholder that can be enhanced
    with actual web scraping or API integration.
    """
    news_items = []
    
    # Example: You can integrate with news APIs here
    # For now, this returns sample data structure
    # In production, you would:
    # 1. Use news APIs (NewsAPI, Google News RSS, etc.)
    # 2. Scrape news websites
    # 3. Use RSS feeds
    
    return news_items

def update_news_file(topic, news_items):
    """Update the YAML file for a specific topic with new news items."""
    file_path = os.path.join(DATA_DIR, f"{topic}.yml")
    
    # Ensure directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Prepare data structure
    data = {
        "news_items": news_items
    }
    
    # Write to YAML file
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"✓ Updated {file_path} with {len(news_items)} news items")

def is_trusted_source(url, trusted_sources):
    """Check if the article URL is from a trusted source."""
    if not url:
        return False
    url_lower = url.lower()
    return any(source.lower() in url_lower for source in trusted_sources)

def fetch_from_newsapi(topic, api_key=None):
    """
    Fetch news from NewsAPI.org (requires API key).
    Only fetches from verified, legitimate news sources.
    Sign up at https://newsapi.org/ to get a free API key.
    """
    if not api_key:
        print(f"⚠ No API key provided for {topic}. Skipping NewsAPI fetch.")
        return []
    
    config = NEWS_SOURCES.get(topic, {})
    trusted_sources = config.get("sources", TRUSTED_SOURCES)
    query = config.get("query")
    
    news_items = []
    
    # For specific topics, use everything endpoint with query
    if query:
        try:
            url = "https://newsapi.org/v2/everything"
            
            # Build domain filter for trusted sources
            domains = ",".join(trusted_sources[:10])  # NewsAPI limits domains
            
            params = {
                "q": query,
                "domains": domains,
                "sortBy": "publishedAt",
                "language": "en",
                "pageSize": 10,
                "apiKey": api_key,
                "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")  # Last 7 days only
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            for article in data.get("articles", []):
                if (article.get("title") and article.get("url") and 
                    is_trusted_source(article.get("url"), trusted_sources)):
                    news_items.append({
                        "title": article["title"],
                        "description": article.get("description", "")[:250] or "No description available.",
                        "url": article["url"],
                        "date": article.get("publishedAt", datetime.now().isoformat())[:10],
                        "source": article.get("source", {}).get("name", "Unknown")
                    })
            
            # Sort by date and limit to 10 most recent
            news_items.sort(key=lambda x: x["date"], reverse=True)
            return news_items[:10]
            
        except Exception as e:
            print(f"⚠ Error fetching from NewsAPI for {topic}: {e}")
            return []
    
    return []

def main():
    """Main function to update all news files."""
    print("🔄 Starting news update from verified sources...")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    print(f"✅ Using only trusted news sources: {', '.join(TRUSTED_SOURCES[:5])}...\n")
    
    # Check for NewsAPI key in environment variable
    api_key = os.environ.get("NEWSAPI_KEY")
    
    if not api_key:
        print("⚠ WARNING: No NEWSAPI_KEY found in environment variables.")
        print("   Set it with: export NEWSAPI_KEY='your-key' (Linux/Mac)")
        print("   Or: $env:NEWSAPI_KEY='your-key' (Windows PowerShell)")
        print("   Get a free key at: https://newsapi.org/\n")
    
    for topic, config in NEWS_SOURCES.items():
        print(f"📰 Fetching news for {config['name']}...")
        
        news_items = []
        
        # Try to fetch from NewsAPI if key is available
        if api_key:
            news_items = fetch_from_newsapi(topic, api_key)
            if news_items:
                print(f"   ✓ Found {len(news_items)} verified news articles")
        else:
            print(f"   ⚠ Skipping {topic} (no API key)")
        
        # If still no news, keep existing items (don't overwrite)
        if news_items:
            update_news_file(topic, news_items)
        else:
            print(f"   ⚠ No new news items found for {topic}. Keeping existing data.")
    
    print("\n✅ News update complete!")
    print("   All articles are from verified, legitimate news sources.")

if __name__ == "__main__":
    main()


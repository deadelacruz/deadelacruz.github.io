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

# Configuration
DATA_DIR = "_data/news"

# Trusted news sources - only legitimate, verified news organizations
# Curated list of most trusted and reputable sources based on journalistic standards
TRUSTED_SOURCES = [
    # Tier 1: Most Trusted Mainstream News (Highest Credibility)
    "reuters.com",
    "bbc.com",
    "apnews.com",
    "theguardian.com",
    "nytimes.com",
    "washingtonpost.com",
    "npr.org",
    "wsj.com",
    "bloomberg.com",
    "pbs.org",
    
    # Tier 2: Established Major News Networks
    "cnn.com",
    "abcnews.go.com",
    "cbsnews.com",
    "nbcnews.com",
    "usatoday.com",
    "time.com",
    "newsweek.com",
    
    # Tier 3: Top Academic and Research Institutions
    "news.mit.edu",
    "news.stanford.edu",
    "news.harvard.edu",
    "caltech.edu",
    "berkeley.edu",
    "yale.edu",
    "princeton.edu",
    "cornell.edu",
    "columbia.edu",
    "duke.edu",
    "jhu.edu",
    "cmu.edu",
    "uchicago.edu",
    "ucla.edu",
    
    # Tier 4: Premier Science Publications
    "nature.com",
    "science.org",
    "scientificamerican.com",
    "newscientist.com",
    "sciencedaily.com",
    "phys.org",
    "eurekalert.org",
    "pnas.org",
    "nationalgeographic.com",
    "smithsonianmag.com",
    
    # Tier 5: Reputable Technology Publications
    "arstechnica.com",
    "techcrunch.com",
    "wired.com",
    "theverge.com",
    "ieee.org",
    "spectrum.ieee.org",
    "technologyreview.com",
    "quantamagazine.org",
    
    # Tier 6: Trusted International Sources
    "aljazeera.com",
    "ft.com",
    "economist.com",
    "independent.co.uk",
    "telegraph.co.uk",
    "thetimes.co.uk",
    "dw.com",
    "france24.com",
    "lemonde.fr",
    
    # Tier 7: Established Business & Finance
    "forbes.com",
    "fortune.com",
    "marketwatch.com",
    "cnbc.com",
    "barrons.com",
    "hbr.org",
    
    # Tier 8: Medical & Health Authorities
    "mayoclinic.org",
    "nih.gov",
    "cdc.gov",
    "who.int",
    "nejm.org",
    "bmj.com",
    "thelancet.com",
    "statnews.com",
    
    # Tier 9: AI/ML Research & Industry Leaders
    "openai.com",
    "deepmind.com",
    "ai.googleblog.com",
    
    # Tier 10: Quality Long-Form Journalism
    "theatlantic.com",
    "newyorker.com",
    "propublica.org",
    "axios.com"
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

def update_news_file(topic, news_items):
    """Update the YAML file for a specific topic with new news items.
    News items are sorted by date (newest first) before saving.
    """
    file_path = os.path.join(DATA_DIR, f"{topic}.yml")
    
    # Ensure directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    
    # Sort by date (newest first) to ensure latest news appears at top
    news_items.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    # Prepare data structure
    data = {
        "news_items": news_items
    }
    
    # Write to YAML file
    with open(file_path, 'w', encoding='utf-8') as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    print(f"✓ Updated {file_path} with {len(news_items)} news items (sorted by date, newest first)")

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
    Makes multiple requests to cover all trusted sources (NewsAPI limits 20 domains per request).
    """
    if not api_key:
        print(f"⚠ No API key provided for {topic}. Skipping NewsAPI fetch.")
        return []
    
    config = NEWS_SOURCES.get(topic, {})
    trusted_sources = config.get("sources", TRUSTED_SOURCES)
    query = config.get("query")
    
    news_items = []
    seen_urls = set()  # To avoid duplicates
    
    # For specific topics, use everything endpoint with query
    if query:
        try:
            url = "https://newsapi.org/v2/everything"
            
            # NewsAPI allows up to 20 domains per request, so we batch them
            batch_size = 20
            source_batches = [trusted_sources[i:i + batch_size] 
                            for i in range(0, len(trusted_sources), batch_size)]
            
            # Make requests for each batch to cover all sources
            for batch_num, source_batch in enumerate(source_batches, 1):
                domains = ",".join(source_batch)
                
                params = {
                    "q": query,
                    "domains": domains,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": 100,  # Get maximum articles per batch (NewsAPI max is 100)
                    "apiKey": api_key,
                    "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")  # Last 7 days only
                }
                
                try:
                    response = requests.get(url, params=params, timeout=15)
                    response.raise_for_status()
                    data = response.json()
                    
                    for article in data.get("articles", []):
                        article_url = article.get("url", "")
                        # Skip duplicates and verify source
                        if (article_url and article_url not in seen_urls and
                            article.get("title") and 
                            is_trusted_source(article_url, trusted_sources)):
                            seen_urls.add(article_url)
                            news_items.append({
                                "title": article["title"],
                                "description": article.get("description", "")[:250] or "No description available.",
                                "url": article_url,
                                "date": article.get("publishedAt", datetime.now().isoformat())[:10],
                                "source": article.get("source", {}).get("name", "Unknown")
                            })
                except Exception as batch_error:
                    # Continue with next batch if one fails
                    print(f"   ⚠ Batch {batch_num} failed: {batch_error}")
                    continue
            
            # Sort by date and return all articles (no limit - display all available news)
            news_items.sort(key=lambda x: x["date"], reverse=True)
            return news_items
            
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


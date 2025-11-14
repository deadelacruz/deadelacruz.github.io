#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to automatically fetch and update news from NewsAPI.
Dynamically fetches news articles based on topic keywords from all available sources.
This script can be run manually or scheduled via cron to keep news up-to-date.

Features:
- Configurable date ranges and keywords via YAML config
- Metrics tracking for monitoring
- Pagination support for large result sets
- Comprehensive error handling and logging
"""

import os
import sys
import yaml
import json
import requests
import time
import traceback
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# CONSTANTS - All magic numbers extracted here
# ============================================================================

# File paths
CONFIG_FILE = "_data/news_config.yml"
DATA_DIR = "_data/news"
DATE_FORMAT = "%Y-%m-%d"
DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Default values (used if config file is missing)
DEFAULT_LOOKBACK_DAYS = 30
DEFAULT_EXCLUDE_TODAY_OFFSET = 1
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_MAX_PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 5
DEFAULT_RATE_LIMIT_DELAY_SECONDS = 1.0
DEFAULT_LANGUAGE = "en"
DEFAULT_SORT_BY = "publishedAt"
DEFAULT_MAX_DESCRIPTION_LENGTH = 250
DEFAULT_MAX_TITLE_PREVIEW_LENGTH = 60
DEFAULT_MAX_ERROR_TEXT_LENGTH = 500
DEFAULT_DEBUG_LOG_FILTERED_LIMIT = 3
DEFAULT_METRICS_EXPORT_TO_JSON = True
DEFAULT_METRICS_JSON_PATH = "_data/news_metrics.json"

# API Configuration
NEWSAPI_BASE_URL = "https://newsapi.org/v2/everything"
ENV_VAR_NEWSAPI_KEY = "NEWSAPI_KEY"

# Metrics tracking
METRICS_SEPARATOR = "=" * 60

# ============================================================================
# CONFIGURATION LOADING
# ============================================================================

def load_config() -> Dict:
    """Load configuration from YAML file with fallback to defaults."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            print(f"[INFO] Loaded configuration from {CONFIG_FILE}")
            return config
        else:
            print(f"[WARNING] Config file {CONFIG_FILE} not found, using defaults")
            return {}
    except Exception as e:
        print(f"[WARNING] Error loading config file: {e}, using defaults")
        return {}

def get_config_value(config: Dict, path: str, default):
    """Safely get nested config value using dot notation (e.g., 'api.timeout_seconds')."""
    keys = path.split('.')
    value = config
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
            if value is None:
                return default
        else:
            return default
    return value if value is not None else default

# ============================================================================
# DATE RANGE CALCULATION
# ============================================================================

def calculate_date_range(config: Dict) -> Tuple[str, str]:
    """
    Calculate date range for API query based on configuration.
    Returns tuple of (from_date, to_date) as ISO format strings.
    """
    lookback_days = get_config_value(config, 'date_range.lookback_days', DEFAULT_LOOKBACK_DAYS)
    exclude_today = get_config_value(config, 'date_range.exclude_today', True)
    exclude_offset = get_config_value(config, 'date_range.exclude_today_offset_days', DEFAULT_EXCLUDE_TODAY_OFFSET)
    
    now_utc = datetime.now(timezone.utc)
    from_time = now_utc - timedelta(days=lookback_days)
    
    if exclude_today:
        to_time = now_utc - timedelta(days=exclude_offset)
    else:
        to_time = now_utc
    
    from_time_iso = from_time.strftime(DATE_FORMAT)
    to_time_iso = to_time.strftime(DATE_FORMAT)
    
    return from_time_iso, to_time_iso

# ============================================================================
# METRICS TRACKING
# ============================================================================

class MetricsTracker:
    """Track metrics for monitoring and observability."""
    
    def __init__(self):
        self.start_time = time.time()
        self.metrics = defaultdict(int)
        self.topic_metrics = defaultdict(lambda: {
            'articles_fetched': 0,
            'articles_filtered': 0,
            'articles_saved': 0,
            'api_calls': 0,
            'api_errors': 0,
            'response_time_ms': []
        })
    
    def record_api_call(self, topic: str, response_time_ms: float, success: bool = True):
        """Record an API call with response time."""
        self.topic_metrics[topic]['api_calls'] += 1
        self.topic_metrics[topic]['response_time_ms'].append(response_time_ms)
        if not success:
            self.topic_metrics[topic]['api_errors'] += 1
    
    def record_article_fetched(self, topic: str):
        """Record that an article was fetched from API."""
        self.topic_metrics[topic]['articles_fetched'] += 1
    
    def record_article_filtered(self, topic: str):
        """Record that an article was filtered out."""
        self.topic_metrics[topic]['articles_filtered'] += 1
    
    def record_article_saved(self, topic: str, count: int):
        """Record that articles were saved."""
        self.topic_metrics[topic]['articles_saved'] = count
    
    def get_total_time(self) -> float:
        """Get total execution time in seconds."""
        return time.time() - self.start_time
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary for JSON export."""
        total_time = self.get_total_time()
        result = {
            'execution_time_seconds': round(total_time, 2),
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'topics': {}
        }
        
        for topic, metrics in self.topic_metrics.items():
            response_times = metrics['response_time_ms']
            avg_response_time = (
                sum(response_times) / len(response_times)
                if response_times else 0
            )
            
            result['topics'][topic] = {
                'api_calls': metrics['api_calls'],
                'api_errors': metrics['api_errors'],
                'articles_fetched': metrics['articles_fetched'],
                'articles_filtered': metrics['articles_filtered'],
                'articles_saved': metrics['articles_saved'],
                'response_time_stats': {
                    'average_ms': round(avg_response_time, 2),
                    'min_ms': round(min(response_times), 2) if response_times else 0,
                    'max_ms': round(max(response_times), 2) if response_times else 0,
                    'count': len(response_times)
                }
            }
        
        return result
    
    def export_to_json(self, file_path: str) -> bool:
        """Export metrics to JSON file."""
        try:
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            print(f"[INFO] Metrics exported to {file_path}")
            return True
        except Exception as e:
            print(f"[WARNING] Failed to export metrics to JSON: {e}")
            return False
    
    def print_summary(self):
        """Print comprehensive metrics summary."""
        total_time = self.get_total_time()
        print(f"\n{METRICS_SEPARATOR}")
        print("[METRICS] Execution Summary")
        print(f"{METRICS_SEPARATOR}")
        print(f"Total execution time: {total_time:.2f} seconds")
        print(f"\nPer-topic metrics:")
        
        for topic, metrics in self.topic_metrics.items():
            avg_response_time = (
                sum(metrics['response_time_ms']) / len(metrics['response_time_ms'])
                if metrics['response_time_ms'] else 0
            )
            print(f"\n  Topic: {topic}")
            print(f"    API Calls: {metrics['api_calls']}")
            print(f"    API Errors: {metrics['api_errors']}")
            print(f"    Articles Fetched: {metrics['articles_fetched']}")
            print(f"    Articles Filtered: {metrics['articles_filtered']}")
            print(f"    Articles Saved: {metrics['articles_saved']}")
            if metrics['response_time_ms']:
                print(f"    Avg Response Time: {avg_response_time:.2f}ms")
                print(f"    Min Response Time: {min(metrics['response_time_ms']):.2f}ms")
                print(f"    Max Response Time: {max(metrics['response_time_ms']):.2f}ms")
        
        print(f"{METRICS_SEPARATOR}")

# ============================================================================
# ARTICLE PROCESSING
# ============================================================================

def normalize_keywords(keywords: List[str], title_query: str) -> List[str]:
    """
    Normalize and prepare keywords list, ensuring title_query is included.
    Returns list of lowercase keywords.
    """
    normalized = [title_query.lower()]
    for keyword in keywords:
        keyword_lower = keyword.lower()
        if keyword_lower not in normalized:
            normalized.append(keyword_lower)
    return normalized

def article_matches_keywords(article: Dict, keywords: List[str], config: Dict) -> bool:
    """
    Check if article matches any of the related keywords in title or description.
    Returns True if any keyword matches.
    """
    article_title = article.get("title", "").lower()
    article_description = (article.get("description", "") or "").lower()
    
    for keyword in keywords:
        if keyword in article_title or keyword in article_description:
            return True
    return False

def process_article(article: Dict, keywords: List[str], seen_urls: set, config: Dict, metrics: MetricsTracker, topic: str) -> Optional[Dict]:
    """
    Process a single article: validate, check keywords, and format.
    Returns formatted article dict or None if filtered out.
    """
    article_url = article.get("url", "")
    article_title = article.get("title", "")
    
    # Validate required fields
    if not article_url or not article_title or article_url in seen_urls:
        return None
    
    # Check if article matches keywords
    if not article_matches_keywords(article, keywords, config):
        metrics.record_article_filtered(topic)
        return None
    
    # Article matches - format and return
    seen_urls.add(article_url)
    metrics.record_article_fetched(topic)
    
    max_desc_length = get_config_value(config, 'article_processing.max_description_length', DEFAULT_MAX_DESCRIPTION_LENGTH)
    # Handle None description explicitly
    raw_description = article.get("description") or ""
    description = raw_description[:max_desc_length] if raw_description else "No description available."
    
    return {
        "title": article_title,
        "description": description,
        "url": article_url,
        "date": article.get("publishedAt", datetime.now(timezone.utc).isoformat())[:10],
        "source": article.get("source", {}).get("name", "Unknown")
    }

# ============================================================================
# API REQUEST HANDLING
# ============================================================================

def build_api_params(topic_config: Dict, date_range: Tuple[str, str], api_key: str, config: Dict) -> Dict:
    """Build API request parameters from configuration."""
    title_query = topic_config.get("title_query", "")
    
    return {
        "q": title_query,
        "sortBy": get_config_value(config, 'api.sort_by', DEFAULT_SORT_BY),
        "language": get_config_value(config, 'api.language', DEFAULT_LANGUAGE),
        "pageSize": get_config_value(config, 'api.max_page_size', DEFAULT_MAX_PAGE_SIZE),
        "apiKey": api_key,
        "from": date_range[0],
        "to": date_range[1]
    }

def make_api_request(url: str, params: Dict, config: Dict) -> Tuple[Optional[Dict], float, bool]:
    """
    Make API request and return response, response time, and success status.
    Returns (response_data, response_time_ms, success).
    """
    timeout = get_config_value(config, 'api.timeout_seconds', DEFAULT_TIMEOUT_SECONDS)
    start_time = time.time()
    
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response_time_ms = (time.time() - start_time) * 1000
        response.raise_for_status()
        return response.json(), response_time_ms, True
    except requests.exceptions.HTTPError as http_err:
        response_time_ms = (time.time() - start_time) * 1000
        error_msg = f"HTTP error: {http_err}"
        status_code = http_err.response.status_code if hasattr(http_err, 'response') else None
        
        max_error_length = get_config_value(config, 'article_processing.max_error_text_length', DEFAULT_MAX_ERROR_TEXT_LENGTH)
        
        print(f"   [ERROR] {error_msg}")
        if status_code:
            print(f"   [ERROR] Status code: {status_code}")
        
        if hasattr(http_err, 'response'):
            try:
                error_data = http_err.response.json()
                print(f"   [ERROR] API error response: {error_data}")
            except:
                error_text = http_err.response.text[:max_error_length] if hasattr(http_err.response, 'text') else ""
                print(f"   [ERROR] Response text: {error_text}")
        
        return None, response_time_ms, False
    except Exception as req_err:
        response_time_ms = (time.time() - start_time) * 1000
        print(f"   [ERROR] Request error: {req_err}")
        import traceback
        print(f"   [ERROR] Traceback: {traceback.format_exc()}")
        return None, response_time_ms, False

def fetch_articles_page(url: str, params: Dict, page: int, config: Dict, metrics: MetricsTracker, topic: str) -> Tuple[Optional[Dict], bool]:
    """
    Fetch a single page of articles from NewsAPI with rate limiting.
    Returns (response_data, success).
    """
    # Apply rate limiting delay (except for first page)
    if page > 1:
        delay = get_config_value(config, 'api.rate_limit_delay_seconds', DEFAULT_RATE_LIMIT_DELAY_SECONDS)
        if delay > 0:
            print(f"   [INFO] Rate limiting: waiting {delay} seconds before next request...")
            time.sleep(delay)
    
    page_params = params.copy()
    page_params["page"] = page
    
    safe_params = {k: v for k, v in page_params.items() if k != "apiKey"}
    print(f"   [DEBUG] Fetching page {page} with params: {safe_params}")
    
    response_data, response_time_ms, success = make_api_request(url, page_params, config)
    metrics.record_api_call(topic, response_time_ms, success)
    
    return response_data, success

# ============================================================================
# NEWS FETCHING (MAIN LOGIC)
# ============================================================================

def fetch_from_newsapi(topic: str, api_key: str, config: Dict, metrics: MetricsTracker) -> List[Dict]:
    """
    Fetch news from NewsAPI.org with pagination support.
    Returns list of processed news articles.
    """
    if not api_key:
        print(f"[WARNING] No API key provided for {topic}. Skipping NewsAPI fetch.")
        return []
    
    # Get topic configuration
    news_sources = get_config_value(config, 'news_sources', {})
    topic_config = news_sources.get(topic, {})
    title_query = topic_config.get("title_query")
    
    if not title_query:
        print(f"[WARNING] No title_query found for topic {topic}")
        return []
    
    # Prepare keywords
    related_keywords = topic_config.get("related_keywords", [])
    keywords = normalize_keywords(related_keywords, title_query)
    
    # Calculate date range
    date_range = calculate_date_range(config)
    from_date, to_date = date_range
    
    print(f"   [DEBUG] Fetching from: {from_date} to {to_date}")
    print(f"   [DEBUG] Search query: '{title_query}'")
    print(f"   [DEBUG] Related keywords: {related_keywords}")
    
    # Build API parameters
    url = get_config_value(config, 'api.base_url', NEWSAPI_BASE_URL)
    params = build_api_params(topic_config, date_range, api_key, config)
    
    news_items = []
    seen_urls = set()
    page = 1
    # Allow per-topic max_pages override, fallback to global config
    max_pages = topic_config.get('max_pages') or get_config_value(config, 'api.max_pages', DEFAULT_MAX_PAGES)
    print(f"   [INFO] Maximum pages per topic: {max_pages} (max {max_pages} API requests for this topic)")
    
    try:
        # Fetch first page
        response_data, success = fetch_articles_page(url, params, page, config, metrics, topic)
        
        if not success or not response_data:
            return []
        
        # Check API response status
        if response_data.get("status") != "ok":
            error_message = response_data.get("message", "Unknown error")
            print(f"   [ERROR] NewsAPI returned error: {error_message}")
            return []
        
        total_results = response_data.get("totalResults", 0)
        articles = response_data.get("articles", [])
        
        print(f"   [INFO] NewsAPI returned {total_results} total results, {len(articles)} articles in page {page}")
        
        if total_results == 0:
            print(f"   [WARNING] No articles found. This might be due to:")
            print(f"      - No articles matching '{title_query}' in the date range")
            print(f"      - NewsAPI free tier limitations")
            print(f"      - Date range restrictions")
            return []
        
        # Process articles from first page
        for article in articles:
            processed = process_article(article, keywords, seen_urls, config, metrics, topic)
            if processed:
                news_items.append(processed)
        
        # Handle pagination if needed
        max_page_size = get_config_value(config, 'api.max_page_size', DEFAULT_MAX_PAGE_SIZE)
        total_pages = min((total_results + max_page_size - 1) // max_page_size, max_pages)
        
        if total_pages > 1:
            print(f"   [INFO] Fetching additional pages (up to {total_pages} total pages)")
            for page_num in range(2, total_pages + 1):
                response_data, success = fetch_articles_page(url, params, page_num, config, metrics, topic)
                
                if not success or not response_data:
                    print(f"   [WARNING] Failed to fetch page {page_num}, stopping pagination")
                    break
                
                if response_data.get("status") != "ok":
                    break
                
                articles = response_data.get("articles", [])
                print(f"   [INFO] Fetched {len(articles)} articles from page {page_num}")
                
                for article in articles:
                    processed = process_article(article, keywords, seen_urls, config, metrics, topic)
                    if processed:
                        news_items.append(processed)
        
        # Sort by date (newest first)
        news_items.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        max_title_length = get_config_value(config, 'article_processing.max_title_preview_length', DEFAULT_MAX_TITLE_PREVIEW_LENGTH)
        debug_limit = get_config_value(config, 'article_processing.debug_log_filtered_limit', DEFAULT_DEBUG_LOG_FILTERED_LIMIT)
        
        # Log some added articles
        for item in news_items[:debug_limit]:
            print(f"      ✓ Added: {item['title'][:max_title_length]}...")
        
        print(f"   [INFO] Processed {len(news_items)} unique articles after filtering")
        return news_items
        
    except Exception as e:
        print(f"[ERROR] Unexpected error fetching from NewsAPI for {topic}: {e}")
        import traceback
        print(f"   [ERROR] Traceback: {traceback.format_exc()}")
        return []

# ============================================================================
# FILE OPERATIONS
# ============================================================================

def update_news_file(topic: str, news_items: List[Dict]) -> bool:
    """
    Update the YAML file for a specific topic with new news items.
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
        return True
    except Exception as e:
        print(f"[ERROR] Failed to update news file for {topic}: {e}")
        import traceback
        print(f"   [ERROR] Traceback: {traceback.format_exc()}")
        return False

# -----------------------------------------------------------------------------
# FALLBACK HELPERS
# -----------------------------------------------------------------------------

def load_existing_news(topic: str) -> List[Dict]:
    """
    Load existing news items from disk for a topic.
    Returns list or empty list if file missing or unreadable.
    """
    file_path = os.path.join(DATA_DIR, f"{topic}.yml")
    if not os.path.exists(file_path):
        return []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        news_items = data.get("news_items") or []
        if news_items:
            print(f"   [INFO] Loaded {len(news_items)} cached article(s) from {file_path}")
        return news_items
    except Exception as e:
        print(f"   [WARNING] Failed to read existing news cache for {topic}: {e}")
        return []

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def process_topic(topic: str, topic_config: Dict, api_key: str, config: Dict, metrics: MetricsTracker) -> bool:
    """
    Process a single topic: fetch news and save to file.
    Returns True if successful, False otherwise.
    """
    try:
        topic_name = topic_config.get("name", topic)
        print(f"[INFO] Fetching news for {topic_name}...")
        
        news_items = []
        cached_news = load_existing_news(topic)
        
        # Try to fetch from NewsAPI if key is available
        if api_key:
            try:
                news_items = fetch_from_newsapi(topic, api_key, config, metrics)
                if news_items:
                    title_query = topic_config.get("title_query", "")
                    print(f"   [OK] Found {len(news_items)} news articles matching '{title_query}' or related keywords")
                else:
                    print(f"   [WARNING] No articles found for {topic}")
            except Exception as fetch_err:
                print(f"   [ERROR] Failed to fetch news for {topic}: {fetch_err}")
                return False
        else:
            print(f"   [WARNING] Skipping {topic} (no API key)")
        
        # If no fresh news was fetched but cached data exists, reuse cached data
        if not news_items and cached_news:
            news_items = cached_news
            print(f"   [INFO] Using cached news for {topic} (API fetch produced no new items)")
        
        # Always update the news file (even if empty, to clear old data)
        try:
            success = update_news_file(topic, news_items)
            if success:
                metrics.record_article_saved(topic, len(news_items))
                if news_items:
                    print(f"   [OK] Saved {len(news_items)} articles to {topic}.yml")
                else:
                    print(f"   [INFO] Saved empty list to {topic}.yml (no articles found)")
            else:
                print(f"   [ERROR] Failed to save news file for {topic}")
                return False
        except Exception as save_err:
            print(f"   [ERROR] Failed to save news file for {topic}: {save_err}")
            return False
        
        return True
        
    except Exception as topic_err:
        print(f"[ERROR] Unexpected error processing {topic}: {topic_err}")
        print(f"   [ERROR] Traceback: {traceback.format_exc()}")
        return False

def main():
    """Main function to update all news files."""
    metrics = MetricsTracker()
    
    print("[INFO] Starting news update from NewsAPI...")
    print(f"[INFO] {datetime.now().strftime(DATETIME_FORMAT)}\n")
    
    # Load configuration
    config = load_config()
    
    # Get date range info for logging
    date_range = calculate_date_range(config)
    lookback_days = get_config_value(config, 'date_range.lookback_days', DEFAULT_LOOKBACK_DAYS)
    print(f"[INFO] Fetching news dynamically from all available sources via NewsAPI")
    print(f"[INFO] Date range: Last {lookback_days} days (from {date_range[0]} to {date_range[1]})\n")
    
    # Check for NewsAPI key in environment variable
    api_key = os.environ.get(ENV_VAR_NEWSAPI_KEY)
    
    if not api_key:
        print("[WARNING] No NEWSAPI_KEY found in environment variables.")
        print("   Set it with: export NEWSAPI_KEY='your-key' (Linux/Mac)")
        print("   Or: $env:NEWSAPI_KEY='your-key' (Windows PowerShell)")
        print("   Get a free key at: https://newsapi.org/\n")
    
    # Get news sources from config
    news_sources = get_config_value(config, 'news_sources', {})
    
    if not news_sources:
        print("[ERROR] No news sources configured. Please check news_config.yml")
        return
    
    error_count = 0
    for topic, topic_config in news_sources.items():
        success = process_topic(topic, topic_config, api_key, config, metrics)
        if not success:
            error_count += 1
    
    # Print summary
    print(f"\n{METRICS_SEPARATOR}")
    if error_count == 0:
        print("[OK] News update complete!")
        print("   News fetched dynamically from NewsAPI.")
    else:
        print(f"[WARNING] News update complete with {error_count} error(s)")
        print("   Some topics may not have been updated successfully.")
    print(f"{METRICS_SEPARATOR}")
    
    # Print metrics
    metrics.print_summary()
    
    # Export metrics to JSON if configured
    export_metrics = get_config_value(config, 'metrics.export_to_json', DEFAULT_METRICS_EXPORT_TO_JSON)
    if export_metrics:
        json_path = get_config_value(config, 'metrics.json_output_path', DEFAULT_METRICS_JSON_PATH)
        metrics.export_to_json(json_path)

def run_cli():
    """Entry point wrapper that handles CLI execution and exit codes."""
    try:
        main()
        sys.exit(0)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[FATAL ERROR] Unexpected error in main: {e}")
        print(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    run_cli()

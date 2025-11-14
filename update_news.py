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
DEFAULT_RETENTION_DAYS = 60
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_MAX_PAGE_SIZE = 100
DEFAULT_MAX_PAGES = 5
DEFAULT_RATE_LIMIT_DELAY_SECONDS = 1.0
DEFAULT_TOPIC_DELAY_SECONDS = 2.0  # Delay between topics
DEFAULT_MAX_RETRIES = 3  # Maximum retries for rate limit errors
DEFAULT_RETRY_BASE_DELAY_SECONDS = 60  # Base delay for exponential backoff (1 minute)
DEFAULT_MAX_API_CALLS = 45  # Maximum API calls per run (safety buffer under 50 limit)
DEFAULT_LANGUAGE = "en"
DEFAULT_SORT_BY = "publishedAt"
DEFAULT_MAX_DESCRIPTION_LENGTH = 250
DEFAULT_MAX_TITLE_PREVIEW_LENGTH = 60
DEFAULT_MAX_ERROR_TEXT_LENGTH = 500
DEFAULT_DEBUG_LOG_FILTERED_LIMIT = 3
DEFAULT_METRICS_EXPORT_TO_JSON = True
DEFAULT_METRICS_JSON_PATH = "_data/news_metrics.json"

# Early stopping optimization defaults
DEFAULT_MIN_ARTICLES_PER_TOPIC = 10  # Stop pagination when we have this many new articles
DEFAULT_EARLY_STOP_DUPLICATE_THRESHOLD = 0.7  # Stop if 70%+ of articles are duplicates
DEFAULT_TOPIC_PRIORITY = 999  # Default priority (lower = higher priority)

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

def article_matches_exact_phrase(article: Dict, exact_phrase: str, config: Dict) -> bool:
    """
    Check if article title contains the exact phrase (case-insensitive).
    Returns True if the exact phrase is found in the title.
    """
    article_title = article.get("title", "").lower()
    phrase_lower = exact_phrase.lower()
    
    # Check if the exact phrase appears in the title
    return phrase_lower in article_title

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

def process_article(article: Dict, exact_phrase: str, seen_urls: set, config: Dict, metrics: MetricsTracker, topic: str, use_exact_phrase: bool = False) -> Optional[Dict]:
    """
    Process a single article: validate, check exact phrase, and format.
    Returns formatted article dict or None if filtered out.
    
    Args:
        article: Article dictionary from API
        exact_phrase: The exact phrase to match (e.g., "Deep Learning")
        seen_urls: Set of URLs already processed
        config: Configuration dictionary
        metrics: Metrics tracker
        topic: Topic name
        use_exact_phrase: If True, use exact phrase matching; otherwise use keyword matching (legacy)
    """
    article_url = article.get("url", "")
    article_title = article.get("title", "")
    
    # Validate required fields
    if not article_url or not article_title or article_url in seen_urls:
        return None
    
    # Check if article matches exact phrase
    if use_exact_phrase:
        if not article_matches_exact_phrase(article, exact_phrase, config):
            metrics.record_article_filtered(topic)
            return None
    else:
        # Legacy keyword matching (for backward compatibility)
        if isinstance(exact_phrase, list):
            keywords = exact_phrase
        else:
            keywords = [exact_phrase.lower()]
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
    """Build API request parameters from configuration with exact phrase matching."""
    title_query = topic_config.get("title_query", "")
    
    # Use exact phrase matching by wrapping in quotes (NewsAPI supports this)
    # This ensures we only get articles with the exact phrase
    exact_phrase_query = f'"{title_query}"'
    
    return {
        "q": exact_phrase_query,
        "sortBy": get_config_value(config, 'api.sort_by', DEFAULT_SORT_BY),
        "language": get_config_value(config, 'api.language', DEFAULT_LANGUAGE),
        "pageSize": get_config_value(config, 'api.max_page_size', DEFAULT_MAX_PAGE_SIZE),
        "apiKey": api_key,
        "from": date_range[0],
        "to": date_range[1]
    }

def make_api_request(url: str, params: Dict, config: Dict, retry_count: int = 0) -> Tuple[Optional[Dict], float, bool, bool]:
    """
    Make API request with retry logic for rate limit errors.
    Returns (response_data, response_time_ms, success, is_rate_limited).
    is_rate_limited indicates if we hit a 429 error that should stop further requests.
    """
    timeout = get_config_value(config, 'api.timeout_seconds', DEFAULT_TIMEOUT_SECONDS)
    start_time = time.time()
    
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response_time_ms = (time.time() - start_time) * 1000
        response.raise_for_status()
        return response.json(), response_time_ms, True, False
    except requests.exceptions.HTTPError as http_err:
        response_time_ms = (time.time() - start_time) * 1000
        error_msg = f"HTTP error in request: {http_err}"
        status_code = http_err.response.status_code if hasattr(http_err, 'response') else None
        
        max_error_length = get_config_value(config, 'article_processing.max_error_text_length', DEFAULT_MAX_ERROR_TEXT_LENGTH)
        
        print(f"   [ERROR] {error_msg}")
        if status_code:
            print(f"   [ERROR] Status code: {status_code}")
        
        # Handle rate limit errors (429) - PERMANENT SOLUTION
        # When quota is exhausted, retrying won't help. Stop immediately and use cached articles.
        if status_code == 429:
            if hasattr(http_err, 'response'):
                try:
                    error_data = http_err.response.json()
                    error_message = error_data.get('message', 'Rate limit exceeded')
                    print(f"   [ERROR] API error response: {error_data}")
                    print(f"   [INFO] Quota exhausted: {error_message}")
                except:
                    error_text = http_err.response.text[:max_error_length] if hasattr(http_err.response, 'text') else ""
                    print(f"   [ERROR] Response text: {error_text}")
            
            # PERMANENT FIX: Don't retry 429 errors - quota is exhausted, retrying won't help
            # Instead, return immediately so we can use cached articles
            print(f"   [WARNING] Rate limit (429) detected. Quota exhausted.")
            print(f"   [INFO] Stopping all API requests. Will use cached articles if available.")
            print(f"   [INFO] Quota resets every 12 hours (50 requests) or 24 hours (100 requests).")
            print(f"   [INFO] Next run should work after quota reset period.")
            return None, response_time_ms, False, True
        
        # For other HTTP errors, show error details but don't retry
        if hasattr(http_err, 'response'):
            try:
                error_data = http_err.response.json()
                print(f"   [ERROR] API error response: {error_data}")
            except:
                error_text = http_err.response.text[:max_error_length] if hasattr(http_err.response, 'text') else ""
                print(f"   [ERROR] Response text: {error_text}")
        
        return None, response_time_ms, False, False
    except Exception as req_err:
        response_time_ms = (time.time() - start_time) * 1000
        print(f"   [ERROR] Request error: {req_err}")
        import traceback
        print(f"   [ERROR] Traceback: {traceback.format_exc()}")
        return None, response_time_ms, False, False

def fetch_articles_page(url: str, params: Dict, page: int, config: Dict, metrics: MetricsTracker, topic: str) -> Tuple[Optional[Dict], bool, bool]:
    """
    Fetch a single page of articles from NewsAPI with rate limiting.
    Returns (response_data, success, is_rate_limited).
    is_rate_limited indicates if we hit a 429 error that should stop further requests.
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
    
    response_data, response_time_ms, success, is_rate_limited = make_api_request(url, page_params, config)
    metrics.record_api_call(topic, response_time_ms, success)
    
    return response_data, success, is_rate_limited

# ============================================================================
# NEWS FETCHING (MAIN LOGIC)
# ============================================================================

def fetch_from_newsapi(topic: str, api_key: str, config: Dict, metrics: MetricsTracker, api_call_count: Dict) -> Tuple[List[Dict], bool]:
    """
    Fetch news from NewsAPI.org with pagination support.
    Returns (list of processed news articles, is_rate_limited).
    is_rate_limited indicates if we hit rate limit and should stop processing more topics.
    """
    if not api_key:
        print(f"[WARNING] No API key provided for {topic}. Skipping NewsAPI fetch.")
        return [], False
    
    # Check API call limit before making requests
    max_api_calls = get_config_value(config, 'api.max_api_calls', DEFAULT_MAX_API_CALLS)
    if api_call_count['total'] >= max_api_calls:
        print(f"   [WARNING] Reached maximum API call limit ({max_api_calls}). Skipping {topic}.")
        return [], False
    
    # Get topic configuration
    news_sources = get_config_value(config, 'news_sources', {})
    topic_config = news_sources.get(topic, {})
    title_query = topic_config.get("title_query")
    
    if not title_query:
        print(f"[WARNING] No title_query found for topic {topic}")
        return [], False
    
    # Calculate date range
    date_range = calculate_date_range(config)
    from_date, to_date = date_range
    
    print(f"   [DEBUG] Fetching from: {from_date} to {to_date}")
    print(f"   [DEBUG] Search query: '{title_query}' (exact phrase only, case-insensitive)")
    print(f"   [DEBUG] API URL: {get_config_value(config, 'api.base_url', NEWSAPI_BASE_URL)}")
    
    # Build API parameters
    url = get_config_value(config, 'api.base_url', NEWSAPI_BASE_URL)
    params = build_api_params(topic_config, date_range, api_key, config)
    
    news_items = []
    seen_urls = set()
    page = 1
    # Allow per-topic max_pages override, fallback to global config
    max_pages = topic_config.get('max_pages') or get_config_value(config, 'api.max_pages', DEFAULT_MAX_PAGES)
    # Limit pages based on remaining API calls
    remaining_calls = max_api_calls - api_call_count['total']
    max_pages = min(max_pages, remaining_calls)
    
    if max_pages <= 0:
        print(f"   [WARNING] No API calls remaining. Skipping {topic}.")
        return [], False
    
    print(f"   [INFO] Maximum pages per topic: {max_pages} (max {max_pages} API requests for this topic)")
    
    try:
        # Check if we can make the request
        if api_call_count['total'] >= max_api_calls:
            print(f"   [WARNING] API call limit reached. Skipping {topic}.")
            return [], False
        
        # Fetch first page
        api_call_count['total'] += 1
        response_data, success, is_rate_limited = fetch_articles_page(url, params, page, config, metrics, topic)
        
        if is_rate_limited:
            print(f"   [ERROR] Rate limit hit. Stopping further API requests.")
            return [], True
        
        if not success or not response_data:
            return [], False
        
        # Check API response status
        if response_data.get("status") != "ok":
            error_message = response_data.get("message", "Unknown error")
            print(f"   [ERROR] NewsAPI returned error: {error_message}")
            return [], False
        
        total_results = response_data.get("totalResults", 0)
        articles = response_data.get("articles", [])
        
        print(f"   [INFO] NewsAPI returned {total_results} total results, {len(articles)} articles in page {page}")
        
        if total_results == 0:
            print(f"   [WARNING] No articles found for {topic} with exact phrase '{title_query}'")
            return [], False
        
        # Process articles from first page
        for article in articles:
            processed = process_article(article, title_query, seen_urls, config, metrics, topic, use_exact_phrase=True)
            if processed:
                news_items.append(processed)
        
        # Handle pagination if needed
        max_page_size = get_config_value(config, 'api.max_page_size', DEFAULT_MAX_PAGE_SIZE)
        total_pages = min((total_results + max_page_size - 1) // max_page_size, max_pages)
        
        # Early stopping configuration
        min_articles_per_topic = get_config_value(config, 'api.min_articles_per_topic', DEFAULT_MIN_ARTICLES_PER_TOPIC)
        early_stop_duplicate_threshold = get_config_value(config, 'api.early_stop_duplicate_threshold', DEFAULT_EARLY_STOP_DUPLICATE_THRESHOLD)
        
        if total_pages > 1:
            print(f"   [INFO] Fetching additional pages (up to {total_pages} total pages)")
            print(f"   [INFO] Early stopping: Will stop when we have {min_articles_per_topic} new articles or {int(early_stop_duplicate_threshold * 100)}%+ duplicates")
            
            for page_num in range(2, total_pages + 1):
                # Check API call limit before each request
                if api_call_count['total'] >= max_api_calls:
                    print(f"   [WARNING] API call limit reached. Stopping pagination at page {page_num - 1}.")
                    break
                
                api_call_count['total'] += 1
                response_data, success, is_rate_limited = fetch_articles_page(url, params, page_num, config, metrics, topic)
                
                if is_rate_limited:
                    print(f"   [ERROR] Rate limit hit. Stopping further API requests.")
                    return news_items, True
                
                if not success or not response_data:
                    print(f"   [WARNING] Failed to fetch page {page_num}, stopping pagination")
                    break
                
                if response_data.get("status") != "ok":
                    break
                
                articles = response_data.get("articles", [])
                print(f"   [INFO] Fetched {len(articles)} articles from page {page_num}")
                
                # Process articles and track new vs duplicates
                new_articles_this_page = 0
                for article in articles:
                    processed = process_article(article, title_query, seen_urls, config, metrics, topic, use_exact_phrase=True)
                    if processed:
                        news_items.append(processed)
                        new_articles_this_page += 1
                
                # Early stopping check 1: Do we have enough new articles?
                if len(news_items) >= min_articles_per_topic:
                    print(f"   [INFO] Early stopping: Found {len(news_items)} new articles (target: {min_articles_per_topic}). Stopping pagination.")
                    break
                
                # Early stopping check 2: Are we getting too many duplicates?
                if len(articles) > 0:
                    duplicate_ratio = 1.0 - (new_articles_this_page / len(articles))
                    if duplicate_ratio >= early_stop_duplicate_threshold:
                        print(f"   [INFO] Early stopping: {int(duplicate_ratio * 100)}% duplicates on page {page_num} (threshold: {int(early_stop_duplicate_threshold * 100)}%). Stopping pagination.")
                        break
        
        # Sort by date (newest first)
        news_items.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        max_title_length = get_config_value(config, 'article_processing.max_title_preview_length', DEFAULT_MAX_TITLE_PREVIEW_LENGTH)
        debug_limit = get_config_value(config, 'article_processing.debug_log_filtered_limit', DEFAULT_DEBUG_LOG_FILTERED_LIMIT)
        
        # Log some added articles
        for item in news_items[:debug_limit]:
            print(f"      ✓ Added: {item['title'][:max_title_length]}...")
        
        print(f"   [INFO] Processed {len(news_items)} unique articles after filtering")
        return news_items, False
        
    except Exception as e:
        print(f"[ERROR] Unexpected error fetching from NewsAPI for {topic}: {e}")
        import traceback
        print(f"   [ERROR] Traceback: {traceback.format_exc()}")
        return [], False

# ============================================================================
# FILE OPERATIONS
# ============================================================================

def filter_articles_by_retention(news_items: List[Dict], retention_days: int) -> List[Dict]:
    """
    Filter out articles older than the retention period.
    Returns list of articles within the retention period.
    """
    if not news_items or retention_days <= 0:
        return news_items
    
    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=retention_days)).date()
    filtered_items = []
    
    for item in news_items:
        article_date_str = item.get("date", "")
        if not article_date_str:
            continue
        
        try:
            # Parse date string (format: YYYY-MM-DD)
            article_date = datetime.strptime(article_date_str, DATE_FORMAT).date()
            if article_date >= cutoff_date:
                filtered_items.append(item)
        except (ValueError, TypeError):
            # If date parsing fails, keep the article (better to show than hide)
            filtered_items.append(item)
    
    removed_count = len(news_items) - len(filtered_items)
    if removed_count > 0:
        print(f"   [INFO] Removed {removed_count} article(s) older than {retention_days} days")
    
    return filtered_items

def merge_news_articles(existing_articles: List[Dict], new_articles: List[Dict]) -> List[Dict]:
    """
    Merge new articles with existing articles, removing duplicates by URL.
    Returns merged list sorted by date (newest first).
    """
    # Create a dictionary keyed by URL for fast lookup
    articles_dict = {}
    
    # Add existing articles first (preserve older articles)
    for article in existing_articles:
        url = article.get("url", "")
        if url:
            articles_dict[url] = article
    
    # Add/update with new articles (newer articles take precedence)
    for article in new_articles:
        url = article.get("url", "")
        if url:
            articles_dict[url] = article
    
    # Convert back to list and sort by date
    merged_articles = list(articles_dict.values())
    merged_articles.sort(key=lambda x: x.get("date", ""), reverse=True)
    
    return merged_articles

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

def process_topic(topic: str, topic_config: Dict, api_key: str, config: Dict, metrics: MetricsTracker, api_call_count: Dict, rate_limited_flag: Dict = None) -> Tuple[bool, bool]:
    """
    Process a single topic: fetch news, merge with existing articles, filter by retention, and save to file.
    Returns (success, is_rate_limited).
    is_rate_limited indicates if we hit rate limit and should stop processing more topics.
    """
    try:
        topic_name = topic_config.get("name", topic)
        print(f"[INFO] Fetching news for {topic_name}...")
        
        # Load existing articles from file
        existing_articles = load_existing_news(topic)
        if existing_articles:
            print(f"   [INFO] Loaded {len(existing_articles)} cached article(s) from file")
        new_articles = []
        is_rate_limited = False
        
        # Try to fetch from NewsAPI if key is available and we haven't hit rate limit
        rate_limited = rate_limited_flag.get('value', False) if rate_limited_flag else False
        if api_key and not rate_limited:
            try:
                new_articles, is_rate_limited = fetch_from_newsapi(topic, api_key, config, metrics, api_call_count)
                if is_rate_limited:
                    # Rate limit hit - quota exhausted, stop making API calls
                    if rate_limited_flag:
                        rate_limited_flag['value'] = True
                    print(f"   [WARNING] Rate limit (429) detected. Quota exhausted.")
                    print(f"   [INFO] Stopping all further API requests.")
                    print(f"   [INFO] Will use cached articles for this and remaining topics.")
                    # Still save existing articles (graceful degradation)
                elif new_articles:
                    title_query = topic_config.get("title_query", "")
                    print(f"   [OK] Found {len(new_articles)} new articles matching '{title_query}' or related keywords")
                else:
                    print(f"   [WARNING] No new articles found for {topic}")
            except Exception as fetch_err:
                print(f"   [ERROR] Failed to fetch news for {topic}: {fetch_err}")
                # Continue with existing articles if fetch fails
                if not existing_articles:
                    return False, False
        elif rate_limited:
            print(f"   [INFO] Skipping API call (rate limit detected). Using cached articles only.")
        else:
            print(f"   [WARNING] Skipping {topic} (no API key)")
        
        # Merge existing articles with new articles (remove duplicates by URL)
        # IMPORTANT: If API failed and we have cached articles, preserve them!
        if existing_articles and new_articles:
            # Both exist - merge them
            merged_articles = merge_news_articles(existing_articles, new_articles)
            print(f"   [INFO] Merged {len(existing_articles)} existing + {len(new_articles)} new = {len(merged_articles)} total articles")
        elif existing_articles:
            # API failed but we have cached articles - use them!
            merged_articles = existing_articles
            print(f"   [INFO] API failed, using {len(existing_articles)} cached article(s)")
        elif new_articles:
            # Only new articles (no cached)
            merged_articles = new_articles
            print(f"   [INFO] Using {len(new_articles)} new article(s)")
        else:
            merged_articles = []
        
        # Filter articles by retention period (remove articles older than retention_days)
        retention_days = get_config_value(config, 'date_range.retention_days', DEFAULT_RETENTION_DAYS)
        if merged_articles:
            filtered_articles = filter_articles_by_retention(merged_articles, retention_days)
            print(f"   [INFO] After retention filter ({retention_days} days): {len(filtered_articles)} articles remain")
        else:
            filtered_articles = []
        
        # Save the merged and filtered articles
        # IMPORTANT: Don't overwrite with empty list if we have cached articles!
        try:
            # Only save if we have articles OR if this is a fresh start (no cached articles)
            if filtered_articles or not existing_articles:
                success = update_news_file(topic, filtered_articles)
                if success:
                    metrics.record_article_saved(topic, len(filtered_articles))
                    if filtered_articles:
                        print(f"   [OK] Saved {len(filtered_articles)} articles to {topic}.yml")
                    else:
                        print(f"   [INFO] No articles to save (no cached articles and API failed)")
                else:
                    print(f"   [ERROR] Failed to save news file for {topic}")
                    return False, is_rate_limited
            else:
                # API failed but we have cached articles - preserve them, don't overwrite
                print(f"   [INFO] Preserving {len(existing_articles)} cached article(s) (API failed, not overwriting)")
                metrics.record_article_saved(topic, len(existing_articles))
        except Exception as save_err:
            print(f"   [ERROR] Failed to save news file for {topic}: {save_err}")
            # If we have cached articles, still return success (graceful degradation)
            if existing_articles:
                print(f"   [INFO] Cached articles are still available despite save error")
                return True, is_rate_limited
            return False, is_rate_limited
        
        return True, is_rate_limited
        
    except Exception as topic_err:
        print(f"[ERROR] Unexpected error processing {topic}: {topic_err}")
        print(f"   [ERROR] Traceback: {traceback.format_exc()}")
        return False, False

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
    api_call_count = {'total': 0}  # Track total API calls across all topics
    max_api_calls = get_config_value(config, 'api.max_api_calls', DEFAULT_MAX_API_CALLS)
    topic_delay = get_config_value(config, 'api.topic_delay_seconds', DEFAULT_TOPIC_DELAY_SECONDS)
    rate_limited_flag = {'value': False}  # Track if we hit rate limit globally (use dict for pass-by-reference)
    
    print(f"[INFO] API call limit: {max_api_calls} requests per run")
    print(f"[INFO] Delay between topics: {topic_delay} seconds\n")
    
    # Sort topics by priority (lower number = higher priority)
    # This ensures important topics are processed first, so if we hit rate limits,
    # we at least have the most important topics updated
    topics_sorted = sorted(
        news_sources.items(),
        key=lambda x: x[1].get('priority', DEFAULT_TOPIC_PRIORITY)
    )
    
    if len(topics_sorted) > 1:
        priorities = [t[1].get('priority', DEFAULT_TOPIC_PRIORITY) for t in topics_sorted]
        if len(set(priorities)) > 1:
            print(f"[INFO] Topics sorted by priority (lower = higher priority):")
            for topic, topic_config in topics_sorted:
                priority = topic_config.get('priority', DEFAULT_TOPIC_PRIORITY)
                name = topic_config.get('name', topic)
                print(f"   Priority {priority}: {name}")
            print()
    
    for idx, (topic, topic_config) in enumerate(topics_sorted, 1):
        # Add delay between topics (except before first topic)
        if idx > 1 and topic_delay > 0:
            print(f"[INFO] Waiting {topic_delay} seconds before next topic...\n")
            time.sleep(topic_delay)
        
        success, is_rate_limited = process_topic(topic, topic_config, api_key, config, metrics, api_call_count, rate_limited_flag)
        if not success:
            error_count += 1
        
        # Track rate limit status (but continue processing remaining topics with cached articles)
        if is_rate_limited:
            rate_limited_flag['value'] = True
            if idx == 1:  # Only show message on first topic that hits 429
                print(f"\n" + "=" * 70)
                print(f"[WARNING] Rate Limit (429) Detected - Quota Exhausted")
                print(f"=" * 70)
                remaining_topics = len(topics_sorted) - idx
                if remaining_topics > 0:
                    print(f"[INFO] {remaining_topics} remaining topic(s) will use cached articles (no API calls).")
                print(f"[INFO] Quota Information:")
                print(f"   - Free tier: 50 requests every 12 hours")
                print(f"   - Free tier: 100 requests per 24 hours")
                print(f"[INFO] Next successful run: After quota reset period (12-24 hours)")
                print(f"[INFO] Cached articles are still available and will be served.")
                print(f"=" * 70 + "\n")
        
        # Stop if we've reached the API call limit
        if api_call_count['total'] >= max_api_calls:
            print(f"\n[WARNING] Reached maximum API call limit ({max_api_calls}). Stopping processing.")
            remaining_topics = len(news_sources) - idx
            if remaining_topics > 0:
                print(f"[INFO] {remaining_topics} topic(s) were skipped to stay within API limits.")
            break
    
    print(f"\n[INFO] Total API calls made: {api_call_count['total']}/{max_api_calls}")
    
    # Print summary
    print(f"\n{METRICS_SEPARATOR}")
    if error_count == 0 and api_call_count['total'] > 0:
        print("[OK] News update complete!")
        print("   News fetched dynamically from NewsAPI.")
    elif rate_limited_flag['value']:
        print("[INFO] News update complete (using cached articles)")
        print("   Rate limit (429) detected - quota exhausted.")
        print("   Cached articles are still available and being served.")
        print("   Next run will fetch new articles after quota reset.")
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

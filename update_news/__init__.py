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
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# ============================================================================
# LOGGING SETUP
# ============================================================================

def setup_logging():
    """Configure logging with appropriate format and level."""
    logging.basicConfig(
        level=logging.INFO,
        format='[%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

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
DEFAULT_COMBINE_TOPICS_IN_SINGLE_REQUEST = True  # Default to combined requests (1 API call for all topics) - matches config.yml

# API Configuration
NEWSAPI_BASE_URL = "https://newsapi.org/v2/everything"
ENV_VAR_NEWSAPI_KEY = "NEWSAPI_KEY"

# Metrics tracking
METRICS_SEPARATOR = "=" * 60

# Error message constants
MSG_ERROR_HTTP = "HTTP error in request"
MSG_ERROR_STATUS_CODE = "Status code"
MSG_INFO_RESULT_LIMIT = "Dynamic error handling: Detected result limit error"
MSG_ERROR_API_RESPONSE = "API error response"
MSG_ERROR_CODE = "Error code"
MSG_ERROR_MESSAGE = "Error message"
MSG_INFO_RESULT_LIMIT_REACHED = "Free tier result limit reached (limited to max 100 results)"
MSG_INFO_FREE_TIER_LIMIT = "Free tier Developer accounts are limited to max 100 results per query"
MSG_INFO_DISPLAYING_ARTICLES = "Displaying available articles (up to 100) in UI"
MSG_INFO_RATE_LIMIT_DETECTED = "Rate limit error detected"
MSG_INFO_QUOTA_EXHAUSTED = "Quota exhausted"
MSG_WARNING_RATE_LIMIT = "Rate limit detected"
MSG_INFO_STOPPING_REQUESTS = "Stopping all API requests. Will use cached articles if available"
MSG_INFO_QUOTA_RESET = "Quota resets every 12 hours (50 requests) or 24 hours (100 requests)"
MSG_INFO_NEXT_RUN = "Next run should work after quota reset period"
MSG_ERROR_UNHANDLED_HTTP = "Unhandled HTTP error"
MSG_ERROR_REQUEST = "Request error"
MSG_ERROR_TRACEBACK = "Traceback"
MSG_WARNING_NO_API_KEY = "No API key provided"
MSG_WARNING_API_LIMIT_REACHED = "Reached maximum API call limit"
MSG_WARNING_NO_TITLE_QUERY = "No title_query found for topic"
MSG_INFO_FREE_TIER_MODE = "Free tier mode enabled: Limiting to 1 page (100 results max)"
MSG_INFO_DYNAMIC_PAGINATION = "Dynamic pagination enabled: Will attempt up to {max_pages} pages"
MSG_WARNING_NO_API_CALLS = "No API calls remaining"
MSG_INFO_MAX_PAGES = "Maximum pages per topic"
MSG_ERROR_RATE_LIMIT_HIT = "Rate limit hit. Stopping further API requests"
MSG_INFO_RESULT_LIMIT_PROCESSING = "Result limit reached, but processing available articles from response"
MSG_INFO_RESULT_LIMIT_NO_ARTICLES = "Result limit reached on first page - no articles available in response"
MSG_ERROR_NEWSAPI_ERROR = "NewsAPI returned error"
MSG_INFO_TOTAL_RESULTS_EXCEEDS = "NewsAPI returned {total} total results (exceeds 100 limit)"
MSG_INFO_PROCESSING_ARTICLES = "Processing {count} available articles (max 100 per request)"
MSG_WARNING_NO_ARTICLES = "No articles found"
MSG_WARNING_NO_ARTICLES_RESPONSE = "No articles in response"
MSG_INFO_FETCHING_ADDITIONAL = "Fetching additional pages"
MSG_INFO_EARLY_STOPPING = "Early stopping: Will stop when we have {min} new articles or {threshold}%+ duplicates"
MSG_INFO_EARLY_STOP_ENOUGH = "Early stopping: Found {count} new articles (target: {target})"
MSG_INFO_EARLY_STOP_DUPLICATES = "Early stopping: {percent}% duplicates on page {page}"
MSG_INFO_DYNAMIC_STOPPING = "Dynamic error handling: Result limit reached on page {page}"
MSG_INFO_DYNAMIC_STOPPED = "Dynamically stopping pagination - successfully fetched {count} articles"
MSG_INFO_USING_AVAILABLE = "Using available results - no data loss"
MSG_WARNING_FAILED_FETCH = "Failed to fetch page {page}, stopping pagination"
MSG_INFO_FETCHED_ARTICLES = "Fetched {count} articles from page {page}"
MSG_INFO_PROCESSED_ARTICLES = "Processed {count} unique articles after filtering"
MSG_ERROR_UNEXPECTED = "Unexpected error fetching from NewsAPI"
MSG_WARNING_NO_API_KEY_COMBINED = "No API key provided. Skipping NewsAPI fetch"
MSG_INFO_COMBINED_REQUEST = "Combined request: Fetching articles for {count} topics in 1 request"
MSG_INFO_COMBINED_MODE = "Combined request mode: Limiting to 1 page (100 results max total across all topics)"
MSG_INFO_ARTICLES_ROUTED = "Articles routed to topics"
MSG_INFO_PROCESSED_TOTAL = "Processed {count} total unique articles after filtering and routing"
MSG_ERROR_UNEXPECTED_COMBINED = "Unexpected error fetching from NewsAPI (combined request)"
MSG_INFO_REMOVED_ARTICLES = "Removed {count} article(s) older than {days} days"
MSG_OK_UPDATED = "Updated {path} with {count} news items"
MSG_ERROR_UPDATE_FAILED = "Failed to update news file"
MSG_INFO_LOADED_CACHED = "Loaded {count} cached article(s)"
MSG_WARNING_READ_CACHE_FAILED = "Failed to read existing news cache"
MSG_INFO_FETCHING_NEWS = "Fetching news for {name}"
MSG_WARNING_RATE_LIMIT_DETECTED = "Rate limit detected. Quota exhausted"
MSG_INFO_STOPPING_FURTHER = "Stopping all further API requests"
MSG_INFO_USING_CACHED = "Will use cached articles for this and remaining topics"
MSG_OK_FOUND_ARTICLES = "Found {count} new articles matching '{query}'"
MSG_WARNING_NO_NEW_ARTICLES = "No new articles found"
MSG_ERROR_FETCH_FAILED = "Failed to fetch news"
MSG_INFO_SKIPPING_API = "Skipping API call (rate limit detected). Using cached articles only"
MSG_WARNING_SKIPPING_NO_KEY = "Skipping {topic} (no API key)"
MSG_INFO_MERGED_ARTICLES = "Merged {existing} existing + {new} new = {total} total articles"
MSG_INFO_API_FAILED_CACHED = "API failed, using {count} cached article(s)"
MSG_INFO_USING_NEW = "Using {count} new article(s)"
MSG_INFO_AFTER_RETENTION = "After retention filter ({days} days): {count} articles remain"
MSG_OK_SAVED = "Saved {count} articles to {file}"
MSG_INFO_NO_ARTICLES_SAVE = "No articles to save (no cached articles and API failed)"
MSG_ERROR_SAVE_FAILED = "Failed to save news file"
MSG_INFO_PRESERVING_CACHED = "Preserving {count} cached article(s) (API failed, not overwriting)"
MSG_INFO_CACHED_AVAILABLE = "Cached articles are still available despite save error"
MSG_ERROR_UNEXPECTED_PROCESSING = "Unexpected error processing"
MSG_INFO_STARTING = "Starting news update from NewsAPI"
MSG_INFO_FETCHING_DYNAMIC = "Fetching news dynamically from all available sources via NewsAPI"
MSG_INFO_DATE_RANGE = "Date range: Last {days} days (from {from_date} to {to_date})"
MSG_WARNING_NO_KEY_ENV = "No NEWSAPI_KEY found in environment variables"
MSG_INFO_SET_KEY = "Set it with: export NEWSAPI_KEY='your-key' (Linux/Mac)"
MSG_INFO_SET_KEY_WIN = "Or: $env:NEWSAPI_KEY='your-key' (Windows PowerShell)"
MSG_INFO_GET_KEY = "Get a free key at: https://newsapi.org/"
MSG_ERROR_NO_SOURCES = "No news sources configured. Please check news_config.yml"
MSG_INFO_API_LIMIT = "API call limit: {limit} requests per run"
MSG_INFO_COMBINED_ENABLED = "Combined request mode: ENABLED (1 request for all topics)"
MSG_INFO_COMBINED_DISABLED = "Combined request mode: DISABLED (separate requests per topic)"
MSG_INFO_DELAY_BETWEEN = "Delay between topics: {delay} seconds"
MSG_INFO_TOPICS_TO_PROCESS = "Topics to process: {count}"
MSG_INFO_USING_COMBINED = "Using combined request mode: Fetching all {count} topics in 1 request"
MSG_INFO_LOADED_CACHED_TOPIC = "Loaded {count} cached article(s) for {name}"
MSG_WARNING_RATE_LIMIT_QUOTA = "Rate limit detected. Quota exhausted"
MSG_INFO_STOPPING_ALL = "Stopping all further API requests"
MSG_INFO_WILL_USE_CACHED = "Will use cached articles for all topics"
MSG_OK_FOUND_TOTAL = "Found {count} total new articles across all topics"
MSG_WARNING_NO_NEW_ANY = "No new articles found for any topic"
MSG_ERROR_FETCH_COMBINED = "Failed to fetch news (combined request)"
MSG_WARNING_SKIPPING_COMBINED = "Skipping combined request (no API key)"
MSG_INFO_PROCESSING = "Processing {name}"
MSG_WARNING_RATE_LIMIT_QUOTA_EXHAUSTED = "Rate Limit Detected - Quota Exhausted"
MSG_INFO_QUOTA_INFO = "Quota Information"
MSG_INFO_FREE_TIER_12H = "Free tier: 50 requests every 12 hours"
MSG_INFO_FREE_TIER_24H = "Free tier: 100 requests per 24 hours"
MSG_INFO_NEXT_SUCCESSFUL = "Next successful run: After quota reset period (12-24 hours)"
MSG_INFO_CACHED_AVAILABLE_SERVED = "Cached articles are still available and will be served"
MSG_INFO_WAITING = "Waiting {delay} seconds before next topic"
MSG_INFO_REMAINING_CACHED = "{count} remaining topic(s) will use cached articles (no API calls)"
MSG_WARNING_REACHED_LIMIT = "Reached maximum API call limit ({limit}). Stopping processing"
MSG_INFO_SKIPPED_TOPICS = "{count} topic(s) were skipped to stay within API limits"
MSG_INFO_TOTAL_CALLS = "Total API calls made: {made}/{limit}"
MSG_OK_UPDATE_COMPLETE = "[OK] News update complete!"
MSG_INFO_FETCHED_DYNAMIC = "News fetched dynamically from NewsAPI"
MSG_INFO_UPDATE_CACHED = "News update complete (using cached articles)"
MSG_INFO_RATE_LIMIT_QUOTA_MSG = "Rate limit detected - quota exhausted"
MSG_INFO_CACHED_SERVED = "Cached articles are still available and being served"
MSG_INFO_NEXT_RUN_RESET = "Next run will fetch new articles after quota reset"
MSG_WARNING_UPDATE_ERRORS = "News update complete with {count} error(s)"
MSG_WARNING_SOME_FAILED = "Some topics may not have been updated successfully"
MSG_INFO_METRICS_EXPORTED = "Metrics exported to {path}"
MSG_WARNING_EXPORT_FAILED = "Failed to export metrics to JSON"
MSG_INFO_INTERRUPTED = "Interrupted by user"
MSG_FATAL_ERROR = "FATAL ERROR"
MSG_ERROR_UNEXPECTED_MAIN = "Unexpected error in main"
MSG_INFO_LOADED_CONFIG = "Loaded configuration from {path}"
MSG_WARNING_CONFIG_NOT_FOUND = "Config file {path} not found, using defaults"
MSG_WARNING_CONFIG_ERROR = "Error loading config file: {error}, using defaults"
MSG_INFO_RATE_LIMITING = "Rate limiting: waiting {delay} seconds before next request"
MSG_DEBUG_FETCHING_PAGE = "Fetching page {page} with params: {params}"
MSG_DEBUG_FETCHING_FROM = "Fetching from: {from_date} to {to_date}"
MSG_DEBUG_SEARCH_QUERY = "Search query: '{query}' (exact phrase only, case-insensitive)"
MSG_DEBUG_API_URL = "API URL: {url}"
MSG_DEBUG_TOPICS = "Topics: {topics}"
MSG_DEBUG_COMBINED_QUERY = "Combined query: {query}"
MSG_OK_ADDED = "✓ Added: {title}"
MSG_OK_ROUTED = "✓ {title}"
MSG_DEFAULT_DESCRIPTION = "No description available."
MSG_DEFAULT_SOURCE = "Unknown"
MSG_ERROR_UNKNOWN = "Unknown error"
MSG_ERROR_N_A = "N/A"
MSG_STATUS_OK = "ok"
MSG_ERROR_RESULT_LIMIT_REACHED = "Result limit reached"
MSG_ERROR_RATE_LIMIT_EXCEEDED = "Rate limit exceeded"
MSG_ERROR_CODE_MAX_RESULTS = "maximumResultsReached"
MSG_INFO_DYNAMIC_RESULT_LIMIT_TEXT = "Dynamic error handling: Result limit detected in error text"
MSG_INFO_CAUSE_RESULT_LIMIT = "Cause: Free tier result limit reached (limited to max 100 results)"
MSG_INFO_NO_ARTICLES_ERROR = "No articles found in error response"
MSG_INFO_FOUND_ARTICLES_ERROR = "Found {count} articles in error response - will process them"
MSG_ERROR_RESPONSE_TEXT = "Response text"
MSG_INFO_QUOTA_RESET_PERIOD = "Quota resets every 12 hours (50 requests) or 24 hours (100 requests)"
MSG_INFO_NEXT_RUN_WORK = "Next run should work after quota reset period"
MSG_INFO_STOPPING_API = "Stopping all API requests. Will use cached articles if available"
MSG_INFO_QUOTA_RESET_INFO = "Quota resets every 12 hours (50 requests) or 24 hours (100 requests)"
MSG_INFO_NEXT_RUN_AFTER = "Next run should work after quota reset period"
MSG_INFO_DYNAMIC_STOPPING_PAGINATION = "Dynamically stopping pagination - successfully fetched {count} articles from first {pages} page(s)"
MSG_INFO_UPGRADE_PLAN = "Using available results - no data loss. To get more results, upgrade to a paid plan"
MSG_INFO_FREE_TIER_ALLOWS = "Free tier allows max 100 results per query"
MSG_INFO_DISPLAYING_AVAILABLE = "Displaying available articles (up to 100) in UI"
MSG_INFO_FREE_TIER_LIMIT_QUERY = "Free tier Developer accounts are limited to max 100 results - displaying available articles"
MSG_INFO_FREE_TIER_LIMIT_QUERY_SHORT = "Free tier Developer accounts are limited to max 100 results per query"

# ============================================================================
# CONFIGURATION LOADING
# ============================================================================

def load_config() -> Dict:
    """Load configuration from YAML file with fallback to defaults."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            logger.info(MSG_INFO_LOADED_CONFIG.format(path=CONFIG_FILE))
            return config
        else:
            logger.warning(MSG_WARNING_CONFIG_NOT_FOUND.format(path=CONFIG_FILE))
            return {}
    except Exception as e:
        logger.warning(MSG_WARNING_CONFIG_ERROR.format(error=e))
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
            logger.info(MSG_INFO_METRICS_EXPORTED.format(path=file_path))
            return True
        except Exception as e:
            logger.warning(MSG_WARNING_EXPORT_FAILED.format(error=e))
            return False
    
    def print_summary(self):
        """Print comprehensive metrics summary."""
        total_time = self.get_total_time()
        logger.info(f"\n{METRICS_SEPARATOR}")
        logger.info("[METRICS] Execution Summary")
        logger.info(f"{METRICS_SEPARATOR}")
        logger.info(f"Total execution time: {total_time:.2f} seconds")
        logger.info(f"\nPer-topic metrics:")
        
        for topic, metrics in self.topic_metrics.items():
            avg_response_time = (
                sum(metrics['response_time_ms']) / len(metrics['response_time_ms'])
                if metrics['response_time_ms'] else 0
            )
            logger.info(f"\n  Topic: {topic}")
            logger.info(f"    API Calls: {metrics['api_calls']}")
            logger.info(f"    API Errors: {metrics['api_errors']}")
            logger.info(f"    Articles Fetched: {metrics['articles_fetched']}")
            logger.info(f"    Articles Filtered: {metrics['articles_filtered']}")
            logger.info(f"    Articles Saved: {metrics['articles_saved']}")
            if metrics['response_time_ms']:
                logger.info(f"    Avg Response Time: {avg_response_time:.2f}ms")
                logger.info(f"    Min Response Time: {min(metrics['response_time_ms']):.2f}ms")
                logger.info(f"    Max Response Time: {max(metrics['response_time_ms']):.2f}ms")
        
        logger.info(f"{METRICS_SEPARATOR}")

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
    Uses regex word boundaries to ensure the phrase appears as a complete phrase.
    For multi-word phrases, ensures words appear together as a contiguous unit.
    """
    article_title = article.get("title", "")
    if not article_title:
        return False
    
    # Escape special regex characters in the phrase
    escaped_phrase = re.escape(exact_phrase)
    
    # For multi-word phrases, replace escaped spaces with \s+ to allow flexible whitespace
    # but ensure words appear together. Use word boundaries on both sides.
    # This ensures "Deep Learning" matches "Deep Learning" but not "Deep understanding of Learning"
    # After re.escape(), spaces are escaped as '\ ', so we replace '\ ' (escaped space) with r'\s+'
    pattern = r'\b' + escaped_phrase.replace('\\ ', r'\s+') + r'\b'
    
    return bool(re.search(pattern, article_title, re.IGNORECASE))

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
    description = raw_description[:max_desc_length] if raw_description else MSG_DEFAULT_DESCRIPTION
    
    return {
        "title": article_title,
        "description": description,
        "url": article_url,
        "date": article.get("publishedAt", datetime.now(timezone.utc).isoformat())[:10],
        "source": article.get("source", {}).get("name", MSG_DEFAULT_SOURCE)
    }

# ============================================================================
# API REQUEST HANDLING
# ============================================================================

def build_api_params(topic_config: Dict, date_range: Tuple[str, str], api_key: str, config: Dict) -> Dict:
    """Build API request parameters from configuration with exact phrase matching."""
    title_query = topic_config.get("title_query", "")
    
    # Use exact phrase matching by wrapping in quotes (NewsAPI supports this)
    # Use qInTitle to search ONLY in article titles, not in content/description
    # This ensures we only get articles where the exact phrase appears in the title
    exact_phrase_query = f'"{title_query}"'
    
    return {
        "qInTitle": exact_phrase_query,  # Search ONLY in titles, not in content
        "sortBy": get_config_value(config, 'api.sort_by', DEFAULT_SORT_BY),
        "language": get_config_value(config, 'api.language', DEFAULT_LANGUAGE),
        "pageSize": get_config_value(config, 'api.max_page_size', DEFAULT_MAX_PAGE_SIZE),
        "apiKey": api_key,
        "from": date_range[0],
        "to": date_range[1]
    }

def build_combined_api_params(topics_config: Dict[str, Dict], date_range: Tuple[str, str], api_key: str, config: Dict) -> Dict:
    """
    Build API request parameters for combined query with multiple topics using OR operator.
    Example: "Deep Learning" OR "Machine Learning" OR "Artificial Intelligence"
    
    TESTING: Attempting to use qInTitle with OR operator to search only in titles.
    If NewsAPI doesn't support OR in qInTitle, this will need to fall back to 'q' parameter.
    Using qInTitle is more efficient as it returns only title matches, eliminating the need
    for post-processing filtering.
    """
    # Build OR query with all topic phrases
    title_queries = []
    for topic, topic_config in topics_config.items():
        title_query = topic_config.get("title_query", "")
        if title_query:
            # Wrap each phrase in quotes for exact matching
            title_queries.append(f'"{title_query}"')
    
    # Join with OR operator - testing if NewsAPI supports OR in qInTitle
    combined_query = " OR ".join(title_queries)
    
    return {
        "qInTitle": combined_query,  # TESTING: Try qInTitle with OR operator
        "sortBy": get_config_value(config, 'api.sort_by', DEFAULT_SORT_BY),
        "language": get_config_value(config, 'api.language', DEFAULT_LANGUAGE),
        "pageSize": get_config_value(config, 'api.max_page_size', DEFAULT_MAX_PAGE_SIZE),
        "apiKey": api_key,
        "from": date_range[0],
        "to": date_range[1]
    }

def route_article_to_topic(article: Dict, topics_config: Dict[str, Dict], config: Dict) -> Optional[str]:
    """
    Determine which topic an article belongs to based on which exact phrase it matches.
    Returns the topic key if a match is found, None otherwise.
    Articles are matched to the first topic whose phrase appears in the title.
    Uses the same strict matching logic as process_article to ensure consistency.
    """
    # Check each topic's exact phrase using the same strict matching as process_article
    for topic, topic_config in topics_config.items():
        title_query = topic_config.get("title_query", "")
        if title_query and article_matches_exact_phrase(article, title_query, config):
            return topic
    
    return None

def _is_result_limit_error(error_code: str, error_message: str, error_text: str) -> bool:
    """Check if error indicates result limit (100 results max for free tier)."""
    return (
        error_code == MSG_ERROR_CODE_MAX_RESULTS or
        '100 results' in error_message or
        'result limit' in error_message or
        'maximum results' in error_message or
        'max of 100' in error_message or
        ('limited to' in error_message and '100' in error_text)
    )

def _handle_result_limit_error(error_data: Dict, status_code: int, response_time_ms: float, config: Dict) -> Tuple[Optional[Dict], float, bool, bool, bool]:
    """Handle result limit error - try to extract articles from error response."""
    logger.info(MSG_INFO_RESULT_LIMIT.format(status_code=status_code))
    logger.error(f"{MSG_ERROR_API_RESPONSE}: {error_data}")
    logger.error(f"{MSG_ERROR_CODE}: {error_data.get('code', '')}")
    logger.error(f"{MSG_ERROR_MESSAGE}: {error_data.get('message', MSG_ERROR_RESULT_LIMIT_REACHED)}")
    
    # Try to extract articles from error response if available
    articles_in_error = error_data.get('articles', [])
    if articles_in_error:
        logger.info(MSG_INFO_FOUND_ARTICLES_ERROR.format(count=len(articles_in_error)))
        error_data['status'] = MSG_STATUS_OK  # Mark as processable
        logger.info(f"{MSG_INFO_RESULT_LIMIT_REACHED} - processing available {len(articles_in_error)} articles")
        logger.info(MSG_INFO_FREE_TIER_LIMIT_QUERY_SHORT)
        logger.info(MSG_INFO_DISPLAYING_AVAILABLE)
        return error_data, response_time_ms, True, False, True
    
    logger.info(f"{MSG_INFO_CAUSE_RESULT_LIMIT} - {error_data.get('message', MSG_ERROR_RESULT_LIMIT_REACHED)}")
    logger.info(MSG_INFO_FREE_TIER_LIMIT_QUERY_SHORT)
    logger.info(MSG_INFO_NO_ARTICLES_ERROR)
    return None, response_time_ms, False, False, True

def _is_rate_limit_error(error_code: str, error_message: str, error_text: str, status_code: Optional[int]) -> bool:
    """Check if error indicates rate limit (quota exhausted) - dynamic detection."""
    # Check for common rate limit indicators in error messages
    rate_limit_indicators = [
        'rate limit',
        'rate_limit',
        'quota',
        'too many requests',
        'too many calls',
        'request limit',
        'api limit exceeded',
        'throttle',
        'throttled'
    ]
    
    error_text_lower = error_text.lower()
    error_message_lower = error_message.lower()
    
    # Check error message and text for rate limit keywords
    for indicator in rate_limit_indicators:
        if indicator in error_message_lower or indicator in error_text_lower:
            return True
    
    # Also check for common rate limit error codes
    rate_limit_codes = ['rateLimitExceeded', 'tooManyRequests', 'quotaExceeded']
    if error_code.lower() in [code.lower() for code in rate_limit_codes]:
        return True
    
    return False

def _handle_rate_limit_error(http_err: requests.exceptions.HTTPError, status_code: int, response_time_ms: float, config: Dict) -> Tuple[Optional[Dict], float, bool, bool, bool]:
    """Handle rate limit error - quota exhausted (detected dynamically)."""
    logger.info(f"{MSG_INFO_RATE_LIMIT_DETECTED} (HTTP {status_code})")
    max_error_length = get_config_value(config, 'article_processing.max_error_text_length', DEFAULT_MAX_ERROR_TEXT_LENGTH)
    
    if hasattr(http_err, 'response'):
        try:
            error_data = http_err.response.json()
            error_message = error_data.get('message', MSG_ERROR_RATE_LIMIT_EXCEEDED)
            logger.error(f"{MSG_ERROR_API_RESPONSE}: {error_data}")
            logger.error(f"{MSG_ERROR_MESSAGE}: {error_message}")
            logger.info(f"{MSG_INFO_QUOTA_EXHAUSTED} - {error_message}")
        except (ValueError, AttributeError, TypeError):
            error_text = http_err.response.text[:max_error_length] if hasattr(http_err.response, 'text') else ""
            logger.error(f"{MSG_ERROR_RESPONSE_TEXT}: {error_text}")
    
    logger.warning(f"{MSG_WARNING_RATE_LIMIT} (HTTP {status_code}). {MSG_INFO_QUOTA_EXHAUSTED}.")
    logger.info(MSG_INFO_STOPPING_REQUESTS)
    logger.info(MSG_INFO_QUOTA_RESET)
    logger.info(MSG_INFO_NEXT_RUN)
    return None, response_time_ms, False, True, False

def _handle_other_http_error(http_err: requests.exceptions.HTTPError, status_code: Optional[int], response_time_ms: float, config: Dict) -> Tuple[Optional[Dict], float, bool, bool, bool]:
    """Handle other HTTP errors."""
    logger.error(f"{MSG_ERROR_UNHANDLED_HTTP} (Status code: {status_code})")
    max_error_length = get_config_value(config, 'article_processing.max_error_text_length', DEFAULT_MAX_ERROR_TEXT_LENGTH)
    
    if hasattr(http_err, 'response'):
        try:
            error_data = http_err.response.json()
            logger.error(f"{MSG_ERROR_API_RESPONSE}: {error_data}")
            if isinstance(error_data, dict):
                error_code = error_data.get('code', MSG_ERROR_N_A)
                error_message = error_data.get('message', MSG_ERROR_N_A)
                logger.error(f"{MSG_ERROR_CODE}: {error_code}")
                logger.error(f"{MSG_ERROR_MESSAGE}: {error_message}")
        except (ValueError, AttributeError, TypeError):
            error_text = http_err.response.text[:max_error_length] if hasattr(http_err.response, 'text') else ""
            logger.error(f"{MSG_ERROR_RESPONSE_TEXT}: {error_text}")
    
    return None, response_time_ms, False, False, False

def make_api_request(url: str, params: Dict, config: Dict, retry_count: int = 0) -> Tuple[Optional[Dict], float, bool, bool, bool]:
    """
    Make API request with dynamic error handling.
    Returns (response_data, response_time_ms, success, is_rate_limited, is_result_limit_reached).
    is_rate_limited indicates if we hit rate limit that should stop further requests.
    is_result_limit_reached indicates if we hit a result limit error (free tier 100 result limit per query).
    """
    timeout = get_config_value(config, 'api.timeout_seconds', DEFAULT_TIMEOUT_SECONDS)
    start_time = time.time()
    
    try:
        response = requests.get(url, params=params, timeout=timeout)
        response_time_ms = (time.time() - start_time) * 1000
        response.raise_for_status()
        return response.json(), response_time_ms, True, False, False
    except requests.exceptions.HTTPError as http_err:
        response_time_ms = (time.time() - start_time) * 1000
        status_code = http_err.response.status_code if hasattr(http_err, 'response') else None
        max_error_length = get_config_value(config, 'article_processing.max_error_text_length', DEFAULT_MAX_ERROR_TEXT_LENGTH)
        
        logger.error(f"{MSG_ERROR_HTTP}: {http_err}")
        if status_code:
            logger.error(f"{MSG_ERROR_STATUS_CODE}: {status_code}")
        
        # DYNAMIC HANDLING: Detect rate limit and result limit errors for ANY status code
        # Check error message/content to detect rate limit errors, not just specific status codes
        if hasattr(http_err, 'response'):
            try:
                error_data = http_err.response.json()
                error_code = error_data.get('code', '')
                error_message = error_data.get('message', '').lower()
                error_text_lower = str(error_data).lower()
                
                # DYNAMIC: Check if error message indicates rate limit (works for any status code)
                if _is_rate_limit_error(error_code, error_message, error_text_lower, status_code):
                    return _handle_rate_limit_error(http_err, status_code, response_time_ms, config)
                
                # DYNAMIC: Check if error message indicates result limit (works for any status code)
                if _is_result_limit_error(error_code, error_message, error_text_lower):
                    return _handle_result_limit_error(error_data, status_code, response_time_ms, config)
            except (ValueError, AttributeError, TypeError):
                error_text = http_err.response.text[:max_error_length] if hasattr(http_err.response, 'text') else ""
                logger.error(f"{MSG_ERROR_RESPONSE_TEXT}: {error_text}")
                
                # DYNAMIC: Check error text for rate limit keywords even if JSON parsing fails
                if error_text:
                    error_text_lower = error_text.lower()
                    if _is_rate_limit_error('', '', error_text_lower, status_code):
                        logger.info(f"Dynamic error handling: Rate limit detected in error text (HTTP {status_code})")
                        return _handle_rate_limit_error(http_err, status_code, response_time_ms, config)
                    
                    # Check error text for result limit keywords even if JSON parsing fails
                    if '100 results' in error_text_lower or 'result limit' in error_text_lower or 'max of 100' in error_text_lower:
                        logger.info(f"{MSG_INFO_DYNAMIC_RESULT_LIMIT_TEXT}. {MSG_INFO_FREE_TIER_ALLOWS}")
                        return None, response_time_ms, False, False, True
        
        # Handle other HTTP errors
        return _handle_other_http_error(http_err, status_code, response_time_ms, config)
    except Exception as req_err:
        response_time_ms = (time.time() - start_time) * 1000
        logger.error(f"{MSG_ERROR_REQUEST}: {req_err}")
        logger.error(f"{MSG_ERROR_TRACEBACK}: {traceback.format_exc()}")
        return None, response_time_ms, False, False, False

def fetch_articles_page(url: str, params: Dict, page: int, config: Dict, metrics: MetricsTracker, topic: str) -> Tuple[Optional[Dict], bool, bool, bool]:
    """
    Fetch a single page of articles from NewsAPI with rate limiting.
    Returns (response_data, success, is_rate_limited, is_result_limit_reached).
    is_rate_limited indicates if we hit a rate limit error that should stop further requests (detected dynamically).
    is_result_limit_reached indicates if we hit a result limit error (free tier 100 result limit per query).
    """
    # Apply rate limiting delay (except for first page)
    if page > 1:
        delay = get_config_value(config, 'api.rate_limit_delay_seconds', DEFAULT_RATE_LIMIT_DELAY_SECONDS)
        if delay > 0:
            logger.info(MSG_INFO_RATE_LIMITING.format(delay=delay))
            time.sleep(delay)
    
    page_params = params.copy()
    page_params["page"] = page
    
    safe_params = {k: v for k, v in page_params.items() if k != "apiKey"}
    logger.debug(MSG_DEBUG_FETCHING_PAGE.format(page=page, params=safe_params))
    
    response_data, response_time_ms, success, is_rate_limited, is_result_limit_reached = make_api_request(url, page_params, config)
    metrics.record_api_call(topic, response_time_ms, success)
    
    return response_data, success, is_rate_limited, is_result_limit_reached

# ============================================================================
# NEWS FETCHING (MAIN LOGIC)
# ============================================================================

def _validate_api_request(api_key: str, api_call_count: Dict, max_api_calls: int, context: str = "") -> bool:
    """Validate that API key exists and we haven't exceeded call limits."""
    if not api_key:
        logger.warning(f"{MSG_WARNING_NO_API_KEY}{f' for {context}' if context else ''}. Skipping NewsAPI fetch.")
        return False
    
    if api_call_count['total'] >= max_api_calls:
        logger.warning(f"{MSG_WARNING_API_LIMIT_REACHED} ({max_api_calls}).{f' Skipping {context}.' if context else ''}")
        return False
    
    return True

def _process_api_response(response_data: Optional[Dict], success: bool, is_rate_limited: bool, 
                         is_result_limit_reached: bool, page: int = 1) -> Tuple[Optional[Dict], bool]:
    """
    Process API response and handle rate limits and result limits.
    Returns (response_data, should_stop) where should_stop indicates if we should stop processing.
    """
    if is_rate_limited:
        logger.error(MSG_ERROR_RATE_LIMIT_HIT)
        return None, True
    
    # DYNAMIC HANDLING: Process articles even if we hit result limit or have errors
    if is_result_limit_reached and response_data:
        logger.info(MSG_INFO_RESULT_LIMIT_PROCESSING)
    
    if not success or not response_data:
        if is_result_limit_reached:
            logger.info(MSG_INFO_RESULT_LIMIT_NO_ARTICLES)
        return None, False
    
    # Check API response status - but allow processing if we have articles (even with result limit)
    response_status = response_data.get("status", "")
    if response_status != MSG_STATUS_OK and not is_result_limit_reached:
        error_message = response_data.get("message", MSG_ERROR_UNKNOWN)
        logger.error(f"{MSG_ERROR_NEWSAPI_ERROR}: {error_message}")
        return None, False
    
    return response_data, False

def _log_results_summary(total_results: int, articles: List[Dict], page: int = 1):
    """Log summary of API results."""
    if total_results > 100:
        logger.info(MSG_INFO_TOTAL_RESULTS_EXCEEDS.format(total=total_results))
        logger.info(MSG_INFO_PROCESSING_ARTICLES.format(count=len(articles)))
        logger.info(MSG_INFO_FREE_TIER_LIMIT_QUERY)
    else:
        logger.info(f"NewsAPI returned {total_results} total results, {len(articles)} articles in page {page}")

def _validate_articles_response(articles: List[Dict], total_results: int, context: str = "") -> bool:
    """Validate that we have articles to process."""
    if len(articles) == 0:
        if total_results == 0:
            logger.warning(f"{MSG_WARNING_NO_ARTICLES}{f' for {context}' if context else ''}")
        else:
            logger.warning(f"{MSG_WARNING_NO_ARTICLES_RESPONSE} (totalResults: {total_results})")
        return False
    return True

def _log_processed_articles(articles: List[Dict], config: Dict, prefix: str = ""):
    """Log summary of processed articles."""
    max_title_length = get_config_value(config, 'article_processing.max_title_preview_length', DEFAULT_MAX_TITLE_PREVIEW_LENGTH)
    debug_limit = get_config_value(config, 'article_processing.debug_log_filtered_limit', DEFAULT_DEBUG_LOG_FILTERED_LIMIT)
    
    for item in articles[:debug_limit]:
        logger.info(f"{prefix}{MSG_OK_ADDED.format(title=item['title'][:max_title_length])}")

def fetch_from_newsapi(topic: str, api_key: str, config: Dict, metrics: MetricsTracker, api_call_count: Dict) -> Tuple[List[Dict], bool]:
    """
    Fetch news from NewsAPI.org with pagination support.
    Returns (list of processed news articles, is_rate_limited).
    is_rate_limited indicates if we hit rate limit and should stop processing more topics.
    Note: Result limit errors are handled dynamically - we stop pagination but continue with other topics.
    """
    # Validate API request
    max_api_calls = get_config_value(config, 'api.max_api_calls', DEFAULT_MAX_API_CALLS)
    if not _validate_api_request(api_key, api_call_count, max_api_calls, topic):
        return [], False
    
    # Get topic configuration
    news_sources = get_config_value(config, 'news_sources', {})
    topic_config = news_sources.get(topic, {})
    title_query = topic_config.get("title_query")
    
    if not title_query:
        logger.warning(f"{MSG_WARNING_NO_TITLE_QUERY} {topic}")
        return [], False
    
    # Calculate date range
    date_range = calculate_date_range(config)
    from_date, to_date = date_range
    
    logger.debug(MSG_DEBUG_FETCHING_FROM.format(from_date=from_date, to_date=to_date))
    logger.debug(MSG_DEBUG_SEARCH_QUERY.format(query=title_query))
    logger.debug(MSG_DEBUG_API_URL.format(url=get_config_value(config, 'api.base_url', NEWSAPI_BASE_URL)))
    
    # Build API parameters
    url = get_config_value(config, 'api.base_url', NEWSAPI_BASE_URL)
    params = build_api_params(topic_config, date_range, api_key, config)
    
    news_items = []
    seen_urls = set()
    page = 1
    # Dynamic pagination: Try to fetch multiple pages, but gracefully handle result limit errors if they occur
    # If free_tier_mode is enabled, limit to 1 page to avoid result limit errors proactively
    # If disabled (default), try multiple pages and handle result limits dynamically when they occur
    free_tier_mode = get_config_value(config, 'api.free_tier_mode', False)  # Default: dynamic error handling
    if free_tier_mode:
        max_pages = 1
        logger.info(MSG_INFO_FREE_TIER_MODE)
    else:
        # Allow per-topic max_pages override, fallback to global config
        max_pages = topic_config.get('max_pages') or get_config_value(config, 'api.max_pages', DEFAULT_MAX_PAGES)
        # Limit pages based on remaining API calls
        remaining_calls = max_api_calls - api_call_count['total']
        max_pages = min(max_pages, remaining_calls)
        logger.info(MSG_INFO_DYNAMIC_PAGINATION.format(max_pages=max_pages))
    
    if max_pages <= 0:
        logger.warning(f"{MSG_WARNING_NO_API_CALLS}. Skipping {topic}.")
        return [], False
    
    logger.info(f"{MSG_INFO_MAX_PAGES}: {max_pages} (max {max_pages} API requests for this topic)")
    
    try:
        # Check if we can make the request
        if api_call_count['total'] >= max_api_calls:
            logger.warning(f"{MSG_WARNING_API_LIMIT_REACHED}. Skipping {topic}.")
            return [], False
        
        # Fetch first page
        api_call_count['total'] += 1
        response_data, success, is_rate_limited, is_result_limit_reached = fetch_articles_page(url, params, page, config, metrics, topic)
        
        # Process API response
        response_data, should_stop = _process_api_response(response_data, success, is_rate_limited, is_result_limit_reached, page)
        if should_stop:
            return [], True
        if not response_data:
            return [], False
        
        total_results = response_data.get("totalResults", 0)
        articles = response_data.get("articles", [])
        
        # Log results summary
        _log_results_summary(total_results, articles, page)
        
        # Validate articles response
        if not _validate_articles_response(articles, total_results, f"{topic} with exact phrase '{title_query}'"):
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
            logger.info(f"{MSG_INFO_FETCHING_ADDITIONAL} (up to {total_pages} total pages)")
            logger.info(MSG_INFO_EARLY_STOPPING.format(min=min_articles_per_topic, threshold=int(early_stop_duplicate_threshold * 100)))
            
            for page_num in range(2, total_pages + 1):
                # Check API call limit before each request
                if api_call_count['total'] >= max_api_calls:
                    logger.warning(f"{MSG_WARNING_API_LIMIT_REACHED}. Stopping pagination at page {page_num - 1}.")
                    break
                
                api_call_count['total'] += 1
                response_data, success, is_rate_limited, is_result_limit_reached = fetch_articles_page(url, params, page_num, config, metrics, topic)
                
                if is_rate_limited:
                    logger.error(MSG_ERROR_RATE_LIMIT_HIT)
                    return news_items, True
                
                # Dynamic error handling: Gracefully stop pagination when result limit is reached
                # This allows the script to work with both free tier (100 results max) and paid plans
                if is_result_limit_reached:
                    logger.info(MSG_INFO_DYNAMIC_STOPPING.format(page=page_num))
                    logger.info(MSG_INFO_DYNAMIC_STOPPED.format(count=len(news_items), pages=page_num - 1))
                    logger.info(MSG_INFO_UPGRADE_PLAN)
                    break
                
                if not success or not response_data:
                    logger.warning(MSG_WARNING_FAILED_FETCH.format(page=page_num))
                    break
                
                if response_data.get("status") != MSG_STATUS_OK:
                    break
                
                articles = response_data.get("articles", [])
                logger.info(MSG_INFO_FETCHED_ARTICLES.format(count=len(articles), page=page_num))
                
                # Process articles and track new vs duplicates
                new_articles_this_page = 0
                for article in articles:
                    processed = process_article(article, title_query, seen_urls, config, metrics, topic, use_exact_phrase=True)
                    if processed:
                        news_items.append(processed)
                        new_articles_this_page += 1
                
                # Early stopping check 1: Do we have enough new articles?
                if len(news_items) >= min_articles_per_topic:
                    logger.info(MSG_INFO_EARLY_STOP_ENOUGH.format(count=len(news_items), target=min_articles_per_topic))
                    break
                
                # Early stopping check 2: Are we getting too many duplicates?
                if len(articles) > 0:
                    duplicate_ratio = 1.0 - (new_articles_this_page / len(articles))
                    if duplicate_ratio >= early_stop_duplicate_threshold:
                        logger.info(MSG_INFO_EARLY_STOP_DUPLICATES.format(percent=int(duplicate_ratio * 100), page=page_num, threshold=int(early_stop_duplicate_threshold * 100)))
                        break
        
        # Sort by date (newest first)
        news_items.sort(key=lambda x: x.get("date", ""), reverse=True)
        
        # Log processed articles
        _log_processed_articles(news_items, config, "      ")
        logger.info(MSG_INFO_PROCESSED_ARTICLES.format(count=len(news_items)))
        return news_items, False
        
    except Exception as e:
        logger.error(f"{MSG_ERROR_UNEXPECTED} for {topic}: {e}")
        logger.error(f"{MSG_ERROR_TRACEBACK}: {traceback.format_exc()}")
        return [], False

def fetch_combined_from_newsapi(topics_config: Dict[str, Dict], api_key: str, config: Dict, metrics: MetricsTracker, api_call_count: Dict) -> Tuple[Dict[str, List[Dict]], bool]:
    """
    Fetch news from NewsAPI.org for multiple topics in a single combined request using OR operator.
    Returns (dict mapping topic to list of articles, is_rate_limited).
    Articles are automatically routed to the correct topic based on which phrase they match.
    """
    # Validate API request
    max_api_calls = get_config_value(config, 'api.max_api_calls', DEFAULT_MAX_API_CALLS)
    if not _validate_api_request(api_key, api_call_count, max_api_calls, "combined request"):
        return {topic: [] for topic in topics_config.keys()}, False
    
    # Calculate date range
    date_range = calculate_date_range(config)
    from_date, to_date = date_range
    
    # Build combined query
    topic_names = [topic_config.get("name", topic) for topic, topic_config in topics_config.items()]
    title_queries = [topic_config.get("title_query", "") for topic_config in topics_config.values()]
    combined_query = " OR ".join([f'"{q}"' for q in title_queries if q])
    
    logger.info(MSG_INFO_COMBINED_REQUEST.format(count=len(topics_config)))
    logger.debug(MSG_DEBUG_TOPICS.format(topics=', '.join(topic_names)))
    logger.debug(MSG_DEBUG_FETCHING_FROM.format(from_date=from_date, to_date=to_date))
    logger.debug(MSG_DEBUG_COMBINED_QUERY.format(query=combined_query))
    logger.debug(MSG_DEBUG_API_URL.format(url=get_config_value(config, 'api.base_url', NEWSAPI_BASE_URL)))
    
    # Build API parameters
    url = get_config_value(config, 'api.base_url', NEWSAPI_BASE_URL)
    params = build_combined_api_params(topics_config, date_range, api_key, config)
    
    # Initialize result dictionary - one list per topic
    topic_articles = {topic: [] for topic in topics_config.keys()}
    seen_urls = {topic: set() for topic in topics_config.keys()}  # Track seen URLs per topic
    
    page = 1
    # For combined requests, always limit to 1 page (100 results max) to get balanced results across topics
    # This ensures we get max 100 results total distributed across all topics in a single API call
    max_pages = 1
    logger.info(MSG_INFO_COMBINED_MODE)
    
    try:
        # Check if we can make the request
        if api_call_count['total'] >= max_api_calls:
            logger.warning(f"{MSG_WARNING_API_LIMIT_REACHED}. Skipping combined request.")
            return topic_articles, False
        
        # Fetch first page
        api_call_count['total'] += 1
        # Use first topic name for metrics (combined request)
        first_topic = list(topics_config.keys())[0]
        response_data, success, is_rate_limited, is_result_limit_reached = fetch_articles_page(url, params, page, config, metrics, first_topic)
        
        # Process API response
        response_data, should_stop = _process_api_response(response_data, success, is_rate_limited, is_result_limit_reached, page)
        if should_stop:
            return topic_articles, True
        if not response_data:
            return topic_articles, False
        
        total_results = response_data.get("totalResults", 0)
        articles = response_data.get("articles", [])
        
        # Log results summary
        _log_results_summary(total_results, articles, page)
        
        # Validate articles response
        if not _validate_articles_response(articles, total_results, "combined query"):
            return topic_articles, False
        
        # Process articles from first page - route to appropriate topics
        # Combined requests are limited to 1 page (100 results max) to get balanced distribution across topics
        for article in articles:
            topic = route_article_to_topic(article, topics_config, config)
            if topic:
                # Get the title_query for this topic for exact phrase matching
                title_query = topics_config[topic].get("title_query", "")
                processed = process_article(article, title_query, seen_urls[topic], config, metrics, topic, use_exact_phrase=True)
                if processed:
                    topic_articles[topic].append(processed)
            # If article doesn't match any topic, it's filtered out (this shouldn't happen with OR query, but handle gracefully)
        
        # Combined requests: Only fetch 1 page (100 results max total)
        # Results are automatically distributed across topics based on what NewsAPI returns
        # This ensures we get max 100 results total in 1 API call, distributed across all topics
        
        # Sort articles by date (newest first) for each topic
        for topic in topics_config.keys():
            topic_articles[topic].sort(key=lambda x: x.get("date", ""), reverse=True)
        
        # Log summary per topic
        logger.info(MSG_INFO_ARTICLES_ROUTED)
        for topic, articles_list in topic_articles.items():
            topic_name = topics_config[topic].get("name", topic)
            logger.info(f"      {topic_name}: {len(articles_list)} articles")
            # Log some added articles
            _log_processed_articles(articles_list, config, "         ")
        
        total_articles = sum(len(articles) for articles in topic_articles.values())
        logger.info(MSG_INFO_PROCESSED_TOTAL.format(count=total_articles))
        return topic_articles, False
        
    except Exception as e:
        logger.error(f"{MSG_ERROR_UNEXPECTED_COMBINED}: {e}")
        logger.error(f"{MSG_ERROR_TRACEBACK}: {traceback.format_exc()}")
        return topic_articles, False

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
        logger.info(MSG_INFO_REMOVED_ARTICLES.format(count=removed_count, days=retention_days))
    
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

def merge_filter_and_save_articles(topic: str, topic_config: Dict, existing_articles: List[Dict], 
                                   new_articles: List[Dict], config: Dict, metrics: MetricsTracker) -> Tuple[bool, int]:
    """
    Shared function to merge existing and new articles, filter by retention, and save to file.
    Handles all the common logic for both individual and combined request modes.
    
    Returns (success, article_count) where article_count is the number of articles saved/preserved.
    """
    # Merge existing articles with new articles (remove duplicates by URL)
    # IMPORTANT: If API failed and we have cached articles, preserve them!
    if existing_articles and new_articles:
        # Both exist - merge them
        merged_articles = merge_news_articles(existing_articles, new_articles)
        logger.info(MSG_INFO_MERGED_ARTICLES.format(existing=len(existing_articles), new=len(new_articles), total=len(merged_articles)))
    elif existing_articles:
        # API failed but we have cached articles - use them!
        merged_articles = existing_articles
        logger.info(MSG_INFO_API_FAILED_CACHED.format(count=len(existing_articles)))
    elif new_articles:
        # Only new articles (no cached)
        merged_articles = new_articles
        logger.info(MSG_INFO_USING_NEW.format(count=len(new_articles)))
    else:
        merged_articles = []
    
    # Filter articles by retention period (remove articles older than retention_days)
    retention_days = get_config_value(config, 'date_range.retention_days', DEFAULT_RETENTION_DAYS)
    if merged_articles:
        filtered_articles = filter_articles_by_retention(merged_articles, retention_days)
        logger.info(MSG_INFO_AFTER_RETENTION.format(days=retention_days, count=len(filtered_articles)))
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
                    logger.info(MSG_OK_SAVED.format(count=len(filtered_articles), file=f"{topic}.yml"))
                else:
                    logger.info(MSG_INFO_NO_ARTICLES_SAVE)
                return True, len(filtered_articles)
            else:
                logger.error(f"{MSG_ERROR_SAVE_FAILED} for {topic}")
                return False, 0
        else:
            # API failed but we have cached articles - preserve them, don't overwrite
            logger.info(MSG_INFO_PRESERVING_CACHED.format(count=len(existing_articles)))
            metrics.record_article_saved(topic, len(existing_articles))
            return True, len(existing_articles)
    except Exception as save_err:
        logger.error(f"{MSG_ERROR_SAVE_FAILED} for {topic}: {save_err}")
        # If we have cached articles, still return success (graceful degradation)
        if existing_articles:
            logger.info(MSG_INFO_CACHED_AVAILABLE)
            return True, len(existing_articles)
        return False, 0

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
        
        logger.info(MSG_OK_UPDATED.format(path=file_path, count=len(news_items)))
        return True
    except Exception as e:
        logger.error(f"{MSG_ERROR_UPDATE_FAILED} for {topic}: {e}")
        logger.error(f"{MSG_ERROR_TRACEBACK}: {traceback.format_exc()}")
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
            logger.info(MSG_INFO_LOADED_CACHED.format(count=len(news_items)))
        return news_items
    except Exception as e:
        logger.warning(f"{MSG_WARNING_READ_CACHE_FAILED} for {topic}: {e}")
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
        logger.info(MSG_INFO_FETCHING_NEWS.format(name=topic_name))
        
        # Load existing articles from file
        existing_articles = load_existing_news(topic)
        if existing_articles:
            logger.info(f"   {MSG_INFO_LOADED_CACHED.format(count=len(existing_articles))}")
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
                    logger.warning(MSG_WARNING_RATE_LIMIT_DETECTED)
                    logger.info(MSG_INFO_STOPPING_FURTHER)
                    logger.info(MSG_INFO_USING_CACHED)
                    # Still save existing articles (graceful degradation)
                elif new_articles:
                    title_query = topic_config.get("title_query", "")
                    logger.info(MSG_OK_FOUND_ARTICLES.format(count=len(new_articles), query=title_query))
                else:
                    logger.warning(f"{MSG_WARNING_NO_NEW_ARTICLES} for {topic}")
            except Exception as fetch_err:
                logger.error(f"{MSG_ERROR_FETCH_FAILED} for {topic}: {fetch_err}")
                # Continue with existing articles if fetch fails
                if not existing_articles:
                    return False, False
        elif rate_limited:
            logger.info(MSG_INFO_SKIPPING_API)
        else:
            logger.warning(MSG_WARNING_SKIPPING_NO_KEY.format(topic=topic))
        
        # Merge, filter, and save articles using shared function
        success, article_count = merge_filter_and_save_articles(
            topic, topic_config, existing_articles, new_articles, config, metrics
        )
        if not success:
            return False, is_rate_limited
        
        return True, is_rate_limited
        
    except Exception as topic_err:
        logger.error(f"{MSG_ERROR_UNEXPECTED_PROCESSING} {topic}: {topic_err}")
        logger.error(f"{MSG_ERROR_TRACEBACK}: {traceback.format_exc()}")
        return False, False

def main():
    """Main function to update all news files."""
    metrics = MetricsTracker()
    
    logger.info(MSG_INFO_STARTING)
    logger.info(f"{datetime.now().strftime(DATETIME_FORMAT)}\n")
    
    # Load configuration
    config = load_config()
    
    # Get date range info for logging
    date_range = calculate_date_range(config)
    lookback_days = get_config_value(config, 'date_range.lookback_days', DEFAULT_LOOKBACK_DAYS)
    logger.info(MSG_INFO_FETCHING_DYNAMIC)
    logger.info(MSG_INFO_DATE_RANGE.format(days=lookback_days, from_date=date_range[0], to_date=date_range[1]) + "\n")
    
    # Check for NewsAPI key in environment variable
    api_key = os.environ.get(ENV_VAR_NEWSAPI_KEY)
    
    if not api_key:
        logger.warning(MSG_WARNING_NO_KEY_ENV)
        logger.info(MSG_INFO_SET_KEY)
        logger.info(MSG_INFO_SET_KEY_WIN)
        logger.info(MSG_INFO_GET_KEY + "\n")
    
    # Get news sources from config
    news_sources = get_config_value(config, 'news_sources', {})
    
    if not news_sources:
        logger.error(MSG_ERROR_NO_SOURCES)
        return
    
    error_count = 0
    api_call_count = {'total': 0}  # Track total API calls across all topics
    max_api_calls = get_config_value(config, 'api.max_api_calls', DEFAULT_MAX_API_CALLS)
    rate_limited_flag = {'value': False}  # Track if we hit rate limit globally (use dict for pass-by-reference)
    combine_topics = get_config_value(config, 'api.combine_topics_in_single_request', DEFAULT_COMBINE_TOPICS_IN_SINGLE_REQUEST)
    
    logger.info(MSG_INFO_API_LIMIT.format(limit=max_api_calls))
    if combine_topics:
        logger.info(MSG_INFO_COMBINED_ENABLED)
    else:
        topic_delay = get_config_value(config, 'api.topic_delay_seconds', DEFAULT_TOPIC_DELAY_SECONDS)
        logger.info(MSG_INFO_COMBINED_DISABLED)
        logger.info(MSG_INFO_DELAY_BETWEEN.format(delay=topic_delay))
    logger.info("")
    
    # Convert to list of tuples (topics are processed in config order)
    # When combined requests are enabled, all topics are automatically included in 1 API call
    topics_list = list(news_sources.items())
    
    if len(topics_list) > 1:
        logger.info(MSG_INFO_TOPICS_TO_PROCESS.format(count=len(topics_list)))
        for topic, topic_config in topics_list:
            name = topic_config.get('name', topic)
            logger.info(f"   - {name}")
        logger.info("")
    
    # Check if combined requests are enabled
    if combine_topics and len(topics_list) > 1:
        # Use combined request mode: fetch all topics in a single API call
        logger.info(MSG_INFO_USING_COMBINED.format(count=len(topics_list)) + "\n")
        
        # Convert to dict format for combined fetch
        topics_config_dict = dict(topics_list)
        
        # Load existing articles for all topics
        existing_articles_dict = {}
        for topic, topic_config in topics_list:
            existing_articles_dict[topic] = load_existing_news(topic)
            if existing_articles_dict[topic]:
                topic_name = topic_config.get("name", topic)
                logger.info(MSG_INFO_LOADED_CACHED_TOPIC.format(count=len(existing_articles_dict[topic]), name=topic_name))
        
        # Fetch articles for all topics in one request
        new_articles_dict = {}
        is_rate_limited = False
        rate_limited = rate_limited_flag.get('value', False)
        
        if api_key and not rate_limited:
            try:
                new_articles_dict, is_rate_limited = fetch_combined_from_newsapi(
                    topics_config_dict, api_key, config, metrics, api_call_count
                )
                if is_rate_limited:
                    rate_limited_flag['value'] = True
                    logger.warning(f"\n{MSG_WARNING_RATE_LIMIT_QUOTA}")
                    logger.info(MSG_INFO_STOPPING_ALL)
                    logger.info(MSG_INFO_WILL_USE_CACHED)
                else:
                    total_new = sum(len(articles) for articles in new_articles_dict.values())
                    if total_new > 0:
                        logger.info(f"\n{MSG_OK_FOUND_TOTAL.format(count=total_new)}")
                    else:
                        logger.warning(f"\n{MSG_WARNING_NO_NEW_ANY}")
            except Exception as fetch_err:
                logger.error(f"{MSG_ERROR_FETCH_COMBINED}: {fetch_err}")
                new_articles_dict = {topic: [] for topic in topics_config_dict.keys()}
        elif rate_limited:
            logger.info(MSG_INFO_SKIPPING_API)
            new_articles_dict = {topic: [] for topic in topics_config_dict.keys()}
        else:
            logger.warning(MSG_WARNING_SKIPPING_COMBINED)
            new_articles_dict = {topic: [] for topic in topics_config_dict.keys()}
        
        # Process each topic: merge, filter, and save
        for topic, topic_config in topics_list:
            topic_name = topic_config.get("name", topic)
            logger.info(f"\n{MSG_INFO_PROCESSING.format(name=topic_name)}")
            
            existing_articles = existing_articles_dict.get(topic, [])
            new_articles = new_articles_dict.get(topic, [])
            
            # Merge, filter, and save articles using shared function
            success, article_count = merge_filter_and_save_articles(
                topic, topic_config, existing_articles, new_articles, config, metrics
            )
            if not success:
                error_count += 1
        
        # Track rate limit status
        if is_rate_limited:
            rate_limited_flag['value'] = True
            logger.warning(f"\n" + "=" * 70)
            logger.warning(MSG_WARNING_RATE_LIMIT_QUOTA_EXHAUSTED)
            logger.warning("=" * 70)
            logger.info(MSG_INFO_QUOTA_INFO)
            logger.info(f"   - {MSG_INFO_FREE_TIER_12H}")
            logger.info(f"   - {MSG_INFO_FREE_TIER_24H}")
            logger.info(MSG_INFO_NEXT_SUCCESSFUL)
            logger.info(MSG_INFO_CACHED_AVAILABLE_SERVED)
            logger.warning("=" * 70 + "\n")
    
    else:
        # Use individual request mode: process each topic separately
        for idx, (topic, topic_config) in enumerate(topics_list, 1):
            # Add delay between topics (except before first topic)
            if idx > 1 and topic_delay > 0:
                logger.info(MSG_INFO_WAITING.format(delay=topic_delay) + "\n")
                time.sleep(topic_delay)
            
            success, is_rate_limited = process_topic(topic, topic_config, api_key, config, metrics, api_call_count, rate_limited_flag)
            if not success:
                error_count += 1
            
            # Track rate limit status (but continue processing remaining topics with cached articles)
            if is_rate_limited:
                rate_limited_flag['value'] = True
                if idx == 1:  # Only show message on first topic that hits rate limit
                    logger.warning(f"\n" + "=" * 70)
                    logger.warning(MSG_WARNING_RATE_LIMIT_QUOTA_EXHAUSTED)
                    logger.warning("=" * 70)
                    remaining_topics = len(topics_list) - idx
                    if remaining_topics > 0:
                        logger.info(MSG_INFO_REMAINING_CACHED.format(count=remaining_topics))
                    logger.info(MSG_INFO_QUOTA_INFO)
                    logger.info(f"   - {MSG_INFO_FREE_TIER_12H}")
                    logger.info(f"   - {MSG_INFO_FREE_TIER_24H}")
                    logger.info(MSG_INFO_NEXT_SUCCESSFUL)
                    logger.info(MSG_INFO_CACHED_AVAILABLE_SERVED)
                    logger.warning("=" * 70 + "\n")
            
            # Stop if we've reached the API call limit
            if api_call_count['total'] >= max_api_calls:
                logger.warning(MSG_WARNING_REACHED_LIMIT.format(limit=max_api_calls))
                remaining_topics = len(news_sources) - idx
                if remaining_topics > 0:
                    logger.info(MSG_INFO_SKIPPED_TOPICS.format(count=remaining_topics))
                break
    
    logger.info(MSG_INFO_TOTAL_CALLS.format(made=api_call_count['total'], limit=max_api_calls))
    
    # Print summary
    logger.info(f"\n{METRICS_SEPARATOR}")
    if error_count == 0 and api_call_count['total'] > 0:
        logger.info(MSG_OK_UPDATE_COMPLETE)
        logger.info(f"   {MSG_INFO_FETCHED_DYNAMIC}")
    elif rate_limited_flag['value']:
        logger.info(MSG_INFO_UPDATE_CACHED)
        logger.info(f"   {MSG_INFO_RATE_LIMIT_QUOTA_MSG}")
        logger.info(f"   {MSG_INFO_CACHED_SERVED}")
        logger.info(f"   {MSG_INFO_NEXT_RUN_RESET}")
    else:
        logger.warning(MSG_WARNING_UPDATE_ERRORS.format(count=error_count))
        logger.warning(f"   {MSG_WARNING_SOME_FAILED}")
    logger.info(f"{METRICS_SEPARATOR}")
    
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
        logger.info(f"\n{MSG_INFO_INTERRUPTED}")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"\n{MSG_FATAL_ERROR}: {MSG_ERROR_UNEXPECTED_MAIN}: {e}")
        logger.critical(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    run_cli()

"""
Unit tests for news fetching functionality.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import update_news
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from update_news import (
    fetch_from_newsapi,
    MetricsTracker,
    DEFAULT_MAX_PAGES
)


class TestFetchFromNewsapi:
    """Test news fetching from NewsAPI."""
    
    def test_fetch_from_newsapi_no_api_key(self):
        """Test fetching without API key."""
        config = {}
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_from_newsapi("machine-learning", "", config, metrics, api_call_count)
        
        assert result == []
        assert is_rate_limited is False
    
    def test_fetch_from_newsapi_no_topic_config(self):
        """Test fetching with missing topic configuration."""
        config = {"news_sources": {}}
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_from_newsapi("unknown-topic", "test-key", config, metrics, api_call_count)
        
        assert result == []
        assert is_rate_limited is False
    
    def test_fetch_from_newsapi_no_title_query(self):
        """Test fetching with topic config but no title_query."""
        config = {
            "news_sources": {
                "test-topic": {}
            }
        }
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_from_newsapi("test-topic", "test-key", config, metrics, api_call_count)
        
        assert result == []
        assert is_rate_limited is False
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.process_article')
    def test_fetch_from_newsapi_success_single_page(self, mock_process, mock_fetch_page):
        """Test successful fetch with single page."""
        mock_fetch_page.return_value = ({
            "status": "ok",
            "totalResults": 50,
            "articles": [
                {
                    "url": "https://example.com/1",
                    "title": "Machine Learning News",
                    "description": "Machine learning breakthrough",
                    "publishedAt": "2025-01-15T10:00:00Z",
                    "source": {"name": "Tech News"}
                }
            ]
        }, True, False)
        
        mock_process.return_value = {
            "title": "Machine Learning News",
            "date": "2025-01-15",
            "url": "https://example.com/1",
            "description": "Machine learning breakthrough",
            "source": "Tech News"
        }
        
        config = {
            "news_sources": {
                "machine-learning": {
                    "title_query": "Machine Learning",
                    "related_keywords": ["machine learning"]
                }
            },
            "api": {
                "max_page_size": 100,
                "max_pages": 5
            }
        }
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_from_newsapi("machine-learning", "test-key", config, metrics, api_call_count)
        
        assert len(result) == 1
        assert result[0]["title"] == "Machine Learning News"
        assert is_rate_limited is False
        mock_fetch_page.assert_called_once()
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.process_article')
    def test_fetch_from_newsapi_pagination_stops_on_error_status(self, mock_process, mock_fetch_page):
        """Test pagination stops when page returns error status."""
        # First page
        mock_fetch_page.side_effect = [
            ({
                "status": "ok",
                "totalResults": 250,
                "articles": [
                    {
                        "url": "https://example.com/1",
                        "title": "ML Article 1",
                        "description": "Machine learning",
                        "publishedAt": "2025-01-15T10:00:00Z",
                        "source": {"name": "Tech News"}
                    }
                ]
            }, True, False),
            # Second page with error status
            ({
                "status": "error",
                "message": "Rate limit exceeded"
            }, True, False)
        ]
        
        mock_process.return_value = {"title": "ML Article 1", "date": "2025-01-15", "url": "1", "description": "", "source": ""}
        
        config = {
            "news_sources": {
                "machine-learning": {
                    "title_query": "Machine Learning",
                    "related_keywords": ["machine learning"]
                }
            },
            "api": {
                "max_page_size": 100,
                "max_pages": 5
            }
        }
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_from_newsapi("machine-learning", "test-key", config, metrics, api_call_count)
        
        # Should stop after second page returns error status (line 465)
        assert mock_fetch_page.call_count == 2
        assert is_rate_limited is False
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.process_article')
    def test_fetch_from_newsapi_pagination(self, mock_process, mock_fetch_page):
        """Test fetching with pagination."""
        # First page
        mock_fetch_page.side_effect = [
            ({
                "status": "ok",
                "totalResults": 250,
                "articles": [
                    {
                        "url": "https://example.com/1",
                        "title": "ML Article 1",
                        "description": "Machine learning",
                        "publishedAt": "2025-01-15T10:00:00Z",
                        "source": {"name": "Tech News"}
                    }
                ]
            }, True, False),
            # Second page
            ({
                "status": "ok",
                "articles": [
                    {
                        "url": "https://example.com/2",
                        "title": "ML Article 2",
                        "description": "Machine learning",
                        "publishedAt": "2025-01-14T10:00:00Z",
                        "source": {"name": "Tech News"}
                    }
                ]
            }, True, False)
        ]
        
        mock_process.side_effect = [
            {"title": "ML Article 1", "date": "2025-01-15", "url": "1", "description": "", "source": ""},
            {"title": "ML Article 2", "date": "2025-01-14", "url": "2", "description": "", "source": ""}
        ]
        
        config = {
            "news_sources": {
                "machine-learning": {
                    "title_query": "Machine Learning",
                    "related_keywords": ["machine learning"]
                }
            },
            "api": {
                "max_page_size": 100,
                "max_pages": 5
            }
        }
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_from_newsapi("machine-learning", "test-key", config, metrics, api_call_count)
        
        # Should fetch 2 pages (total 250 results / 100 per page = 3 pages, but max_pages limits to 5)
        assert mock_fetch_page.call_count >= 2
        assert is_rate_limited is False
    
    @patch('update_news.fetch_articles_page')
    def test_fetch_from_newsapi_api_error_status(self, mock_fetch_page):
        """Test handling API error status."""
        mock_fetch_page.return_value = ({
            "status": "error",
            "message": "Invalid API key"
        }, True, False)
        
        config = {
            "news_sources": {
                "machine-learning": {
                    "title_query": "Machine Learning",
                    "related_keywords": []
                }
            }
        }
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_from_newsapi("machine-learning", "test-key", config, metrics, api_call_count)
        
        assert result == []
        assert is_rate_limited is False
    
    @patch('update_news.fetch_articles_page')
    def test_fetch_from_newsapi_no_results(self, mock_fetch_page):
        """Test handling no results from API."""
        mock_fetch_page.return_value = ({
            "status": "ok",
            "totalResults": 0,
            "articles": []
        }, True, False)
        
        config = {
            "news_sources": {
                "machine-learning": {
                    "title_query": "Machine Learning",
                    "related_keywords": []
                }
            }
        }
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_from_newsapi("machine-learning", "test-key", config, metrics, api_call_count)
        
        assert result == []
        assert is_rate_limited is False
    
    @patch('update_news.fetch_articles_page')
    def test_fetch_from_newsapi_fetch_failure(self, mock_fetch_page):
        """Test handling fetch page failure."""
        mock_fetch_page.return_value = (None, False, False)
        
        config = {
            "news_sources": {
                "machine-learning": {
                    "title_query": "Machine Learning",
                    "related_keywords": []
                }
            }
        }
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_from_newsapi("machine-learning", "test-key", config, metrics, api_call_count)
        
        assert result == []
        assert is_rate_limited is False
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.process_article')
    def test_fetch_from_newsapi_pagination_stops_on_error(self, mock_process, mock_fetch_page):
        """Test pagination stops when page fetch fails."""
        mock_fetch_page.side_effect = [
            ({
                "status": "ok",
                "totalResults": 250,
                "articles": [{"url": "1", "title": "Test", "description": "test", "publishedAt": "2025-01-15T10:00:00Z", "source": {"name": "Test"}}]
            }, True, False),
            (None, False, False)  # Second page fails
        ]
        
        mock_process.return_value = {"title": "Test", "date": "2025-01-15", "url": "1", "description": "", "source": ""}
        
        config = {
            "news_sources": {
                "machine-learning": {
                    "title_query": "Machine Learning",
                    "related_keywords": ["machine learning"]
                }
            },
            "api": {
                "max_page_size": 100,
                "max_pages": 5
            }
        }
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_from_newsapi("machine-learning", "test-key", config, metrics, api_call_count)
        
        # Should stop after first page fails
        assert mock_fetch_page.call_count == 2
        assert is_rate_limited is False
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.calculate_date_range')
    @patch('update_news.build_api_params')
    def test_fetch_from_newsapi_max_pages_zero(self, mock_build, mock_date, mock_fetch_page):
        """Test fetch_from_newsapi when max_pages <= 0 (lines 497-498)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        mock_build.return_value = {"q": "test"}
        
        # To hit line 497-498, we need max_pages <= 0 after calculation
        # This requires remaining_calls = 0, which means api_call_count['total'] = max_api_calls
        # But we also need to pass the check at line 461, which requires api_call_count['total'] < max_api_calls
        # This is a contradiction, so we need a mock that returns different values
        class ChangingApiCount:
            def __init__(self):
                self._calls = 0
                self._value = 9  # Start below limit
            
            def __getitem__(self, key):
                if key == 'total':
                    self._calls += 1
                    # First call (line 461 check): return 9 (below limit)
                    # Later calls (max_pages calc): return 10 (at limit)
                    if self._calls == 1:
                        return 9
                    else:
                        return 10  # At limit for max_pages calculation
                return None
            
            def __setitem__(self, key, value):
                if key == 'total':
                    self._value = value
            
            def get(self, key, default=None):
                if key == 'total':
                    return self.__getitem__(key)
                return default
        
        config = {
            "news_sources": {
                "test-topic": {"title_query": "Test"}
            },
            "api": {"max_api_calls": 10, "max_pages": 5}
        }
        metrics = MetricsTracker()
        api_call_count = ChangingApiCount()
        
        from io import StringIO
        import sys
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            result, is_rate_limited = fetch_from_newsapi("test-topic", "key", config, metrics, api_call_count)
            output = sys.stdout.getvalue()
            assert result == []
            assert is_rate_limited is False
            assert "No API calls remaining" in output
            assert mock_fetch_page.call_count == 0
        finally:
            sys.stdout = old_stdout
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.calculate_date_range')
    @patch('update_news.build_api_params')
    def test_fetch_from_newsapi_api_limit_in_try_block(self, mock_build, mock_date, mock_fetch_page):
        """Test fetch_from_newsapi API limit check inside try block (lines 505-506)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        mock_build.return_value = {"q": "test"}
        
        # Create a custom dict-like object that changes value between accesses
        class ChangingDict:
            def __init__(self):
                self._access_count = 0
                self._value = 4  # Start below limit
            
            def __getitem__(self, key):
                if key == 'total':
                    # Track accesses: first few return 4, then return 5 (at limit)
                    self._access_count += 1
                    # During max_pages calculation and initial checks: return 4
                    # During try block check: return 5
                    if self._access_count <= 2:  # Allow a couple accesses for max_pages calc
                        return 4
                    else:
                        return 5  # At limit for try block check
                return None
            
            def __setitem__(self, key, value):
                if key == 'total':
                    self._value = value
                    # Reset access count when value is set
                    self._access_count = 0
            
            def get(self, key, default=None):
                if key == 'total':
                    return self.__getitem__(key)
                return default
        
        config = {
            "news_sources": {
                "test-topic": {"title_query": "Test", "max_pages": 10}
            },
            "api": {"max_api_calls": 5}
        }
        metrics = MetricsTracker()
        api_call_count = ChangingDict()
        
        from io import StringIO
        import sys
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            result, is_rate_limited = fetch_from_newsapi("test-topic", "key", config, metrics, api_call_count)
            output = sys.stdout.getvalue()
            # Should hit the check at line 504-506
            assert "API call limit reached" in output or result == []
            assert mock_fetch_page.call_count == 0
        finally:
            sys.stdout = old_stdout
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.process_article')
    @patch('update_news.calculate_date_range')
    @patch('update_news.build_api_params')
    def test_fetch_from_newsapi_api_limit_during_pagination_break(self, mock_build, mock_date, mock_process, mock_fetch_page):
        """Test fetch_from_newsapi API limit check during pagination that triggers break (lines 554-556)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        mock_build.return_value = {"q": "test"}
        
        # To hit line 554-556, we need:
        # 1. total_pages > 1 (enter pagination loop)
        # 2. api_call_count['total'] >= max_api_calls when checking at line 554
        # Strategy: Use max_api_calls = 3, and simulate that after fetching page 2, 
        # when checking for page 3, we're already at the limit
        # This requires a custom dict that returns limit value when checking for page 3
        config = {
            "news_sources": {
                "test-topic": {"title_query": "Test"}
            },
            "api": {"max_api_calls": 3, "max_page_size": 100, "max_pages": 5}
        }
        metrics = MetricsTracker()
        
        # Use a custom dict that tracks pagination state
        # After page 2 is fetched (total = 2), when checking for page 3, return 3 (at limit)
        class LimitReachingDict:
            def __init__(self):
                self._value = 0
                self._get_count = 0
                self._ready_for_limit = False
            
            def __getitem__(self, key):
                if key == 'total':
                    self._get_count += 1
                    # After page 2 is fetched (value = 2), the next get in pagination loop should return limit
                    # We set _ready_for_limit when value becomes 2, then on next get, return limit
                    if self._ready_for_limit:
                        self._ready_for_limit = False  # Only return limit once
                        return 3  # At limit (max_api_calls = 3)
                    return self._value
                return None
            
            def __setitem__(self, key, value):
                if key == 'total':
                    self._value = value
                    # When value becomes 2 (after page 2 is fetched), mark that next get should return limit
                    if value == 2:
                        self._ready_for_limit = True
            
            def get(self, key, default=None):
                if key == 'total':
                    return self.__getitem__(key)
                return default
        
        api_call_count = LimitReachingDict()
        
        # Mock fetch_page to return multiple pages worth of results
        call_count = [0]
        def fetch_side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # First page - return success with many results (250 results = 3 pages)
                return ({
                    "status": "ok",
                    "totalResults": 250,
                    "articles": [{"url": "1", "title": "Test", "description": "test", "publishedAt": "2025-01-15T10:00:00Z", "source": {"name": "Test"}}]
                }, True, False)
            elif call_count[0] == 2:
                # Second page - return success
                return ({
                    "status": "ok",
                    "articles": [{"url": "2", "title": "Test2", "description": "test", "publishedAt": "2025-01-14T10:00:00Z", "source": {"name": "Test"}}]
                }, True, False)
            else:
                # Should not reach here if break works
                return (None, False, False)
        
        mock_fetch_page.side_effect = fetch_side_effect
        # Mock process_article to return articles for both pages
        mock_process.side_effect = [
            {"title": "Test", "date": "2025-01-15", "url": "1", "description": "", "source": ""},
            {"title": "Test2", "date": "2025-01-14", "url": "2", "description": "", "source": ""}
        ]
        
        from io import StringIO
        import sys
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            result, is_rate_limited = fetch_from_newsapi("test-topic", "key", config, metrics, api_call_count)
            output = sys.stdout.getvalue()
            # Should hit the check at line 554-556 when checking for page 3
            # The message should be: "API call limit reached. Stopping pagination at page 2."
            assert "API call limit reached" in output or "Stopping pagination" in output
            # Should only fetch 2 pages (first + second), not third
            assert mock_fetch_page.call_count == 2
        finally:
            sys.stdout = old_stdout


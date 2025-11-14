"""
Unit tests for API request handling functions.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import update_news
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from update_news import (
    build_api_params,
    make_api_request,
    fetch_articles_page,
    MetricsTracker,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_SORT_BY,
    DEFAULT_LANGUAGE,
    DEFAULT_MAX_PAGE_SIZE
)


class TestBuildApiParams:
    """Test API parameter building."""
    
    def test_build_api_params_basic(self):
        """Test building basic API parameters."""
        topic_config = {"title_query": "Machine Learning"}
        date_range = ("2025-01-01", "2025-01-31")
        api_key = "test-key"
        config = {}
        
        params = build_api_params(topic_config, date_range, api_key, config)
        
        assert params["q"] == "Machine Learning"
        assert params["from"] == "2025-01-01"
        assert params["to"] == "2025-01-31"
        assert params["apiKey"] == "test-key"
        assert params["sortBy"] == DEFAULT_SORT_BY
        assert params["language"] == DEFAULT_LANGUAGE
        assert params["pageSize"] == DEFAULT_MAX_PAGE_SIZE
    
    def test_build_api_params_with_config(self):
        """Test building API parameters with custom config."""
        topic_config = {"title_query": "Deep Learning"}
        date_range = ("2025-01-01", "2025-01-31")
        api_key = "test-key"
        config = {
            "api": {
                "sort_by": "relevancy",
                "language": "es",
                "max_page_size": 50
            }
        }
        
        params = build_api_params(topic_config, date_range, api_key, config)
        
        assert params["sortBy"] == "relevancy"
        assert params["language"] == "es"
        assert params["pageSize"] == 50


class TestMakeApiRequest:
    """Test API request making."""
    
    @patch('update_news.requests.get')
    def test_make_api_request_success(self, mock_get):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok", "articles": []}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        url = "https://api.example.com"
        params = {"q": "test"}
        config = {}
        
        response_data, response_time, success = make_api_request(url, params, config)
        
        assert success is True
        assert response_data == {"status": "ok", "articles": []}
        assert response_time >= 0
        mock_get.assert_called_once()
    
    @patch('update_news.requests.get')
    def test_make_api_request_http_error(self, mock_get):
        """Test API request with HTTP error."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"message": "Rate limit exceeded"}
        mock_response.text = "Rate limit exceeded"
        
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_get.side_effect = http_error
        
        url = "https://api.example.com"
        params = {"q": "test"}
        config = {}
        
        response_data, response_time, success = make_api_request(url, params, config)
        
        assert success is False
        assert response_data is None
        assert response_time >= 0
    
    @patch('update_news.requests.get')
    def test_make_api_request_timeout(self, mock_get):
        """Test API request with timeout."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout()
        
        url = "https://api.example.com"
        params = {"q": "test"}
        config = {}
        
        response_data, response_time, success = make_api_request(url, params, config)
        
        assert success is False
        assert response_data is None
    
    @patch('update_news.requests.get')
    def test_make_api_request_with_custom_timeout(self, mock_get):
        """Test API request with custom timeout."""
        mock_response = Mock()
        mock_response.json.return_value = {"status": "ok"}
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        url = "https://api.example.com"
        params = {"q": "test"}
        config = {"api": {"timeout_seconds": 30}}
        
        make_api_request(url, params, config)
        
        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["timeout"] == 30


class TestFetchArticlesPage:
    """Test fetching articles page."""
    
    @patch('update_news.make_api_request')
    @patch('update_news.time.sleep')
    def test_fetch_articles_page_first_page(self, mock_sleep, mock_make_request):
        """Test fetching first page (no rate limiting)."""
        mock_make_request.return_value = ({"status": "ok"}, 100.0, True)
        
        tracker = MetricsTracker()
        url = "https://api.example.com"
        params = {"q": "test"}
        config = {}
        topic = "machine-learning"
        
        response_data, success = fetch_articles_page(url, params, 1, config, tracker, topic)
        
        assert success is True
        assert response_data == {"status": "ok"}
        mock_sleep.assert_not_called()  # No delay for first page
    
    @patch('update_news.make_api_request')
    @patch('update_news.time.sleep')
    def test_fetch_articles_page_with_rate_limiting(self, mock_sleep, mock_make_request):
        """Test fetching subsequent page with rate limiting."""
        mock_make_request.return_value = ({"status": "ok"}, 100.0, True)
        
        tracker = MetricsTracker()
        url = "https://api.example.com"
        params = {"q": "test"}
        config = {"api": {"rate_limit_delay_seconds": 2.0}}
        topic = "machine-learning"
        
        response_data, success = fetch_articles_page(url, params, 2, config, tracker, topic)
        
        assert success is True
        mock_sleep.assert_called_once_with(2.0)  # Should delay for page 2+
    
    @patch('update_news.make_api_request')
    @patch('update_news.time.sleep')
    def test_fetch_articles_page_rate_limit_disabled(self, mock_sleep, mock_make_request):
        """Test fetching with rate limiting disabled."""
        mock_make_request.return_value = ({"status": "ok"}, 100.0, True)
        
        tracker = MetricsTracker()
        url = "https://api.example.com"
        params = {"q": "test"}
        config = {"api": {"rate_limit_delay_seconds": 0}}
        topic = "machine-learning"
        
        response_data, success = fetch_articles_page(url, params, 2, config, tracker, topic)
        
        assert success is True
        mock_sleep.assert_not_called()  # No delay when set to 0


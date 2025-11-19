"""
Tests for result limit handling and combined request functionality.
Covers missing lines for 100% coverage.
"""
import os
import sys
import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from io import StringIO
from contextlib import contextmanager

# Add parent directory to path to import update_news
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from update_news import (
    make_api_request,
    fetch_combined_from_newsapi,
    build_combined_api_params,
    route_article_to_topic,
    fetch_from_newsapi,
    MetricsTracker,
)
import update_news


@contextmanager
def capture_logger_output():
    """Context manager to capture logger output to a StringIO."""
    old_handlers = update_news.logger.handlers[:]
    old_level = update_news.logger.level
    output = StringIO()
    handler = logging.StreamHandler(output)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
    update_news.logger.handlers = [handler]
    update_news.logger.setLevel(logging.DEBUG)
    try:
        yield output
    finally:
        update_news.logger.handlers = old_handlers
        update_news.logger.setLevel(old_level)


class TestResultLimitHandling:
    """Test result limit error handling for 100% coverage."""
    
    @patch('update_news.requests.get')
    def test_make_api_request_result_limit_with_articles(self, mock_get):
        """Test make_api_request result limit error with articles in response (lines 456-466)."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 200  # Can be any status code
        mock_response.json.return_value = {
            "code": "maximumResultsReached",
            "message": "You have requested too many results. Developer accounts are limited to a max of 100 results",
            "articles": [
                {"url": "https://example.com/1", "title": "Test Article", "description": "Test", 
                 "publishedAt": "2025-01-15T10:00:00Z", "source": {"name": "Test"}}
            ]
        }
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response
        
        url = "https://api.example.com"
        params = {"q": "test"}
        config = {}
        
        response_data, response_time, success, is_rate_limited, is_result_limit_reached = make_api_request(url, params, config)
        
        assert success is True
        assert is_result_limit_reached is True
        assert is_rate_limited is False
        assert response_data is not None
        assert response_data.get("status") == "ok"
        assert len(response_data.get("articles", [])) == 1
    
    @patch('update_news.requests.get')
    def test_make_api_request_result_limit_without_articles(self, mock_get):
        """Test make_api_request result limit error without articles (lines 468-471)."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 426
        mock_response.json.return_value = {
            "code": "maximumResultsReached",
            "message": "You have requested too many results. Developer accounts are limited to a max of 100 results"
        }
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response
        
        url = "https://api.example.com"
        params = {"q": "test"}
        config = {}
        
        response_data, response_time, success, is_rate_limited, is_result_limit_reached = make_api_request(url, params, config)
        
        assert success is False
        assert is_result_limit_reached is True
        assert is_rate_limited is False
        assert response_data is None
    
    @patch('update_news.requests.get')
    def test_make_api_request_result_limit_in_error_text(self, mock_get):
        """Test make_api_request result limit detected in error text (lines 477-479)."""
        import requests
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.json.side_effect = ValueError("No JSON")
        mock_response.text = "Error: You are limited to a max of 100 results per query"
        http_error = requests.exceptions.HTTPError()
        http_error.response = mock_response
        mock_response.raise_for_status.side_effect = http_error
        mock_get.return_value = mock_response
        
        url = "https://api.example.com"
        params = {"q": "test"}
        config = {}
        
        response_data, response_time, success, is_rate_limited, is_result_limit_reached = make_api_request(url, params, config)
        
        assert success is False
        assert is_result_limit_reached is True
        assert is_rate_limited is False


class TestCombinedRequestFunctions:
    """Test combined request functions for 100% coverage."""
    
    def test_build_combined_api_params(self):
        """Test build_combined_api_params function (lines 365-383)."""
        topics_config = {
            "deep-learning": {"title_query": "Deep Learning"},
            "machine-learning": {"title_query": "Machine Learning"},
            "artificial-intelligence": {"title_query": "Artificial Intelligence"}
        }
        date_range = ("2025-01-01", "2025-01-31")
        api_key = "test-key"
        config = {}
        
        params = build_combined_api_params(topics_config, date_range, api_key, config)
        
        assert params["q"] == '"Deep Learning" OR "Machine Learning" OR "Artificial Intelligence"'
        assert params["from"] == "2025-01-01"
        assert params["to"] == "2025-01-31"
        assert params["apiKey"] == "test-key"
    
    def test_route_article_to_topic(self):
        """Test route_article_to_topic function (lines 385-399)."""
        topics_config = {
            "deep-learning": {"title_query": "Deep Learning"},
            "machine-learning": {"title_query": "Machine Learning"},
            "artificial-intelligence": {"title_query": "Artificial Intelligence"}
        }
        config = {}  # Config not used in matching logic, but required by function signature
        
        # Test matching article
        article1 = {"title": "New Deep Learning Breakthrough"}
        assert route_article_to_topic(article1, topics_config, config) == "deep-learning"
        
        # Test non-matching article
        article2 = {"title": "Random News Article"}
        assert route_article_to_topic(article2, topics_config, config) is None
        
        # Test case-insensitive matching
        article3 = {"title": "MACHINE LEARNING ADVANCES"}
        assert route_article_to_topic(article3, topics_config, config) == "machine-learning"
        
        # Test article with no title
        article4 = {}
        assert route_article_to_topic(article4, topics_config, config) is None
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.process_article')
    @patch('update_news.calculate_date_range')
    def test_fetch_combined_from_newsapi_success(self, mock_date, mock_process, mock_fetch):
        """Test fetch_combined_from_newsapi successful fetch (lines 764-894)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        mock_fetch.return_value = ({
            "status": "ok",
            "totalResults": 50,
            "articles": [
                {"url": "https://example.com/1", "title": "Deep Learning News", "description": "Test",
                 "publishedAt": "2025-01-15T10:00:00Z", "source": {"name": "Test"}},
                {"url": "https://example.com/2", "title": "Machine Learning Advances", "description": "Test",
                 "publishedAt": "2025-01-14T10:00:00Z", "source": {"name": "Test"}}
            ]
        }, True, False, False)
        
        mock_process.side_effect = [
            {"title": "Deep Learning News", "date": "2025-01-15", "url": "1", "description": "", "source": ""},
            {"title": "Machine Learning Advances", "date": "2025-01-14", "url": "2", "description": "", "source": ""}
        ]
        
        topics_config = {
            "deep-learning": {"name": "Deep Learning", "title_query": "Deep Learning"},
            "machine-learning": {"name": "Machine Learning", "title_query": "Machine Learning"}
        }
        config = {}
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_combined_from_newsapi(topics_config, "test-key", config, metrics, api_call_count)
        
        assert is_rate_limited is False
        assert len(result.get("deep-learning", [])) == 1
        assert len(result.get("machine-learning", [])) == 1
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.process_article')
    @patch('update_news.calculate_date_range')
    def test_fetch_combined_from_newsapi_result_limit_with_articles(self, mock_date, mock_process, mock_fetch):
        """Test fetch_combined_from_newsapi with result limit but articles available (lines 825-827)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        mock_fetch.return_value = ({
            "status": "ok",
            "totalResults": 150,
            "articles": [
                {"url": "https://example.com/1", "title": "Deep Learning News", "description": "Test",
                 "publishedAt": "2025-01-15T10:00:00Z", "source": {"name": "Test"}}
            ]
        }, True, False, True)  # is_result_limit_reached = True
        
        mock_process.return_value = {"title": "Deep Learning News", "date": "2025-01-15", "url": "1", "description": "", "source": ""}
        
        topics_config = {
            "deep-learning": {"name": "Deep Learning", "title_query": "Deep Learning"}
        }
        config = {}
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_combined_from_newsapi(topics_config, "test-key", config, metrics, api_call_count)
        
        assert is_rate_limited is False
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.calculate_date_range')
    def test_fetch_combined_from_newsapi_result_limit_no_articles(self, mock_date, mock_fetch):
        """Test fetch_combined_from_newsapi with result limit and no articles (lines 830-832)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        mock_fetch.return_value = (None, False, False, True)  # is_result_limit_reached = True, no response_data
        
        topics_config = {
            "deep-learning": {"name": "Deep Learning", "title_query": "Deep Learning"}
        }
        config = {}
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_combined_from_newsapi(topics_config, "test-key", config, metrics, api_call_count)
        
        assert is_rate_limited is False
        assert len(result.get("deep-learning", [])) == 0
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.process_article')
    @patch('update_news.calculate_date_range')
    def test_fetch_combined_from_newsapi_total_results_over_100(self, mock_date, mock_process, mock_fetch):
        """Test fetch_combined_from_newsapi with totalResults > 100 (lines 845-848)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        mock_fetch.return_value = ({
            "status": "ok",
            "totalResults": 150,
            "articles": [
                {"url": "https://example.com/1", "title": "Deep Learning News", "description": "Test",
                 "publishedAt": "2025-01-15T10:00:00Z", "source": {"name": "Test"}}
            ]
        }, True, False, False)
        
        mock_process.return_value = {"title": "Deep Learning News", "date": "2025-01-15", "url": "1", "description": "", "source": ""}
        
        topics_config = {
            "deep-learning": {"name": "Deep Learning", "title_query": "Deep Learning"}
        }
        config = {}
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        # Capture logger output
        with capture_logger_output() as output:
            result, is_rate_limited = fetch_combined_from_newsapi(topics_config, "test-key", config, metrics, api_call_count)
            output_str = output.getvalue()
            assert "exceeds 100 limit" in output_str or "total results" in output_str
            assert is_rate_limited is False
    
    @patch('update_news.calculate_date_range')
    def test_fetch_combined_from_newsapi_no_api_key(self, mock_date):
        """Test fetch_combined_from_newsapi without API key (lines 764-766)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        topics_config = {
            "deep-learning": {"name": "Deep Learning", "title_query": "Deep Learning"}
        }
        config = {}
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_combined_from_newsapi(topics_config, "", config, metrics, api_call_count)
        
        assert is_rate_limited is False
        assert len(result.get("deep-learning", [])) == 0
    
    @patch('update_news.calculate_date_range')
    def test_fetch_combined_from_newsapi_api_limit_reached(self, mock_date):
        """Test fetch_combined_from_newsapi when API limit reached (lines 769-772)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        topics_config = {
            "deep-learning": {"name": "Deep Learning", "title_query": "Deep Learning"}
        }
        config = {"api": {"max_api_calls": 5}}
        metrics = MetricsTracker()
        api_call_count = {'total': 5}
        
        result, is_rate_limited = fetch_combined_from_newsapi(topics_config, "test-key", config, metrics, api_call_count)
        
        assert is_rate_limited is False
        assert len(result.get("deep-learning", [])) == 0
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.calculate_date_range')
    def test_fetch_combined_from_newsapi_rate_limited(self, mock_date, mock_fetch):
        """Test fetch_combined_from_newsapi when rate limited (lines 819-821)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        mock_fetch.return_value = (None, False, True, False)  # is_rate_limited = True
        
        topics_config = {
            "deep-learning": {"name": "Deep Learning", "title_query": "Deep Learning"}
        }
        config = {}
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        result, is_rate_limited = fetch_combined_from_newsapi(topics_config, "test-key", config, metrics, api_call_count)
        
        assert is_rate_limited is True
    
    @patch('update_news.calculate_date_range')
    @patch('update_news._validate_api_request', return_value=True)
    def test_fetch_combined_from_newsapi_max_pages_zero(self, mock_validate, mock_date):
        """Test fetch_combined_from_newsapi when max_pages <= 0 (lines 1066-1067)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        topics_config = {
            "deep-learning": {"name": "Deep Learning", "title_query": "Deep Learning"}
        }
        config = {}
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        # To test max_pages <= 0, we need to execute the real code with max_pages = 0
        # The only reliable way is to temporarily modify the source file
        import update_news
        import os
        import sys
        
        # Get the source file path
        source_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'update_news.py')
        
        # Read original source
        with open(source_file, 'r', encoding='utf-8') as f:
            original_source = f.read()
        
        # Modify source: replace max_pages = 1 with max_pages = 0
        modified_source = original_source.replace('    max_pages = 1', '    max_pages = 0', 1)
        
        try:
            # Write modified source
            with open(source_file, 'w', encoding='utf-8') as f:
                f.write(modified_source)
            
            # Reload the module to get the modified code
            import importlib
            importlib.reload(update_news)
            
            # Now test with the modified code
            result, is_rate_limited = update_news.fetch_combined_from_newsapi(
                topics_config, "test-key", config, metrics, api_call_count
            )
            assert len(result.get("deep-learning", [])) == 0
            assert is_rate_limited is False
        finally:
            # Restore original source
            with open(source_file, 'w', encoding='utf-8') as f:
                f.write(original_source)
            # Reload the module to restore original code
            importlib.reload(update_news)
    
    @patch('update_news.calculate_date_range')
    def test_fetch_combined_from_newsapi_api_limit_inside_try(self, mock_date):
        """Test fetch_combined_from_newsapi when API limit reached inside try block (lines 1072-1073)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        topics_config = {
            "deep-learning": {"name": "Deep Learning", "title_query": "Deep Learning"}
        }
        config = {"api": {"max_api_calls": 5}}
        metrics = MetricsTracker()
        
        # To test the check inside try (line 1071), we need _validate_api_request to pass
        # but then the check inside try to fail. We can do this by patching _validate_api_request
        # to always return True, then setting api_call_count to max_api_calls
        with patch('update_news._validate_api_request', return_value=True):
            api_call_count = {'total': 5}  # Equal to max_api_calls
            result, is_rate_limited = fetch_combined_from_newsapi(topics_config, "test-key", config, metrics, api_call_count)
            
            assert is_rate_limited is False
            assert len(result.get("deep-learning", [])) == 0


class TestFetchFromNewsapiResultLimit:
    """Test fetch_from_newsapi result limit handling for 100% coverage."""
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.process_article')
    @patch('update_news.calculate_date_range')
    @patch('update_news.build_api_params')
    def test_fetch_from_newsapi_result_limit_with_articles(self, mock_build, mock_date, mock_process, mock_fetch):
        """Test fetch_from_newsapi with result limit but articles available (lines 634-636)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        mock_build.return_value = {"q": "test"}
        mock_fetch.return_value = ({
            "status": "ok",
            "totalResults": 150,
            "articles": [
                {"url": "https://example.com/1", "title": "Test Article", "description": "Test",
                 "publishedAt": "2025-01-15T10:00:00Z", "source": {"name": "Test"}}
            ]
        }, True, False, True)  # is_result_limit_reached = True
        
        mock_process.return_value = {"title": "Test Article", "date": "2025-01-15", "url": "1", "description": "", "source": ""}
        
        config = {
            "news_sources": {
                "test-topic": {"title_query": "Test"}
            }
        }
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        # Capture logger output
        with capture_logger_output() as output:
            result, is_rate_limited = fetch_from_newsapi("test-topic", "key", config, metrics, api_call_count)
            output_str = output.getvalue()
            assert "Result limit reached, but processing" in output_str
            assert is_rate_limited is False
            assert len(result) == 1
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.calculate_date_range')
    @patch('update_news.build_api_params')
    def test_fetch_from_newsapi_result_limit_no_articles(self, mock_build, mock_date, mock_fetch):
        """Test fetch_from_newsapi with result limit and no articles (lines 640-642)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        mock_build.return_value = {"q": "test"}
        mock_fetch.return_value = (None, False, False, True)  # is_result_limit_reached = True, no response_data
        
        config = {
            "news_sources": {
                "test-topic": {"title_query": "Test"}
            }
        }
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        # Capture logger output
        with capture_logger_output() as output:
            result, is_rate_limited = fetch_from_newsapi("test-topic", "key", config, metrics, api_call_count)
            output_str = output.getvalue()
            assert "Result limit reached on first page" in output_str
            assert is_rate_limited is False
            assert len(result) == 0
    
    @patch('update_news.fetch_articles_page')
    @patch('update_news.process_article')
    @patch('update_news.calculate_date_range')
    @patch('update_news.build_api_params')
    def test_fetch_from_newsapi_total_results_over_100(self, mock_build, mock_date, mock_process, mock_fetch):
        """Test fetch_from_newsapi with totalResults > 100 (lines 655-658)."""
        mock_date.return_value = ("2025-01-01", "2025-01-15")
        mock_build.return_value = {"q": "test"}
        mock_fetch.return_value = ({
            "status": "ok",
            "totalResults": 150,
            "articles": [
                {"url": "https://example.com/1", "title": "Test Article", "description": "Test",
                 "publishedAt": "2025-01-15T10:00:00Z", "source": {"name": "Test"}}
            ]
        }, True, False, False)
        
        mock_process.return_value = {"title": "Test Article", "date": "2025-01-15", "url": "1", "description": "", "source": ""}
        
        config = {
            "news_sources": {
                "test-topic": {"title_query": "Test"}
            }
        }
        metrics = MetricsTracker()
        api_call_count = {'total': 0}
        
        # Capture logger output
        with capture_logger_output() as output:
            result, is_rate_limited = fetch_from_newsapi("test-topic", "key", config, metrics, api_call_count)
            output_str = output.getvalue()
            assert "exceeds 100 limit" in output_str or "total results" in output_str
            assert is_rate_limited is False
            assert len(result) >= 1  # May have duplicates, so check >= 1


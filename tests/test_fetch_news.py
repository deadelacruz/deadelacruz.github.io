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
        
        result = fetch_from_newsapi("machine-learning", "", config, metrics)
        
        assert result == []
    
    def test_fetch_from_newsapi_no_topic_config(self):
        """Test fetching with missing topic configuration."""
        config = {"news_sources": {}}
        metrics = MetricsTracker()
        
        result = fetch_from_newsapi("unknown-topic", "test-key", config, metrics)
        
        assert result == []
    
    def test_fetch_from_newsapi_no_title_query(self):
        """Test fetching with topic config but no title_query."""
        config = {
            "news_sources": {
                "test-topic": {}
            }
        }
        metrics = MetricsTracker()
        
        result = fetch_from_newsapi("test-topic", "test-key", config, metrics)
        
        assert result == []
    
    @patch('update_news.fetch_articles_page')
    def test_fetch_from_newsapi_success_single_page(self, mock_fetch_page):
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
        }, True)
        
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
        
        result = fetch_from_newsapi("machine-learning", "test-key", config, metrics)
        
        assert len(result) == 1
        assert result[0]["title"] == "Machine Learning News"
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
            }, True),
            # Second page with error status
            ({
                "status": "error",
                "message": "Rate limit exceeded"
            }, True)
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
        
        result = fetch_from_newsapi("machine-learning", "test-key", config, metrics)
        
        # Should stop after second page returns error status (line 465)
        assert mock_fetch_page.call_count == 2
    
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
            }, True),
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
            }, True)
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
        
        result = fetch_from_newsapi("machine-learning", "test-key", config, metrics)
        
        # Should fetch 2 pages (total 250 results / 100 per page = 3 pages, but max_pages limits to 5)
        assert mock_fetch_page.call_count >= 2
    
    @patch('update_news.fetch_articles_page')
    def test_fetch_from_newsapi_api_error_status(self, mock_fetch_page):
        """Test handling API error status."""
        mock_fetch_page.return_value = ({
            "status": "error",
            "message": "Invalid API key"
        }, True)
        
        config = {
            "news_sources": {
                "machine-learning": {
                    "title_query": "Machine Learning",
                    "related_keywords": []
                }
            }
        }
        metrics = MetricsTracker()
        
        result = fetch_from_newsapi("machine-learning", "test-key", config, metrics)
        
        assert result == []
    
    @patch('update_news.fetch_articles_page')
    def test_fetch_from_newsapi_no_results(self, mock_fetch_page):
        """Test handling no results from API."""
        mock_fetch_page.return_value = ({
            "status": "ok",
            "totalResults": 0,
            "articles": []
        }, True)
        
        config = {
            "news_sources": {
                "machine-learning": {
                    "title_query": "Machine Learning",
                    "related_keywords": []
                }
            }
        }
        metrics = MetricsTracker()
        
        result = fetch_from_newsapi("machine-learning", "test-key", config, metrics)
        
        assert result == []
    
    @patch('update_news.fetch_articles_page')
    def test_fetch_from_newsapi_fetch_failure(self, mock_fetch_page):
        """Test handling fetch page failure."""
        mock_fetch_page.return_value = (None, False)
        
        config = {
            "news_sources": {
                "machine-learning": {
                    "title_query": "Machine Learning",
                    "related_keywords": []
                }
            }
        }
        metrics = MetricsTracker()
        
        result = fetch_from_newsapi("machine-learning", "test-key", config, metrics)
        
        assert result == []
    
    @patch('update_news.fetch_articles_page')
    def test_fetch_from_newsapi_pagination_stops_on_error(self, mock_fetch_page):
        """Test pagination stops when page fetch fails."""
        mock_fetch_page.side_effect = [
            ({
                "status": "ok",
                "totalResults": 250,
                "articles": [{"url": "1", "title": "Test", "description": "test", "publishedAt": "2025-01-15T10:00:00Z", "source": {"name": "Test"}}]
            }, True),
            (None, False)  # Second page fails
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
        
        result = fetch_from_newsapi("machine-learning", "test-key", config, metrics)
        
        # Should stop after first page fails
        assert mock_fetch_page.call_count == 2


"""
Tests for edge cases and remaining coverage gaps.
"""
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from update_news import (
    process_article,
    article_matches_keywords,
    MetricsTracker,
    get_config_value
)


class TestArticleMatchesKeywordsEdgeCases:
    """Test edge cases in article_matches_keywords."""
    
    def test_article_matches_keywords_empty_keywords(self):
        """Test with empty keywords list."""
        article = {
            "title": "Test Article",
            "description": "Some description"
        }
        keywords = []
        config = {}
        
        result = article_matches_keywords(article, keywords, config)
        assert result is False
    
    def test_article_matches_keywords_partial_match(self):
        """Test partial keyword matching."""
        article = {
            "title": "Deep Learning Neural Networks",
            "description": "Article about AI"
        }
        keywords = ["deep learning", "neural networks"]
        config = {}
        
        result = article_matches_keywords(article, keywords, config)
        assert result is True


class TestProcessArticleEdgeCases:
    """Test edge cases in process_article."""
    
    def test_process_article_empty_string_description(self):
        """Test with empty string description."""
        from update_news import MetricsTracker
        tracker = MetricsTracker()
        seen_urls = set()
        
        article = {
            "url": "https://example.com/article1",
            "title": "Deep Learning News",
            "description": "",  # Empty string
            "publishedAt": "2025-01-15T10:00:00Z",
            "source": {"name": "Tech News"}
        }
        
        keywords = ["deep learning"]
        config = {}
        topic = "deep-learning"
        
        result = process_article(article, keywords, seen_urls, config, tracker, topic)
        
        assert result is not None
        assert result["description"] == "No description available."
    
    def test_process_article_missing_publishedAt(self):
        """Test article with missing publishedAt."""
        from update_news import MetricsTracker
        tracker = MetricsTracker()
        seen_urls = set()
        
        article = {
            "url": "https://example.com/article1",
            "title": "Deep Learning News",
            "description": "Some description",
            "source": {"name": "Tech News"}
            # No publishedAt
        }
        
        keywords = ["deep learning"]
        config = {}
        topic = "deep-learning"
        
        result = process_article(article, keywords, seen_urls, config, tracker, topic)
        
        assert result is not None
        assert "date" in result
        assert len(result["date"]) == 10  # Should be YYYY-MM-DD format
    
    def test_process_article_missing_source(self):
        """Test article with missing source."""
        from update_news import MetricsTracker
        tracker = MetricsTracker()
        seen_urls = set()
        
        article = {
            "url": "https://example.com/article1",
            "title": "Deep Learning News",
            "description": "Some description",
            "publishedAt": "2025-01-15T10:00:00Z"
            # No source
        }
        
        keywords = ["deep learning"]
        config = {}
        topic = "deep-learning"
        
        result = process_article(article, keywords, seen_urls, config, tracker, topic)
        
        assert result is not None
        assert result["source"] == "Unknown"
    
    def test_process_article_source_without_name(self):
        """Test article with source dict but no name."""
        from update_news import MetricsTracker
        tracker = MetricsTracker()
        seen_urls = set()
        
        article = {
            "url": "https://example.com/article1",
            "title": "Deep Learning News",
            "description": "Some description",
            "publishedAt": "2025-01-15T10:00:00Z",
            "source": {}  # Empty source dict
        }
        
        keywords = ["deep learning"]
        config = {}
        topic = "deep-learning"
        
        result = process_article(article, keywords, seen_urls, config, tracker, topic)
        
        assert result is not None
        assert result["source"] == "Unknown"
    
    def test_process_article_custom_description_length(self):
        """Test with custom max description length from config."""
        from update_news import MetricsTracker
        tracker = MetricsTracker()
        seen_urls = set()
        
        long_description = "A" * 500
        article = {
            "url": "https://example.com/article1",
            "title": "Deep Learning News",
            "description": long_description,
            "publishedAt": "2025-01-15T10:00:00Z",
            "source": {"name": "Tech News"}
        }
        
        keywords = ["deep learning"]
        config = {
            "article_processing": {
                "max_description_length": 100
            }
        }
        topic = "deep-learning"
        
        result = process_article(article, keywords, seen_urls, config, tracker, topic)
        
        assert result is not None
        assert len(result["description"]) == 100


class TestGetConfigValueEdgeCases:
    """Test edge cases in get_config_value."""
    
    def test_get_config_value_none_value(self):
        """Test when config value is explicitly None."""
        config = {
            "api": {
                "timeout_seconds": None
            }
        }
        result = get_config_value(config, "api.timeout_seconds", 15)
        assert result == 15  # Should return default
    
    def test_get_config_value_empty_string(self):
        """Test when config value is empty string."""
        config = {
            "api": {
                "timeout_seconds": ""
            }
        }
        result = get_config_value(config, "api.timeout_seconds", 15)
        assert result == ""  # Empty string is not None, so it's returned
    
    def test_get_config_value_zero(self):
        """Test when config value is 0 (falsy but valid)."""
        config = {
            "api": {
                "rate_limit_delay_seconds": 0
            }
        }
        result = get_config_value(config, "api.rate_limit_delay_seconds", 1.0)
        assert result == 0  # 0 is not None, so it's returned


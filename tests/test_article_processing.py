"""
Unit tests for article processing functions.
"""
import os
import sys
import pytest

# Add parent directory to path to import update_news
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from update_news import process_article, DEFAULT_MAX_DESCRIPTION_LENGTH


class TestProcessArticle:
    """Test article processing functionality."""
    
    def test_process_article_valid(self):
        """Test processing a valid article."""
        from update_news import MetricsTracker
        tracker = MetricsTracker()
        seen_urls = set()
        
        article = {
            "url": "https://example.com/article1",
            "title": "Deep Learning Breakthrough",
            "description": "A new breakthrough in deep learning research",
            "publishedAt": "2025-01-15T10:00:00Z",
            "source": {"name": "Tech News"}
        }
        
        keywords = ["deep learning"]
        config = {}
        topic = "deep-learning"
        
        result = process_article(article, keywords, seen_urls, config, tracker, topic)
        
        assert result is not None
        assert result["title"] == "Deep Learning Breakthrough"
        assert result["url"] == "https://example.com/article1"
        assert result["date"] == "2025-01-15"
        assert result["source"] == "Tech News"
        assert "https://example.com/article1" in seen_urls
    
    def test_process_article_duplicate_url(self):
        """Test that duplicate URLs are filtered."""
        from update_news import MetricsTracker
        tracker = MetricsTracker()
        seen_urls = {"https://example.com/article1"}
        
        article = {
            "url": "https://example.com/article1",
            "title": "Deep Learning News",
            "description": "Some description"
        }
        
        keywords = ["deep learning"]
        config = {}
        topic = "deep-learning"
        
        result = process_article(article, keywords, seen_urls, config, tracker, topic)
        
        assert result is None
    
    def test_process_article_no_url(self):
        """Test article without URL is filtered."""
        from update_news import MetricsTracker
        tracker = MetricsTracker()
        seen_urls = set()
        
        article = {
            "title": "Deep Learning News",
            "description": "Some description"
        }
        
        keywords = ["deep learning"]
        config = {}
        topic = "deep-learning"
        
        result = process_article(article, keywords, seen_urls, config, tracker, topic)
        
        assert result is None
    
    def test_process_article_no_title(self):
        """Test article without title is filtered."""
        from update_news import MetricsTracker
        tracker = MetricsTracker()
        seen_urls = set()
        
        article = {
            "url": "https://example.com/article1",
            "description": "Some description"
        }
        
        keywords = ["deep learning"]
        config = {}
        topic = "deep-learning"
        
        result = process_article(article, keywords, seen_urls, config, tracker, topic)
        
        assert result is None
    
    def test_process_article_keyword_mismatch(self):
        """Test article that doesn't match keywords is filtered."""
        from update_news import MetricsTracker
        tracker = MetricsTracker()
        seen_urls = set()
        
        article = {
            "url": "https://example.com/article1",
            "title": "Weather Forecast",
            "description": "Sunny skies expected"
        }
        
        keywords = ["deep learning"]
        config = {}
        topic = "deep-learning"
        
        result = process_article(article, keywords, seen_urls, config, tracker, topic)
        
        assert result is None
        assert tracker.topic_metrics[topic]["articles_filtered"] == 1
    
    def test_process_article_description_truncated(self):
        """Test that long descriptions are truncated."""
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
        config = {}
        topic = "deep-learning"
        
        result = process_article(article, keywords, seen_urls, config, tracker, topic)
        
        assert result is not None
        assert len(result["description"]) <= DEFAULT_MAX_DESCRIPTION_LENGTH
    
    def test_process_article_no_description(self):
        """Test article with no description uses default."""
        from update_news import MetricsTracker
        tracker = MetricsTracker()
        seen_urls = set()
        
        article = {
            "url": "https://example.com/article1",
            "title": "Deep Learning News",
            "description": None,
            "publishedAt": "2025-01-15T10:00:00Z",
            "source": {"name": "Tech News"}
        }
        
        keywords = ["deep learning"]
        config = {}
        topic = "deep-learning"
        
        result = process_article(article, keywords, seen_urls, config, tracker, topic)
        
        assert result is not None
        assert result["description"] == "No description available."


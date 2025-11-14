"""
Unit tests for keyword processing functions.
"""
import os
import sys
import pytest

# Add parent directory to path to import update_news
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from update_news import normalize_keywords, article_matches_keywords


class TestNormalizeKeywords:
    """Test keyword normalization."""
    
    def test_normalize_keywords_includes_title_query(self):
        """Test that title_query is always included."""
        keywords = normalize_keywords(["neural networks", "cnn"], "Deep Learning")
        assert "deep learning" in keywords
        assert "neural networks" in keywords
        assert "cnn" in keywords
    
    def test_normalize_keywords_lowercase(self):
        """Test that all keywords are lowercase."""
        keywords = normalize_keywords(["Neural Networks", "CNN"], "Deep Learning")
        assert all(kw.islower() for kw in keywords)
    
    def test_normalize_keywords_no_duplicates(self):
        """Test that duplicates are removed."""
        keywords = normalize_keywords(["deep learning", "neural networks"], "Deep Learning")
        # "deep learning" should only appear once
        assert keywords.count("deep learning") == 1
    
    def test_normalize_keywords_empty_list(self):
        """Test with empty keyword list."""
        keywords = normalize_keywords([], "Machine Learning")
        assert len(keywords) == 1
        assert "machine learning" in keywords


class TestArticleMatchesKeywords:
    """Test article keyword matching."""
    
    def test_article_matches_in_title(self):
        """Test matching keyword in article title."""
        article = {
            "title": "New Breakthrough in Deep Learning Research",
            "description": "Some description"
        }
        keywords = ["deep learning", "neural networks"]
        config = {}
        
        assert article_matches_keywords(article, keywords, config) is True
    
    def test_article_matches_in_description(self):
        """Test matching keyword in article description."""
        article = {
            "title": "AI Research Update",
            "description": "This article discusses neural networks and their applications"
        }
        keywords = ["neural networks", "deep learning"]
        config = {}
        
        assert article_matches_keywords(article, keywords, config) is True
    
    def test_article_no_match(self):
        """Test article that doesn't match any keywords."""
        article = {
            "title": "Weather Forecast for Tomorrow",
            "description": "Sunny skies expected"
        }
        keywords = ["deep learning", "neural networks"]
        config = {}
        
        assert article_matches_keywords(article, keywords, config) is False
    
    def test_article_case_insensitive_match(self):
        """Test that matching is case-insensitive."""
        article = {
            "title": "DEEP LEARNING Advances",
            "description": "Some description"
        }
        keywords = ["deep learning"]
        config = {}
        
        assert article_matches_keywords(article, keywords, config) is True
    
    def test_article_empty_description(self):
        """Test article with empty description."""
        article = {
            "title": "Machine Learning News",
            "description": ""
        }
        keywords = ["machine learning"]
        config = {}
        
        assert article_matches_keywords(article, keywords, config) is True


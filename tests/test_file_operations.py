"""
Unit tests for file operations.
"""
import os
import sys
import pytest
import yaml
import tempfile
import shutil

# Add parent directory to path to import update_news
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from update_news import update_news_file, DATA_DIR


class TestUpdateNewsFile:
    """Test news file update functionality."""
    
    def test_update_news_file_success(self, tmp_path):
        """Test successfully updating news file."""
        # Temporarily change DATA_DIR
        import update_news
        original_dir = update_news.DATA_DIR
        test_dir = str(tmp_path / "_data" / "news")
        update_news.DATA_DIR = test_dir
        
        news_items = [
            {
                "title": "Test Article 1",
                "description": "Description 1",
                "url": "https://example.com/1",
                "date": "2025-01-15",
                "source": "Test Source"
            },
            {
                "title": "Test Article 2",
                "description": "Description 2",
                "url": "https://example.com/2",
                "date": "2025-01-14",
                "source": "Test Source"
            }
        ]
        
        try:
            result = update_news_file("test-topic", news_items)
            
            assert result is True
            file_path = os.path.join(test_dir, "test-topic.yml")
            assert os.path.exists(file_path)
            
            # Verify file content
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            assert "news_items" in data
            assert len(data["news_items"]) == 2
            # Should be sorted by date (newest first)
            assert data["news_items"][0]["date"] == "2025-01-15"
        finally:
            update_news.DATA_DIR = original_dir
    
    def test_update_news_file_empty_list(self, tmp_path):
        """Test updating with empty news items list."""
        import update_news
        original_dir = update_news.DATA_DIR
        test_dir = str(tmp_path / "_data" / "news")
        update_news.DATA_DIR = test_dir
        
        try:
            result = update_news_file("test-topic", [])
            
            assert result is True
            file_path = os.path.join(test_dir, "test-topic.yml")
            assert os.path.exists(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            assert data["news_items"] == []
        finally:
            update_news.DATA_DIR = original_dir
    
    def test_update_news_file_sorts_by_date(self, tmp_path):
        """Test that articles are sorted by date (newest first)."""
        import update_news
        original_dir = update_news.DATA_DIR
        test_dir = str(tmp_path / "_data" / "news")
        update_news.DATA_DIR = test_dir
        
        news_items = [
            {"title": "Old", "date": "2025-01-10", "url": "1", "description": "", "source": ""},
            {"title": "New", "date": "2025-01-15", "url": "2", "description": "", "source": ""},
            {"title": "Middle", "date": "2025-01-12", "url": "3", "description": "", "source": ""}
        ]
        
        try:
            result = update_news_file("test-topic", news_items)
            
            assert result is True
            file_path = os.path.join(test_dir, "test-topic.yml")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # Should be sorted newest first
            assert data["news_items"][0]["date"] == "2025-01-15"
            assert data["news_items"][1]["date"] == "2025-01-12"
            assert data["news_items"][2]["date"] == "2025-01-10"
        finally:
            update_news.DATA_DIR = original_dir
    
    def test_update_news_file_creates_directory(self, tmp_path):
        """Test that function creates directory if it doesn't exist."""
        import update_news
        original_dir = update_news.DATA_DIR
        test_dir = str(tmp_path / "new" / "nested" / "dir" / "news")
        update_news.DATA_DIR = test_dir
        
        news_items = [{"title": "Test", "date": "2025-01-15", "url": "1", "description": "", "source": ""}]
        
        try:
            result = update_news_file("test-topic", news_items)
            
            assert result is True
            assert os.path.exists(test_dir)
        finally:
            update_news.DATA_DIR = original_dir
    
    def test_update_news_file_handles_missing_date(self, tmp_path):
        """Test handling articles with missing date field."""
        import update_news
        original_dir = update_news.DATA_DIR
        test_dir = str(tmp_path / "_data" / "news")
        update_news.DATA_DIR = test_dir
        
        news_items = [
            {"title": "No Date", "url": "1", "description": "", "source": ""},
            {"title": "Has Date", "date": "2025-01-15", "url": "2", "description": "", "source": ""}
        ]
        
        try:
            result = update_news_file("test-topic", news_items)
            
            assert result is True
            file_path = os.path.join(test_dir, "test-topic.yml")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            assert len(data["news_items"]) == 2
        finally:
            update_news.DATA_DIR = original_dir


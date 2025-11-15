"""
Unit tests for configuration loading functions.
"""
import os
import sys
import pytest
import yaml
import tempfile

# Add parent directory to path to import update_news
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from update_news import load_config, get_config_value, DEFAULT_LOOKBACK_DAYS


class TestLoadConfig:
    """Test configuration loading functionality."""
    
    def test_load_config_file_exists(self, tmp_path):
        """Test loading config from existing file."""
        config_file = tmp_path / "_data" / "news_config.yml"
        config_file.parent.mkdir(parents=True)
        
        test_config = {
            'date_range': {
                'lookback_days': 60
            }
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        # Temporarily change the config file path
        import update_news
        original_path = update_news.CONFIG_FILE
        update_news.CONFIG_FILE = str(config_file)
        
        try:
            config = load_config()
            assert config['date_range']['lookback_days'] == 60
        finally:
            update_news.CONFIG_FILE = original_path
    
    def test_load_config_file_not_exists(self):
        """Test loading config when file doesn't exist."""
        import update_news
        original_path = update_news.CONFIG_FILE
        update_news.CONFIG_FILE = "nonexistent_config.yml"
        
        try:
            config = load_config()
            assert config == {}
        finally:
            update_news.CONFIG_FILE = original_path


class TestGetConfigValue:
    """Test config value retrieval."""
    
    def test_get_nested_value(self):
        """Test getting nested config value."""
        config = {
            'api': {
                'timeout_seconds': 30
            }
        }
        value = get_config_value(config, 'api.timeout_seconds', 15)
        assert value == 30
    
    def test_get_missing_value_returns_default(self):
        """Test getting missing value returns default."""
        config = {}
        value = get_config_value(config, 'api.timeout_seconds', 15)
        assert value == 15
    
    def test_get_partially_missing_path(self):
        """Test getting value with partially missing path."""
        config = {
            'api': {}
        }
        value = get_config_value(config, 'api.timeout_seconds', 15)
        assert value == 15
    
    def test_get_deeply_nested_value(self):
        """Test getting deeply nested value."""
        config = {
            'date_range': {
                'lookback_days': 45
            }
        }
        value = get_config_value(config, 'date_range.lookback_days', DEFAULT_LOOKBACK_DAYS)
        assert value == 45


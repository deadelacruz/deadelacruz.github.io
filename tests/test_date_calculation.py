"""
Unit tests for date range calculation.
"""
import os
import sys
import pytest
from datetime import datetime, timedelta, timezone

# Add parent directory to path to import update_news
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from update_news import calculate_date_range, DEFAULT_LOOKBACK_DAYS, DEFAULT_EXCLUDE_TODAY_OFFSET


class TestCalculateDateRange:
    """Test date range calculation functionality."""
    
    def test_calculate_date_range_with_config(self):
        """Test date range calculation with custom config."""
        config = {
            'date_range': {
                'lookback_days': 60,
                'exclude_today': True,
                'exclude_today_offset_days': 1
            }
        }
        from_date, to_date = calculate_date_range(config)
        
        # Verify format
        assert len(from_date) == 10  # YYYY-MM-DD
        assert len(to_date) == 10
        assert from_date.count('-') == 2
        assert to_date.count('-') == 2
    
    def test_calculate_date_range_with_defaults(self):
        """Test date range calculation with default values."""
        config = {}
        from_date, to_date = calculate_date_range(config)
        
        # Should use defaults
        assert len(from_date) == 10
        assert len(to_date) == 10
    
    def test_calculate_date_range_excludes_today(self):
        """Test that date range excludes today when configured."""
        config = {
            'date_range': {
                'lookback_days': 30,
                'exclude_today': True,
                'exclude_today_offset_days': 1
            }
        }
        from_date, to_date = calculate_date_range(config)
        
        # Parse dates
        from_dt = datetime.strptime(from_date, '%Y-%m-%d')
        to_dt = datetime.strptime(to_date, '%Y-%m-%d')
        now = datetime.now(timezone.utc)
        
        # to_date should be yesterday
        expected_to = (now - timedelta(days=1)).date()
        assert to_dt.date() == expected_to
        
        # from_date should be lookback_days ago
        expected_from = (now - timedelta(days=30)).date()
        assert from_dt.date() == expected_from
    
    def test_calculate_date_range_includes_today(self):
        """Test that date range includes today when configured."""
        config = {
            'date_range': {
                'lookback_days': 30,
                'exclude_today': False
            }
        }
        from_date, to_date = calculate_date_range(config)
        
        to_dt = datetime.strptime(to_date, '%Y-%m-%d')
        now = datetime.now(timezone.utc)
        
        # to_date should be today
        assert to_dt.date() == now.date()


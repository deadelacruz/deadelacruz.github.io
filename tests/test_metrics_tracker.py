"""
Unit tests for MetricsTracker class.
"""
import os
import sys
import pytest
import json
import tempfile
import time

# Add parent directory to path to import update_news
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from update_news import MetricsTracker


class TestMetricsTracker:
    """Test metrics tracking functionality."""
    
    def test_initialization(self):
        """Test MetricsTracker initialization."""
        tracker = MetricsTracker()
        assert tracker.start_time > 0
        assert len(tracker.metrics) == 0
        assert len(tracker.topic_metrics) == 0
    
    def test_record_api_call(self):
        """Test recording API calls."""
        tracker = MetricsTracker()
        tracker.record_api_call("machine-learning", 150.5, True)
        
        assert tracker.topic_metrics["machine-learning"]["api_calls"] == 1
        assert tracker.topic_metrics["machine-learning"]["api_errors"] == 0
        assert 150.5 in tracker.topic_metrics["machine-learning"]["response_time_ms"]
    
    def test_record_api_call_error(self):
        """Test recording API call errors."""
        tracker = MetricsTracker()
        tracker.record_api_call("machine-learning", 200.0, False)
        
        assert tracker.topic_metrics["machine-learning"]["api_calls"] == 1
        assert tracker.topic_metrics["machine-learning"]["api_errors"] == 1
    
    def test_record_article_fetched(self):
        """Test recording fetched articles."""
        tracker = MetricsTracker()
        tracker.record_article_fetched("machine-learning")
        tracker.record_article_fetched("machine-learning")
        
        assert tracker.topic_metrics["machine-learning"]["articles_fetched"] == 2
    
    def test_record_article_filtered(self):
        """Test recording filtered articles."""
        tracker = MetricsTracker()
        tracker.record_article_filtered("machine-learning")
        
        assert tracker.topic_metrics["machine-learning"]["articles_filtered"] == 1
    
    def test_record_article_saved(self):
        """Test recording saved articles."""
        tracker = MetricsTracker()
        tracker.record_article_saved("machine-learning", 10)
        
        assert tracker.topic_metrics["machine-learning"]["articles_saved"] == 10
    
    def test_get_total_time(self):
        """Test getting total execution time."""
        tracker = MetricsTracker()
        time.sleep(0.1)  # Small delay
        total_time = tracker.get_total_time()
        
        assert total_time >= 0.1
        assert total_time < 1.0  # Should be less than 1 second
    
    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        tracker = MetricsTracker()
        tracker.record_api_call("machine-learning", 100.0, True)
        tracker.record_api_call("machine-learning", 200.0, True)
        tracker.record_article_fetched("machine-learning")
        tracker.record_article_saved("machine-learning", 5)
        
        metrics_dict = tracker.to_dict()
        
        assert "execution_time_seconds" in metrics_dict
        assert "timestamp" in metrics_dict
        assert "topics" in metrics_dict
        assert "machine-learning" in metrics_dict["topics"]
        
        topic_metrics = metrics_dict["topics"]["machine-learning"]
        assert topic_metrics["api_calls"] == 2
        assert topic_metrics["articles_fetched"] == 1
        assert topic_metrics["articles_saved"] == 5
        assert "response_time_stats" in topic_metrics
    
    def test_export_to_json(self, tmp_path):
        """Test exporting metrics to JSON file."""
        tracker = MetricsTracker()
        tracker.record_api_call("machine-learning", 150.0, True)
        tracker.record_article_saved("machine-learning", 3)
        
        json_path = str(tmp_path / "test_metrics.json")
        result = tracker.export_to_json(json_path)
        
        assert result is True
        assert os.path.exists(json_path)
        
        # Verify JSON content
        with open(json_path, 'r') as f:
            data = json.load(f)
        
        assert "topics" in data
        assert "machine-learning" in data["topics"]
    
    def test_export_to_json_creates_directory(self, tmp_path):
        """Test that export creates directory if it doesn't exist."""
        tracker = MetricsTracker()
        json_path = str(tmp_path / "nested" / "dir" / "metrics.json")
        result = tracker.export_to_json(json_path)
        
        assert result is True
        assert os.path.exists(json_path)
    
    def test_multiple_topics(self):
        """Test tracking metrics for multiple topics."""
        tracker = MetricsTracker()
        tracker.record_api_call("machine-learning", 100.0, True)
        tracker.record_api_call("deep-learning", 150.0, True)
        tracker.record_article_saved("machine-learning", 5)
        tracker.record_article_saved("deep-learning", 3)
        
        metrics_dict = tracker.to_dict()
        
        assert len(metrics_dict["topics"]) == 2
        assert "machine-learning" in metrics_dict["topics"]
        assert "deep-learning" in metrics_dict["topics"]
    
    def test_print_summary_with_metrics(self):
        """Test print_summary with actual metrics data."""
        tracker = MetricsTracker()
        tracker.record_api_call("test-topic", 100.0, True)
        tracker.record_api_call("test-topic", 200.0, True)
        tracker.record_article_fetched("test-topic")
        tracker.record_article_filtered("test-topic")
        tracker.record_article_saved("test-topic", 5)
        
        # Capture stdout
        from io import StringIO
        import sys
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            tracker.print_summary()
            output = sys.stdout.getvalue()
            assert "METRICS" in output
            assert "test-topic" in output
            assert "API Calls: 2" in output
            assert "Avg Response Time" in output
        finally:
            sys.stdout = old_stdout
    
    def test_print_summary_empty_metrics(self):
        """Test print_summary with no metrics."""
        tracker = MetricsTracker()
        
        from io import StringIO
        import sys
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        try:
            tracker.print_summary()
            output = sys.stdout.getvalue()
            assert "METRICS" in output
            assert "Total execution time" in output
        finally:
            sys.stdout = old_stdout


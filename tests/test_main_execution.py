"""
Tests for main execution and error handling.
"""
import os
import sys
import pytest
from unittest.mock import patch, Mock

# Add parent directory to path to import update_news
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMainExecution:
    """Test main execution paths via run_cli wrapper."""
    
    @patch('update_news.sys.exit')
    @patch('update_news.main')
    def test_main_success_exit(self, mock_main, mock_exit):
        """Test run_cli exits with success code."""
        import update_news
        
        update_news.run_cli()
        
        mock_main.assert_called_once()
        mock_exit.assert_called_once_with(0)
    
    @patch('update_news.sys.exit')
    @patch('update_news.main')
    def test_main_keyboard_interrupt_handling(self, mock_main, mock_exit):
        """Test KeyboardInterrupt handling in run_cli."""
        import update_news
        mock_main.side_effect = KeyboardInterrupt()
        
        update_news.run_cli()
        
        mock_exit.assert_called_once_with(1)
    
    @patch('update_news.sys.exit')
    @patch('update_news.traceback.format_exc', return_value="Traceback...")
    @patch('update_news.main')
    def test_main_general_exception_handling(self, mock_main, mock_format, mock_exit):
        """Test general exception handling in run_cli."""
        import update_news
        mock_main.side_effect = Exception("Test error")
        
        update_news.run_cli()
        
        mock_exit.assert_called_once_with(1)
        mock_format.assert_called_once()


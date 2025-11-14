"""
Test the if __name__ == "__main__" block execution.
"""
import os
import sys
import pytest
from unittest.mock import patch, Mock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMainBlock:
    """Test the CLI wrapper used in the __main__ block."""
    
    @patch('update_news.sys.exit')
    @patch('update_news.main')
    def test_main_block_success(self, mock_main, mock_exit):
        """Test successful main execution."""
        import update_news
        
        update_news.run_cli()
        
        mock_main.assert_called_once()
        mock_exit.assert_called_once_with(0)
    
    @patch('update_news.sys.exit')
    @patch('update_news.main')
    def test_main_block_keyboard_interrupt(self, mock_main, mock_exit):
        """Test KeyboardInterrupt handling."""
        import update_news
        mock_main.side_effect = KeyboardInterrupt()
        
        update_news.run_cli()
        
        mock_exit.assert_called_once_with(1)
    
    @patch('update_news.sys.exit')
    @patch('update_news.traceback.format_exc', return_value="Traceback...")
    @patch('update_news.main')
    def test_main_block_general_exception(self, mock_main, mock_format, mock_exit):
        """Test general exception handling."""
        import update_news
        mock_main.side_effect = Exception("Test error")
        
        update_news.run_cli()
        
        mock_exit.assert_called_once_with(1)
        mock_format.assert_called_once()


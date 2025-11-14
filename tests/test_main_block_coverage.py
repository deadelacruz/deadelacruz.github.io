"""
Test to achieve 100% coverage of the __main__ block by executing the code directly.
"""
import os
import sys
from unittest.mock import patch


class TestMainBlockDirectExecution:
    """Test the run_cli helper directly to ensure coverage."""
    
    @patch('update_news.sys.exit')
    @patch('update_news.main')
    def test_main_block_success_path(self, mock_main, mock_exit):
        import update_news
        
        update_news.run_cli()
        
        mock_main.assert_called_once()
        mock_exit.assert_called_once_with(0)
    
    @patch('update_news.sys.exit')
    @patch('update_news.main')
    def test_main_block_keyboard_interrupt(self, mock_main, mock_exit):
        import update_news
        mock_main.side_effect = KeyboardInterrupt()
        
        update_news.run_cli()
        
        mock_exit.assert_called_once_with(1)
    
    @patch('update_news.sys.exit')
    @patch('update_news.traceback.format_exc', return_value="Traceback...")
    @patch('update_news.main')
    def test_main_block_general_exception(self, mock_main, mock_format, mock_exit):
        import update_news
        mock_main.side_effect = Exception("Unexpected error")
        
        update_news.run_cli()
        
        mock_exit.assert_called_once_with(1)
        mock_format.assert_called_once()


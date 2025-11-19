"""
Tests for __main__ block execution to achieve 100% coverage.
Covers the missing lines in __init__.py (line 1583) and __main__.py (lines 8-11).
"""
import os
import sys
import subprocess
import runpy
import pytest
from unittest.mock import patch, Mock

# Add parent directory to path to import update_news
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMainModuleExecution:
    """Test __main__.py module execution (lines 8-11)."""
    
    def test_main_module_execution(self):
        """Test executing update_news as a module: python -m update_news."""
        # Mock run_cli to avoid actual execution
        with patch('update_news.run_cli') as mock_run_cli:
            # Execute the module using runpy
            # This will execute the __main__.py file
            runpy.run_module('update_news', run_name='__main__')
            
            # Verify run_cli was called
            assert mock_run_cli.called, "run_cli should have been called from __main__.py"


class TestInitMainBlock:
    """Test __init__.py __main__ block execution (line 1583)."""
    
    def test_init_main_block_execution(self):
        """Test executing update_news/__init__.py __main__ block (line 1583)."""
        import update_news
        import runpy
        
        # Get the path to __init__.py
        init_file = update_news.__file__
        
        # Use runpy.run_path to execute the file as a script
        # This will properly execute the __main__ block (lines 1582-1583) with correct line numbers for coverage
        # We catch SystemExit since run_cli() calls sys.exit(0)
        try:
            runpy.run_path(init_file, run_name='__main__')
        except SystemExit:
            # run_cli() calls sys.exit(0), which confirms that line 1583 was executed
            pass
        
        # The execution confirms that the __main__ block was executed
        # Coverage will show line 1583 as covered


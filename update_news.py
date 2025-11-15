#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backward compatibility wrapper for update_news module.
Allows execution via: python update_news.py
Also supports: python -m update_news
"""

from update_news import run_cli

if __name__ == "__main__":
    run_cli()

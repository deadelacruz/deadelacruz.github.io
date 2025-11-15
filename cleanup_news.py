#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cleanup script to remove articles that don't match the exact phrase in their title.
This script reads all news YAML files and removes articles that don't contain
the exact topic phrase in their title.

Usage:
    python cleanup_news.py
"""

import os
import sys
import yaml
from typing import Dict, List

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# File paths
CONFIG_FILE = "_data/news_config.yml"
DATA_DIR = "_data/news"

def article_matches_exact_phrase(article_title: str, exact_phrase: str) -> bool:
    """
    Check if article title contains the exact phrase (case-insensitive).
    Returns True if the exact phrase is found in the title.
    Uses the same logic as update_news.py for consistency.
    """
    title_lower = article_title.lower()
    phrase_lower = exact_phrase.lower()
    
    # Check if the exact phrase appears in the title
    if phrase_lower not in title_lower:
        return False
    
    # Additional validation: For multi-word phrases, ensure they appear together
    phrase_words = phrase_lower.split()
    if len(phrase_words) > 1:
        # Find the position of the first word
        first_word_pos = title_lower.find(phrase_words[0])
        if first_word_pos == -1:
            return False
        # Check if subsequent words appear in order after the first word
        current_pos = first_word_pos + len(phrase_words[0])
        for word in phrase_words[1:]:
            next_pos = title_lower.find(word, current_pos)
            if next_pos == -1:
                return False
            # Words should be close together (within reasonable distance)
            if next_pos - current_pos > 10:  # Allow some spacing for punctuation
                return False
            current_pos = next_pos + len(word)
    
    return True

def load_config() -> Dict:
    """Load configuration from YAML file."""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {CONFIG_FILE}")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading config: {e}")
        sys.exit(1)

def load_news_file(topic: str) -> List[Dict]:
    """Load news articles from YAML file."""
    file_path = os.path.join(DATA_DIR, f"{topic}.yml")
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
            return data.get('news_items', [])
    except FileNotFoundError:
        print(f"Warning: News file not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return []

def save_news_file(topic: str, articles: List[Dict]) -> bool:
    """Save news articles to YAML file."""
    file_path = os.path.join(DATA_DIR, f"{topic}.yml")
    try:
        data = {'news_items': articles}
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return True
    except Exception as e:
        print(f"Error saving {file_path}: {e}")
        return False

def cleanup_topic(topic: str, title_query: str) -> tuple[int, int]:
    """
    Clean up articles for a specific topic.
    Returns (articles_kept, articles_removed).
    """
    print(f"\n{'='*60}")
    print(f"Processing: {topic}")
    print(f"Looking for phrase: '{title_query}'")
    print(f"{'='*60}")
    
    # Load articles
    articles = load_news_file(topic)
    if not articles:
        print(f"No articles found in {topic}.yml")
        return 0, 0
    
    print(f"Loaded {len(articles)} articles")
    
    # Filter articles
    kept_articles = []
    removed_articles = []
    
    for article in articles:
        title = article.get('title', '')
        if not title:
            # Skip articles without titles
            removed_articles.append(article)
            continue
        
        if article_matches_exact_phrase(title, title_query):
            kept_articles.append(article)
        else:
            removed_articles.append(article)
            print(f"  ❌ Removing: {title[:60]}...")
    
    # Save cleaned articles
    if save_news_file(topic, kept_articles):
        print(f"\n✅ Saved {len(kept_articles)} articles to {topic}.yml")
    else:
        print(f"\n❌ Failed to save {topic}.yml")
        return 0, 0
    
    return len(kept_articles), len(removed_articles)

def main():
    """Main execution function."""
    print("="*60)
    print("News Articles Cleanup Script")
    print("="*60)
    print("This script will remove articles that don't contain")
    print("the exact topic phrase in their title.")
    print("="*60)
    
    # Load configuration
    config = load_config()
    news_sources = config.get('news_sources', {})
    
    if not news_sources:
        print("Error: No news sources configured in news_config.yml")
        sys.exit(1)
    
    # Process each topic
    total_kept = 0
    total_removed = 0
    
    for topic, topic_config in news_sources.items():
        title_query = topic_config.get('title_query', '')
        if not title_query:
            print(f"\n⚠️  Skipping {topic}: No title_query configured")
            continue
        
        kept, removed = cleanup_topic(topic, title_query)
        total_kept += kept
        total_removed += removed
    
    # Summary
    print("\n" + "="*60)
    print("CLEANUP SUMMARY")
    print("="*60)
    print(f"Articles kept:    {total_kept}")
    print(f"Articles removed: {total_removed}")
    print(f"Total processed:  {total_kept + total_removed}")
    print("="*60)
    
    if total_removed > 0:
        print(f"\n✅ Cleanup complete! Removed {total_removed} irrelevant articles.")
    else:
        print("\n✅ All articles are valid. No cleanup needed.")
    
    print("\nNote: You may want to commit these changes to your repository.")

if __name__ == "__main__":
    main()


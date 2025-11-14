# Why No Recent Articles (1 Hour Ago)? NewsAPI 24-Hour Delay

## The Problem

You see articles on Google News that are "1 hour ago", but they don't appear in your UI. This is because of **NewsAPI free tier's 24-hour delay**.

## NewsAPI Free Tier 24-Hour Delay

### The Limitation
- **NewsAPI free tier:** Articles from the last 24 hours are NOT available
- **Paid tier:** Can access articles immediately (no delay)
- This is a hard restriction - you cannot get articles less than 24 hours old with free tier

### Your Current Configuration
```yaml
date_range:
  exclude_today: true  # Excludes today
  exclude_today_offset_days: 1  # Excludes yesterday too
```

**This means:**
- Articles from today: ❌ Not available (24-hour delay)
- Articles from yesterday: ❌ Excluded by config
- Articles from 2+ days ago: ✅ Available

**So you're only getting articles from 2+ days ago, not recent ones!**

## Why Google News Shows Recent Articles

- Google News has direct access to news sources
- No API delay - they get articles immediately
- They have paid agreements with publishers
- You're using a free API with restrictions

## The Solution

### Option 1: Remove Yesterday Exclusion (Get More Recent Articles)
Change config to only exclude today:

```yaml
date_range:
  exclude_today: true  # Still exclude today (24-hour delay)
  exclude_today_offset_days: 0  # Don't exclude yesterday - get articles from yesterday!
```

**Result:**
- Articles from today: ❌ Still not available (NewsAPI 24-hour delay)
- Articles from yesterday: ✅ Now available!
- Articles from 2+ days ago: ✅ Available

**This gets you articles as recent as ~24-48 hours old** (best you can get with free tier)

### Option 2: Upgrade to Paid Plan (Get Articles Immediately)
- Paid plans have no 24-hour delay
- Can access articles immediately (1 hour ago, etc.)
- Cost: Starting around $449/month

### Option 3: Keep Current Setup
- Only get articles 2+ days old
- More stable (no edge cases with 24-hour delay)
- But miss recent articles

## Recommendation

**Change `exclude_today_offset_days` from `1` to `0`** to get articles from yesterday (the most recent you can get with free tier).

This will give you articles as recent as ~24-48 hours old, which is the best possible with NewsAPI free tier.


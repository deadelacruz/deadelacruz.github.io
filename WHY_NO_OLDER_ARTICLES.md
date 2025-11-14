# Why No Older Articles? NewsAPI Limitations Explained

## The Problem

When you run the script manually, it doesn't get articles older than ~30 days because of **NewsAPI free tier limitations**.

## NewsAPI Free Tier Limitations

### Date Range Limit
- **Free tier:** Only articles up to **1 month (30 days) old**
- **Paid tier:** Can access articles up to **1 year old** or more

### Your Current Configuration
```yaml
date_range:
  lookback_days: 30  # Maximum for free tier!
  exclude_today: true  # Excludes today (24-hour delay)
  exclude_today_offset_days: 1  # Excludes yesterday
```

**This means you're searching:**
- From: 30 days ago
- To: Yesterday (not today, due to 24-hour delay)
- **Total range: ~29 days** (maximum allowed for free tier)

## Why This Happens

1. **NewsAPI Free Tier Restriction:**
   - Free tier only provides articles from the last 30 days
   - This is a hard limit - you cannot access older articles with free tier

2. **Your Script is Already Optimized:**
   - `lookback_days: 30` is the maximum allowed
   - The script is already fetching as far back as possible

3. **24-Hour Delay:**
   - NewsAPI free tier has a 24-hour delay on today's articles
   - So you exclude today and yesterday to avoid errors

## Solutions

### Option 1: Increase Lookback (But Limited by Free Tier)
You can try increasing to 30 days (already at max), but NewsAPI will reject requests for older articles:

```yaml
date_range:
  lookback_days: 30  # Maximum for free tier
```

**Result:** Still only gets last 30 days (free tier limit)

### Option 2: Upgrade to Paid Plan (For Older Articles)
If you need articles older than 30 days:
- Upgrade to NewsAPI paid plan
- Paid plans allow access to articles up to 1 year old
- Cost: Starting around $449/month

### Option 3: Use Multiple Date Ranges (Within 30 Days)
You can fetch articles in smaller chunks to get better coverage:

```yaml
# Fetch last 7 days (most recent)
# Then fetch 7-14 days ago
# Then fetch 14-21 days ago
# Then fetch 21-30 days ago
```

This requires code changes to split the date range.

### Option 4: Keep Building Your Cache Over Time
- Run the script regularly (every 12 hours)
- Each run adds new articles to your cache
- Over time, you'll build up a collection of articles
- Articles are kept for `retention_days: 60` in your UI

## Current Behavior

### What Your Script Does:
1. Searches last 30 days (maximum for free tier)
2. Fetches articles from that period
3. Caches them for 60 days in your UI
4. Each run adds new articles to the cache

### What You're Seeing:
- Only articles from last 30 days
- No articles older than 30 days (NewsAPI free tier limit)
- This is expected behavior for free tier

## How to Maximize What You Get

### 1. Run Script More Frequently
- Run every 12 hours (when quota resets)
- Each run adds new articles
- Builds up your cache over time

### 2. Increase Retention Period
```yaml
date_range:
  retention_days: 90  # Keep articles for 90 days instead of 60
```

This keeps articles longer in your UI, even though you can only fetch last 30 days.

### 3. Use Early Stopping (Already Implemented)
- Gets more articles per API call
- More efficient use of your quota
- Better coverage within the 30-day window

## Summary

**Why no older articles?**
- NewsAPI free tier only allows last 30 days
- Your config is already at maximum (`lookback_days: 30`)
- This is a NewsAPI limitation, not a script issue

**What you can do:**
1. ✅ Keep current setup (already optimized)
2. ✅ Run script regularly to build cache
3. ✅ Increase retention_days to keep articles longer
4. 💰 Upgrade to paid plan for older articles (if needed)

**The script is working correctly** - it's fetching as far back as NewsAPI free tier allows!


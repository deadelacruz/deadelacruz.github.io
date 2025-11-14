# NewsAPI Optimization Strategies: Get More Reliable Articles Despite 429 Errors

## The Core Problem

**Every HTTP request = 1 API call**, regardless of results. You have limited calls (50 per 12 hours, 100 per 24 hours), so you need to maximize **article quality per API call**.

## Strategy 1: Smart Early Stopping (HIGHEST IMPACT)

### The Problem
Currently, you fetch up to 10 pages per topic even if you already have enough articles.

### The Solution
Stop pagination early when you have enough new, high-quality articles.

**Why This Works:**
- If page 1 gives you 20 great articles, why fetch 9 more pages?
- Each skipped page = 1 saved API call
- You can use those saved calls for other topics or future runs

**Implementation:**
- Set a target: "I need at least 10-15 new articles per topic"
- After each page, check: "Do I have enough new articles?"
- If yes, stop pagination and move to next topic
- This can reduce calls from 30 (3 topics × 10 pages) to 6-9 calls (3 topics × 2-3 pages)

---

## Strategy 2: Prioritize High-Value Topics

### The Problem
All topics are treated equally, but some might be more important.

### The Solution
Fetch the most important topics first, so if you hit rate limits, you at least have those.

**Why This Works:**
- If you only have 20 API calls left, use them for your top 2 topics
- Better to have 2 complete topics than 3 incomplete ones
- You can rotate priorities over time

**Implementation:**
- Add priority field to config (1 = highest, 3 = lowest)
- Sort topics by priority before processing
- Process high-priority topics first

---

## Strategy 3: Optimize Query Parameters for Better Results

### Current Setup
You're already using:
- ✅ Exact phrase matching (`"Deep Learning"`)
- ✅ Date range filtering
- ✅ Language filtering
- ✅ Maximum page size (100)

### Additional Optimizations

**A. Use `sortBy=relevancy` for first page, then `publishedAt`**
- First page: Get most relevant articles (better quality)
- Later pages: Get newest articles (more coverage)
- This ensures your first API call gives you the best articles

**B. Add `domains` parameter for trusted sources**
- Only fetch from reputable news sources
- Reduces noise, increases reliability
- Example: `domains=techcrunch.com,arstechnica.com,theverge.com`

**C. Use `excludeDomains` to filter out low-quality sources**
- Remove clickbait sites, aggregators, etc.
- Better signal-to-noise ratio

---

## Strategy 4: Graceful Degradation on 429 Errors

### The Problem
When you hit 429, you lose all progress and get nothing.

### The Solution
Use cached articles as fallback, and make partial progress.

**Why This Works:**
- If you fetch 2 topics successfully but hit 429 on the 3rd, you still have 2 topics updated
- Users see updated content even if one topic failed
- Better than showing nothing

**Current Behavior:**
- ✅ Your code already loads existing articles
- ✅ It merges new + existing articles
- ✅ It saves even if some topics fail

**Enhancement:**
- Add a "last successful fetch" timestamp
- If 429 occurs, show a message: "Using cached articles from [time]"
- This is transparent to users

---

## Strategy 5: Reduce Redundant Pagination

### The Problem
You might fetch 10 pages but only get 5 new articles (rest are duplicates).

### The Solution
Track what you've already fetched and stop when you're getting mostly duplicates.

**Why This Works:**
- If page 3 has 90% duplicates, pages 4-10 will likely be worse
- Stop early and save API calls
- Use those calls for other topics

**Implementation:**
- After each page, calculate: `new_articles / total_articles_in_page`
- If ratio drops below 30% (70% duplicates), consider stopping
- This is especially useful if you run frequently (every 12 hours)

---

## Strategy 6: Batch Date Ranges (Advanced)

### The Problem
Fetching 30 days at once might return too many old articles mixed with new ones.

### The Solution
Split into smaller date ranges and prioritize recent articles.

**Why This Works:**
- First API call: Last 7 days (most relevant)
- If you need more: Next 7 days (still recent)
- Only fetch older articles if you have quota left
- This ensures you always get the newest articles first

**Trade-off:**
- More API calls (one per date range)
- But better article quality and recency
- Only use if you have quota to spare

---

## Strategy 7: Use NewsAPI's "Top Headlines" for Breaking News

### The Problem
"Everything" endpoint is expensive and might miss breaking news.

### The Solution
Use "Top Headlines" endpoint for recent news (last 24 hours).

**Why This Works:**
- "Top Headlines" is faster and often more reliable
- Better for breaking news and trending topics
- Can complement your "Everything" searches

**Limitation:**
- Only works for recent news (last 24 hours)
- Less historical coverage
- Use as supplement, not replacement

---

## Recommended Configuration Changes

### Priority 1: Implement Early Stopping
```yaml
api:
  min_articles_per_topic: 10  # Stop pagination when you have this many new articles
  max_pages: 10  # Keep as fallback maximum
  early_stop_duplicate_threshold: 0.7  # Stop if 70%+ are duplicates
```

### Priority 2: Add Topic Priorities
```yaml
news_sources:
  deep-learning:
    name: "Deep Learning"
    title_query: "Deep Learning"
    priority: 1  # Highest priority
    max_pages: 5  # Fewer pages, but guaranteed to complete
  
  machine-learning:
    name: "Machine Learning"
    title_query: "Machine Learning"
    priority: 2  # Medium priority
    max_pages: 5
  
  artificial-intelligence:
    name: "Artificial Intelligence"
    title_query: "Artificial Intelligence"
    priority: 3  # Lower priority (can be skipped if quota low)
    max_pages: 3
```

### Priority 3: Optimize Query Quality
```yaml
api:
  sort_by: "relevancy"  # First page: most relevant
  sort_by_pagination: "publishedAt"  # Later pages: newest first
  trusted_domains: ["techcrunch.com", "arstechnica.com", "theverge.com"]
  exclude_domains: ["example-low-quality.com"]
```

---

## Expected Impact

### Current Setup
- 3 topics × 10 pages = 30 API calls
- Risk: Hit rate limit, get nothing
- Result: All or nothing

### With Optimizations
- 3 topics × 2-3 pages (early stopping) = 6-9 API calls
- Risk: Low (plenty of buffer)
- Result: Guaranteed to complete all topics
- Bonus: 20-25 API calls saved for future runs or retries

### Quality Improvement
- Better articles (relevancy sorting, trusted sources)
- More reliable (graceful degradation)
- More efficient (early stopping, prioritization)

---

## Implementation Priority

1. **Early Stopping** (Easiest, Highest Impact) - Saves 60-70% of API calls
2. **Topic Prioritization** (Easy, High Value) - Ensures important topics always complete
3. **Query Optimization** (Medium, Quality Boost) - Better articles per call
4. **Graceful Degradation** (Already mostly done) - Just needs better messaging
5. **Advanced Strategies** (Complex, Marginal Gains) - Only if needed

---

## Bottom Line

**The best strategy: Make fewer, smarter API calls that give you better results.**

Instead of:
- 30 API calls → Maybe get articles, maybe hit 429

Do this:
- 6-9 API calls → Guaranteed to get articles, plenty of buffer
- Better article quality per call
- More reliable system

**You'll get MORE reliable articles with FEWER API calls!**


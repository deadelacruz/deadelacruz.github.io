# Dynamic World News Update System

This system allows your Jekyll site to automatically display the latest **verified, legitimate news** from trusted sources around the world. The system fetches news from only verified news organizations to ensure authenticity and prevent fake news.

## Trusted News Sources

The system only fetches news from verified, legitimate news organizations including:
- Reuters
- BBC
- Associated Press (AP News)
- The Guardian
- The New York Times
- The Washington Post
- NPR
- The Wall Street Journal
- Bloomberg
- CNN
- ABC News
- CBS News
- USA Today
- Time Magazine
- MIT News
- Nature
- Science Magazine

**All articles are verified to come from these trusted sources only - no fake news!**

## Available News Categories

1. **Deep Learning** - Latest developments in deep learning
2. **Machine Learning** - Machine learning breakthroughs and innovations
3. **Artificial Intelligence** - AI policy, industry news, and updates
4. **Technology** - General technology news
5. **Science** - Scientific discoveries and research
6. **Business** - Business and finance news
7. **Health** - Health and medical news

## How It Works

1. **Data Files**: News items are stored in `_data/news/` as YAML files:
   - `deep-learning.yml`
   - `machine-learning.yml`
   - `artificial-intelligence.yml`
   - `technology.yml`
   - `science.yml`
   - `business.yml`
   - `health.yml`

2. **Dynamic Display**: The markdown pages use the `news_items.html` include template to dynamically display news from the data files.

3. **Auto-Update Script**: The `update_news.py` script automatically fetches news from verified sources and updates the data files. **Only articles from trusted sources are included.**

## Setup

### Option 1: Manual Updates
Simply edit the YAML files in `_data/news/` to add or update news items.

### Option 2: Automatic Updates with NewsAPI

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Get a NewsAPI key** (free tier available):
   - Sign up at https://newsapi.org/
   - Get your API key

3. **Set environment variable**:
   ```bash
   # Windows PowerShell
   $env:NEWSAPI_KEY="your-api-key-here"
   
   # Linux/Mac
   export NEWSAPI_KEY="your-api-key-here"
   ```

4. **Run the update script**:
   ```bash
   python update_news.py
   ```

### Option 3: Schedule Automatic Updates

#### Windows (Task Scheduler)
1. Open Task Scheduler
2. Create Basic Task
3. Set trigger (e.g., daily at 9 AM)
4. Action: Start a program
5. Program: `python`
6. Arguments: `C:\path\to\update_news.py`
7. Start in: `C:\path\to\your\site`

#### Linux/Mac (Cron)
Add to crontab (`crontab -e`):
```bash
# Update news daily at 9 AM
0 9 * * * cd /path/to/your/site && /usr/bin/python3 update_news.py >> /tmp/news_update.log 2>&1
```

## Customizing News Sources

Edit `update_news.py` to:
- Add more news sources
- Integrate with different APIs
- Add web scraping for specific sites
- Filter news by keywords or date ranges

## News Item Format

Each news item in the YAML files follows this structure:

```yaml
news_items:
  - title: "News Title"
    description: "Brief description of the news"
    url: "https://example.com/article"
    date: "2025-11-05"
    source: "Reuters"  # Source publication name
```

## Verification System

The update script includes a verification system that:
- ✅ Checks all article URLs against a whitelist of trusted sources
- ✅ Only includes articles from verified news organizations
- ✅ Filters out any articles from unknown or untrusted sources
- ✅ Displays the source publication name for transparency

**This ensures that only legitimate, verified news articles are displayed on your site.**

## Notes

- The script preserves existing news if no new items are found
- News items are sorted by date (newest first)
- The system works even without the update script - you can manually edit YAML files
- Jekyll will automatically rebuild the site when data files change


# David Edward Dela Cruz – Portfolio Website

A modern developer portfolio powered by **Jekyll** on the frontend and a fully tested **Python news automation** pipeline on the backend.  
It ships with a dynamic news system, blog, gallery, and deployment tooling that makes it easy to keep content fresh.

---

## 🚀 Tech Stack

| Layer      | Tools |
|-----------|-------|
| **Frontend** | HTML5, Sass/CSS3, JavaScript, jQuery, Bootstrap, Font Awesome, Google Fonts |
| **Site Engine** | Jekyll 4.3.3 |
| **Automation** | Python 3.11+, NewsAPI, YAML data files |
| **Code Quality** | Pre-commit hooks, Black (code formatter), isort (import sorter), pytest (testing) |
| **Tooling & Deploy** | GitHub Pages, GitHub Actions, Netlify/Vercel/Firebase (optional), Docker |

---

## 📰 Dynamic News System

- Pulls fresh AI/ML news from **100+ trusted outlets** (Reuters, MIT Tech Review, Nature, IEEE, etc.).  
- Topics are defined in `_data/news_config.yml` (Deep Learning, Machine Learning, Artificial Intelligence by default).  
- **Exact phrase matching**: Searches for exact phrases only in article **titles** (e.g., "Deep Learning", "Machine Learning", "Artificial Intelligence") - case-insensitive, using NewsAPI's `qInTitle` parameter. This ensures only relevant articles are returned directly from the API, eliminating the need for post-processing filtering of content-only matches.  
- Articles are fetched with `update_news.py`, validated by exact phrase matching (using strict word-boundary regex), deduplicated, stored under `_data/news/*.yml`, and rendered by the Jekyll UI.  
- **Combined request mode** (enabled by default): Fetches all topics in a single API call using `qInTitle` parameter with OR operator (e.g., `"Deep Learning" OR "Machine Learning" OR "Artificial Intelligence"`), reducing API calls from N to 1. Uses NewsAPI's `qInTitle` parameter which searches only in article titles, efficiently returning only relevant articles directly from the API without post-processing filtering. Articles are automatically routed to the correct topic files based on which phrase they match.  
- **Early stopping optimization**: Stops pagination early when enough articles are found or when duplicate threshold is reached, optimizing API usage.  
- **Dynamic error handling**: Automatically detects and handles rate limit errors and result limit errors (free tier: 100 results max per query), gracefully stopping pagination while preserving available results.  
- **Rate limiting & API tracking**: Tracks total API calls (default: max 45 per run), adds delays between topics/pages, and preserves existing articles if rate limits are hit.  
- **Reader-friendly pagination**: The UI shows 10 articles per page by default (configurable via `_data/news_config.yml → ui.articles_per_page`) and provides Previous/Next controls that automatically scroll the reader back to the start of the news section when navigating between pages.  
- Comprehensive logging, metrics (`_data/news_metrics.json`), and JSON/YAML outputs ensure transparency.

### How Fetching Works
1. **Config** → `_data/news_config.yml` defines API settings, exact phrase queries (`title_query`), rate limiting, combined request mode, and output paths.  
2. **CLI Wrapper** → `python -m update_news` (or `python update_news.py`) calls `run_cli()` which handles success/error exit codes.  
3. **Request Mode** → 
   - **Combined mode** (default): Fetches all topics in 1 API call using `qInTitle` parameter with OR operator (e.g., `"Deep Learning" OR "Machine Learning" OR "Artificial Intelligence"`), limited to 1 page (100 results max total). Returns only title matches directly from API, eliminating post-processing filtering. Articles automatically routed to topics.
   - **Separate mode**: Fetches each topic individually using `qInTitle` parameter (single phrase per request) with pagination support (up to 5 pages per topic, 500 articles max per topic), with delays between topics.
4. **Rate Limiting** → Tracks API calls (default: max 45 per run), adds delays between topics/pages, dynamically detects rate limit errors, and preserves cached articles if limits are hit.  
5. **Early Stopping** → Stops pagination when enough articles are found (default: 10) or when duplicate threshold is reached (default: 70%).  
6. **Metrics** → Execution stats are exported automatically to `_data/news_metrics.json` and can be consumed by dashboards or CI.

---

## 🛠️ Local Development

### Prerequisites
- Ruby ≥ 3.0 & Bundler ≥ 2.7  
- Python 3.11+ (3.11 recommended, 3.10+ supported)  
- Git

### Install & Run
```bash
git clone https://github.com/deadelacruz/deadelacruz.github.io.git
cd deadelacruz.github.io

# Jekyll deps
gem install jekyll bundler
bundle install

# Python deps for automation + tests
pip install -r requirements.txt

# (Optional) Set up pre-commit hooks for code formatting
pre-commit install

# Serve site
bundle exec jekyll serve --livereload
# http://localhost:4000
```

### Configure & Fetch News
```bash
# 1. Sign up at https://newsapi.org/ and grab an API key
# 2. Export the key
export NEWSAPI_KEY="your-api-key"        # Linux / macOS
# PowerShell: $env:NEWSAPI_KEY="your-api-key"

# 3. (Optional) Customize news_config.yml
#    - Adjust exact phrase queries (title_query)
#    - Configure rate limiting (max_api_calls, topic_delay_seconds)
#    - Enable/disable combined request mode (combine_topics_in_single_request)
#    - Configure early stopping (min_articles_per_topic, early_stop_duplicate_threshold)
#    - Adjust pagination (max_pages, max_page_size, ui.articles_per_page)

# 4. Update all topics
python update_news.py
# or just rely on the CLI wrapper
python -m update_news
```
Data lands in `_data/news/<topic>.yml`. Rebuild the Jekyll site to see the cards update.

**Note**: The script automatically handles NewsAPI rate limits (50 requests per 12 hours for free tier) by:
- **Combined request mode** (default): Uses 1 API call for all topics using `qInTitle` parameter with OR operator, reducing rate limit risk and returning only relevant title matches directly from API
- Tracking total API calls and stopping before hitting the limit (default: 45 calls max)
- Adding delays between topics/pages (default: 2 seconds between topics, 1 second between pages)
- Dynamically detecting rate limit errors and preserving existing articles if limits are hit
- Handling result limit errors (free tier: 100 results max per query) gracefully
- Early stopping optimization to minimize API usage

---

## 🧪 Testing & Quality

The repo ships with a comprehensive pytest suite covering configuration parsing, exact phrase matching, metrics tracking, API integration, rate limiting, result limit handling, combined requests, file I/O, date calculations, and the CLI wrapper.

```bash
# Install requirements first
pip install -r requirements.txt

# Run everything
pytest

# With coverage (html report written to htmlcov/)
pytest --cov=update_news --cov-report=term-missing --cov-report=html
```

Test files:
- `test_config_loading.py` - Configuration loading and parsing
- `test_keyword_processing.py` - Exact phrase matching logic
- `test_article_processing.py` - Article filtering and processing
- `test_fetch_news.py` - News fetching logic
- `test_api_requests.py` - API request handling
- `test_result_limit_and_combined.py` - Result limits and combined request mode
- `test_metrics_tracker.py` - Metrics tracking
- `test_file_operations.py` - File I/O operations
- `test_date_calculation.py` - Date range calculations
- `test_coverage_complete.py` - Coverage completeness checks

### Code Formatting

The project uses **pre-commit hooks** to ensure consistent code formatting. Hooks run automatically on `git commit` and format code using **Black** and **isort**.

```bash
# Install pre-commit hooks (one-time setup)
pre-commit install

# Run hooks manually on all files
pre-commit run --all-files

# Run hooks on staged files only
pre-commit run
```

The hooks will:
- Format Python code with **Black** (100 character line length)
- Sort imports with **isort** (configured to work with Black)
- Check for trailing whitespace, YAML/JSON validity, and other common issues

Configuration is in `.pre-commit-config.yaml`. To skip hooks for a commit, use `git commit --no-verify` (not recommended).

---

## 📦 Deployment

- **GitHub Pages** (default) – build via GitHub Actions.  
- **Other hosts** – the generated `_site` folder works out of the box on Netlify, Vercel, Firebase Hosting, etc.  
- **Automation** – GitHub Actions workflow runs `python update_news.py` every 12 hours (aligned with NewsAPI quota reset cycle).  
  - Workflow file: `.github/workflows/update-news.yml`  
  - Runs at 00:00 and 12:00 UTC (8:00 AM and 8:00 PM Philippine Time)  
  - Requires `NEWSAPI_KEY` secret in repository settings  
  - Uses Python 3.11  
  - Automatically commits and pushes updated news files  
  - Handles merge conflicts gracefully, preserving news updates

---

## ✨ Features

- Responsive, SEO-optimized portfolio + blog  
- Dynamic news widgets per topic  
- Gallery + project showcase  
- Dark/light theme toggle  
- RSS feed & social sharing  
- **News System Features:**
  - **Exact phrase matching** (case-insensitive) in article titles only for precise filtering
  - **Combined request mode** (default): Fetches all topics in 1 API call using `qInTitle` parameter with OR operator, reducing API usage from N to 1 and returning only title matches (no post-processing filtering needed)
  - **Early stopping optimization**: Stops pagination when enough articles found or duplicate threshold reached
  - **Dynamic error handling**: Automatically detects and handles rate limit and result limit errors
  - **Rate limiting**: API call tracking (max 45 per run), delays between topics/pages, preserves cached articles
  - **Article routing**: In combined mode, articles automatically routed to correct topic files
  - **Article deduplication** and retention period filtering (default: 90 days)
  - **Comprehensive logging** & metrics (`_data/news_metrics.json`) with per-topic statistics
  - **Python CLI entry point** with graceful error handling and exit codes
  - **GitHub Actions automation** (runs every 12 hours, aligned with NewsAPI quota reset)

---

## 👤 Author

**David Edward Dela Cruz**  
- Site: [deadelacruz.github.io](https://deadelacruz.github.io)  
- Email: david22edward@gmail.com  
- GitHub: [@deadelacruz](https://github.com/deadelacruz)

---

## 📄 License

MIT License

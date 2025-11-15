# David Edward Dela Cruz – Portfolio Website

A modern developer portfolio powered by **Jekyll** on the frontend and a fully tested **Python news automation** pipeline on the backend.  
It ships with a dynamic news system, blog, gallery, and deployment tooling that makes it easy to keep content fresh.

---

## 🚀 Tech Stack

| Layer      | Tools |
|-----------|-------|
| **Frontend** | HTML5, Sass/CSS3, JavaScript, jQuery, Bootstrap, Font Awesome, Google Fonts |
| **Site Engine** | Jekyll 4.3.x |
| **Automation** | Python 3, NewsAPI, YAML data files |
| **Tooling & Deploy** | GitHub Pages, GitHub Actions, Netlify/Vercel/Firebase (optional), Docker |

---

## 📰 Dynamic News System

- Pulls fresh AI/ML news from **100+ trusted outlets** (Reuters, MIT Tech Review, Nature, IEEE, etc.).  
- Topics are defined in `_data/news_config.yml` (Deep Learning, Machine Learning, Artificial Intelligence by default).  
- **Exact phrase matching**: Searches for exact phrases only (e.g., "Deep Learning", "Machine Learning", "Artificial Intelligence") - case-insensitive.  
- Articles are fetched with `update_news.py`, filtered by exact phrase matching, deduplicated, stored under `_data/news/*.yml`, and rendered by the Jekyll UI.  
- **Rate limiting & retry logic**: Automatic retry with exponential backoff for rate limit errors (detected dynamically), API call tracking to prevent hitting limits, and delays between topics.  
- Comprehensive logging, metrics (`_data/news_metrics.json`), and JSON/YAML outputs ensure transparency.

### How Fetching Works
1. **Config** → `_data/news_config.yml` defines API settings, exact phrase queries, rate limiting, and output paths.  
2. **CLI Wrapper** → `python -m update_news` (or `python update_news.py`) calls `run_cli()` which handles success/error exit codes.  
3. **Rate Limiting** → Tracks API calls (default: max 45 per run), adds delays between topics, and retries with exponential backoff on rate limit errors (detected dynamically).  
4. **Metrics** → Execution stats are exported automatically and can be consumed by dashboards or CI.

---

## 🛠️ Local Development

### Prerequisites
- Ruby ≥ 3.0 & Bundler ≥ 2.7  
- Python 3.10+  
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
#    - Set retry behavior (max_retries, retry_base_delay_seconds)

# 4. Update all topics
python update_news.py
# or just rely on the CLI wrapper
python -m update_news
```
Data lands in `_data/news/<topic>.yml`. Rebuild the Jekyll site to see the cards update.

**Note**: The script automatically handles NewsAPI rate limits (50 requests per 12 hours for free tier) by:
- Tracking total API calls and stopping before hitting the limit (default: 45 calls max)
- Adding delays between topics (default: 2 seconds)
- Retrying with exponential backoff on rate limit errors (detected dynamically, up to 3 retries)
- Preserving existing articles if rate limits are hit

---

## 🧪 Testing & Quality

The repo ships with a full pytest suite (100% coverage) covering configuration parsing, exact phrase matching, metrics tracking, API integration, rate limiting, file I/O, and the CLI wrapper.

```bash
# Install requirements first
pip install -r requirements.txt

# Run everything
pytest

# With coverage (html report written to htmlcov/)
pytest --cov=update_news --cov-report=term-missing --cov-report=html
```

See [`README_TESTING.md`](README_TESTING.md) for detailed guidance on structuring new tests and integrating them into CI.

---

## 📦 Deployment

- **GitHub Pages** (default) – build via GitHub Actions.  
- **Other hosts** – the generated `_site` folder works out of the box on Netlify, Vercel, Firebase Hosting, etc.  
- **Automation** – GitHub Actions workflow runs `python update_news.py` every 12 hours (aligned with NewsAPI quota reset cycle).  
  - Workflow file: `.github/workflows/update-news.yml`  
  - Requires `NEWSAPI_KEY` secret in repository settings  
  - Automatically commits and pushes updated news files

---

## ✨ Features

- Responsive, SEO-optimized portfolio + blog  
- Dynamic news widgets per topic  
- Gallery + project showcase  
- Dark/light theme toggle  
- RSS feed & social sharing  
- **News System Features:**
  - Exact phrase matching (case-insensitive) for precise article filtering
  - Rate limiting with API call tracking to prevent quota exhaustion
  - Automatic retry with exponential backoff on rate limit errors
  - Delays between topics to respect API limits
  - Article deduplication and retention period filtering
  - Comprehensive logging & metrics (`_data/news_metrics.json`)
  - Python CLI entry point with graceful error handling
  - GitHub Actions automation (runs every 12 hours)

---

## 👤 Author

**David Edward Dela Cruz**  
- Site: [deadelacruz.github.io](https://deadelacruz.github.io)  
- Email: david22edward@gmail.com  
- GitHub: [@deadelacruz](https://github.com/deadelacruz)

---

## 📄 License

MIT License

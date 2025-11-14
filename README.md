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
- Articles are fetched with `update_news.py`, filtered by keywords, deduplicated, stored under `_data/news/*.yml`, and rendered by the Jekyll UI.  
- Comprehensive logging, metrics (`_data/news_metrics.json`), and JSON/YAML outputs ensure transparency.

### How Fetching Works
1. **Config** → `_data/news_config.yml` defines API settings, keywords, and output paths.  
2. **CLI Wrapper** → `python -m update_news` (or `python update_news.py`) calls `run_cli()` which handles success/error exit codes.  
3. **Metrics** → Execution stats are exported automatically and can be consumed by dashboards or CI.

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

# 3. Update all topics
python update_news.py
# or just rely on the CLI wrapper
python -m update_news
```
Data lands in `_data/news/<topic>.yml`. Rebuild the Jekyll site to see the cards update.

---

## 🧪 Testing & Quality

The repo ships with a full pytest suite (100% coverage) covering configuration parsing, keyword normalization, metrics tracking, API integration, file I/O, and the CLI wrapper.

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
- **Automation** – schedule `python update_news.py` (GitHub Action, cron, or serverless job) to keep feeds current.

---

## ✨ Features

- Responsive, SEO-optimized portfolio + blog  
- Dynamic news widgets per topic  
- Gallery + project showcase  
- Dark/light theme toggle  
- RSS feed & social sharing  
- Extensive logging & metrics for the news updater  
- Python CLI entry point with graceful error handling

---

## 👤 Author

**David Edward Dela Cruz**  
- Site: [deadelacruz.github.io](https://deadelacruz.github.io)  
- Email: david22edward@gmail.com  
- GitHub: [@deadelacruz](https://github.com/deadelacruz)

---

## 📄 License

MIT License

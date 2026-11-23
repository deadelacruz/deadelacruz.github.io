# David Edward Dela Cruz - Portfolio Website
A modern developer portfolio powered by **Jekyll** on the frontend and a fully tested **Python news automation** pipeline on the backend.  
It ships with a dynamic news system, blog, gallery, and deployment tooling that makes it easy to keep content fresh.

---

## Tech Stack
| Layer      | Tools |
|-----------|-------|
| **Frontend** | HTML5, Sass/CSS3, JavaScript, jQuery, Bootstrap, Font Awesome, Google Fonts |
| **Site Engine** | Jekyll 4.3.3 |
| **Automation** | Python 3.11+, GDELT DOC API, YAML data files |
| **Code Quality** | Pre-commit hooks, Black (code formatter), isort (import sorter), pytest (testing) |
| **Tooling & Deploy** | GitHub Pages, GitHub Actions, Netlify/Vercel/Firebase (optional), Docker |

---

## Dynamic News System
- Pulls recent AI/ML coverage indexed by GDELT from global news sources.
- Topics are defined in `_data/news_config.yml` (Deep Learning, Machine Learning, Artificial Intelligence by default).  
- **No API key required**: GDELT searches the latest 24 hours, with the workflow scheduled every six hours.
- Articles are fetched with `update_news.py`, deduplicated, stored under `_data/news/*.yml`, and rendered by the Jekyll UI.
- **Graceful failures**: Cached articles are preserved when the source is temporarily unavailable.
- **Reader-friendly pagination**: The UI shows 10 articles per page by default (configurable via `_data/news_config.yml -> ui.articles_per_page`) and provides Previous/Next controls that automatically scroll the reader back to the start of the news section when navigating between pages.  
- Comprehensive logging, metrics (`_data/news_metrics.json`), and JSON/YAML outputs ensure transparency.

### How Fetching Works
1. **Config** -> `_data/news_config.yml` defines the GDELT source, phrase queries (`title_query`), request spacing, retention, and output paths.
2. **CLI Wrapper** -> `python -m update_news` (or `python update_news.py`) calls `run_cli()` which handles success/error exit codes.  
3. **Fetch** -> Makes one full-text query per topic for the previous 24 hours, spacing requests to stay below the public endpoint's rate.
4. **Save** -> New headlines are deduplicated, merged with retained results, and written to topic YAML files.
5. **Metrics** -> Execution stats are exported automatically to `_data/news_metrics.json` and can be consumed by dashboards or CI.

---

## Local Development
### Prerequisites
- Ruby >= 3.0 & Bundler >= 2.7  
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
# Update all topics; the default GDELT source needs no API key.
python update_news.py
# or just rely on the CLI wrapper
python -m update_news
```
Data lands in `_data/news/<topic>.yml`. Rebuild the Jekyll site to see the cards update.

NewsAPI remains as an optional legacy provider for local development. Its free Developer plan delays search articles by 24 hours and is restricted to development and testing, so the published site uses GDELT instead.

---

## Testing and Quality
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

## Deployment
- **GitHub Pages** (default) - build via GitHub Actions.  
- **Other hosts** - the generated `_site` folder works out of the box on Netlify, Vercel, Firebase Hosting, etc.  
- **Automation** - GitHub Actions workflow runs `python -m update_news` every six hours.
  - Workflow file: `.github/workflows/update-news.yml`  
  - Runs at 17 minutes past 00:00, 06:00, 12:00, and 18:00 UTC
  - Uses the keyless GDELT DOC API; no repository secret is required
  - Uses Python 3.11  
  - Automatically commits and pushes updated news files  
  - Handles merge conflicts gracefully, preserving news updates

### Local Windows Scheduler (No GitHub Actions Billing)

If GitHub Actions is unavailable on your account, you can run the same update flow locally using Windows Task Scheduler.

Requirements:
- Git installed and available on PATH
- Python installed
- This repository cloned with git (must contain a `.git` folder)

Setup command (from repo root):

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup-local-news-task.ps1
# Optional for logged-out runs (can be less reliable for git credentialed pushes on some machines):
# powershell -ExecutionPolicy Bypass -File .\scripts\setup-local-news-task.ps1 -UseS4U
```

What setup does:
- Creates/updates `.venv`
- Installs dependencies from `requirements.txt`
- Registers scheduled task `UpdateNewsEvery12HoursLocal`
- Runs at `08:00` and `20:00` local machine time
- Writes logs to `logs/news-update.log`

Manual run once:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-news-update.ps1
```

Remove scheduled task:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\remove-local-news-task.ps1
```

Notes:
- The runner only commits `_data/news/*` and `_data/news_last_updated.yml`.
- If you have other uncommitted changes, it safely skips the run to avoid interfering with your work.

---

## Features
- Responsive, SEO-optimized portfolio + blog  
- Dynamic news widgets per topic  
- Gallery + project showcase  
- Dark/light theme toggle  
- RSS feed & social sharing  
- **News System Features:**
  - **GDELT full-text topic search** with no API key requirement
  - **Frequent automation**: GitHub Actions checks for news every six hours
  - **Rate limiting**: Spaces topic requests and preserves cached articles on source errors
  - **Article deduplication** and retention period filtering (default: 90 days)
  - **Comprehensive logging** & metrics (`_data/news_metrics.json`) with per-topic statistics
  - **Python CLI entry point** with graceful error handling and exit codes
  - **GitHub Actions automation** (runs every six hours)

---

## Author
**David Edward Dela Cruz**  
- Site: [deadelacruz.github.io](https://deadelacruz.github.io)  
- Email: david22edward@gmail.com  
- GitHub: [@deadelacruz](https://github.com/deadelacruz)

---

## License
MIT License


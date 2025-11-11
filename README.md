# David Edward Dela Cruz - Portfolio Website

A modern portfolio website built with Jekyll, featuring dynamic news updates from verified sources, blog functionality, and a beautiful developer-focused design.

## 🚀 Tech Stack

**Backend:**
- Jekyll 4.3.3 (Ruby-based static site generator)
- Python 3 (for news automation)

**Frontend:**
- HTML5, CSS3/Sass, JavaScript
- jQuery, Bootstrap
- Font Awesome, Google Fonts

**Tools & Deployment:**
- Docker, GitHub Actions
- GitHub Pages, Netlify, Firebase, Vercel

## 📰 Dynamic News System

Automatically displays the latest **verified news** from **100+ trusted sources** including:
- Mainstream: Reuters, BBC, AP, The Guardian, NY Times, etc.
- Academic: MIT, Stanford, Harvard, and 26+ top universities
- Science: Nature, Science Magazine, Scientific American, etc.
- Technology: TechCrunch, Wired, The Verge, IEEE, etc.
- International: Al Jazeera, Financial Times, The Economist, etc.
- Business, Health, AI/ML, Developer publications, and more

**News Categories:** Deep Learning, Machine Learning, AI, Technology, Science, Business, Health

**Verification:** All articles are verified against a whitelist of trusted sources - no fake news!

## 🛠️ Quick Setup

### Prerequisites
- Ruby >= 3.0
- Bundler >= 2.7.2
- Python 3
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/deadelacruz/deadelacruz.github.io.git
cd deadelacruz.github.io

# Install Ruby dependencies
gem install jekyll bundler
bundle install

# Install Python dependencies (for news updates)
pip install -r requirements.txt

# Run development server
bundle exec jekyll serve --livereload
```

Visit `http://localhost:4000`

### News Updates

**Manual:** Edit YAML files in `_data/news/`

**Automatic with NewsAPI:**
1. Get API key from https://newsapi.org/
2. Set environment variable:
   ```bash
   # Windows PowerShell
   $env:NEWSAPI_KEY="your-api-key"
   
   # Linux/Mac
   export NEWSAPI_KEY="your-api-key"
   ```
3. Run: `python update_news.py`

## 🚀 Deployment

**GitHub Pages:** Automatically deployed via GitHub Actions

**Other Options:** Netlify, Firebase, Vercel

## 📚 Key Features

- ✅ Responsive design
- ✅ SEO optimized
- ✅ Blog with categories/tags
- ✅ Dynamic news from 100+ verified sources
- ✅ Gallery, portfolio showcase
- ✅ Dark/Light mode
- ✅ RSS feed, social sharing

## 👤 Author

**David Edward Dela Cruz**
- Website: [deadelacruz.github.io](https://deadelacruz.github.io)
- Email: david22edward@gmail.com
- GitHub: [@deadelacruz](https://github.com/deadelacruz)

## 📄 License

MIT License

# News Story Analyzer 📰

A web-based news crawling and analysis tool that fetches news articles from Google News, creates AI-powered summaries, and visualizes story timelines. Perfect for tracking news stories, understanding coverage patterns, and getting quick insights into current events.

## Features

✨ **Key Capabilities:**
- 🔍 Search news articles by keyword from Google News
- 📊 Interactive timeline visualization showing coverage over time
- 🤖 AI-powered article summaries
- 📈 Coverage statistics (article count, sources, date range)
- 🌐 Modern web interface - no technical knowledge required
- 📱 Responsive design for desktop and mobile

## Screenshot

The application provides:
- Clean search interface with customizable parameters
- Story overview with key topics and statistics
- Interactive Plotly timeline chart
- Detailed article listings with summaries

## Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## Installation

### 1. Clone or Download the Project

Download this project to your local machine.

### 2. Create a Virtual Environment (Recommended)

**On Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

This will install:
- Flask (web framework)
- gnews (Google News scraper)
- beautifulsoup4 (HTML parsing)
- newspaper3k (article extraction)
- plotly (data visualization)
- And other required packages

### 4. Configuration (Optional)

Edit `config.py` to customize settings:

```python
MAX_ARTICLES = 20          # Maximum articles to fetch
DEFAULT_LANGUAGE = 'en'    # Language code
DEFAULT_COUNTRY = 'US'     # Country code
```

## Usage

### Starting the Application

1. **Activate your virtual environment** (if not already activated)

2. **Run the Flask application:**

```powershell
python app.py
```

3. **Open your browser** and navigate to:
```
http://localhost:5000
```

### Using the Web Interface

1. **Enter a keyword** - Type any news topic (e.g., "climate change", "artificial intelligence")

2. **Choose parameters:**
   - **Days to Look Back**: How far back to search (7-90 days)
   - **Max Articles**: Number of articles to fetch (10-50)

3. **Click "Search News"** - The app will:
   - Fetch articles from Google News
   - Generate summaries and extract key topics
   - Create a timeline visualization
   - Display all results on the page

4. **Explore results:**
   - View the story overview and key topics
   - Analyze the timeline chart
   - Read individual article summaries
   - Click article links to read full stories

## Project Structure

```
project/
│
├── app.py                 # Flask web application (main entry point)
├── config.py              # Configuration settings
├── news_crawler.py        # Google News crawler module
├── summarizer.py          # Text summarization module
├── timeline.py            # Timeline generation module
├── requirements.txt       # Python dependencies
├── .gitignore            # Git ignore file
│
├── templates/            # HTML templates
│   ├── index.html        # Main search page
│   └── 404.html          # Error page
│
└── static/               # Static files
    ├── css/
    │   └── style.css     # Stylesheet
    └── js/
        └── main.js       # JavaScript logic
```

## How It Works

### 1. News Crawling
- Uses the `gnews` library to search Google News
- Filters articles from mainstream western news sources
- Extracts full article text using `newspaper3k`

### 2. Summarization
- Implements extractive summarization
- Scores sentences based on word frequency
- Identifies key topics across multiple articles

### 3. Timeline Generation
- Groups articles by publication date
- Creates interactive Plotly visualizations
- Shows coverage intensity over time

### 4. Web Interface
- Flask serves the HTML/CSS/JS frontend
- AJAX requests for real-time updates
- Responsive design for all devices

## Troubleshooting

### Common Issues

**1. Import errors or module not found:**
```powershell
# Make sure virtual environment is activated
.\venv\Scripts\Activate.ps1

# Reinstall dependencies
pip install -r requirements.txt
```

**2. No articles found:**
- Try different keywords
- Extend the date range
- Check your internet connection

**3. Port 5000 already in use:**
Edit `app.py` and change the port:
```python
app.run(host='0.0.0.0', port=5001)
```

**4. Slow article fetching:**
- Reduce `MAX_ARTICLES` in config.py
- Some websites may block scraping - this is normal

## Customization

### Change News Sources
Edit `news_crawler.py` to filter specific sources:
```python
preferred_sources = ['Reuters', 'BBC', 'CNN', 'The Guardian']
filtered = crawler.filter_by_sources(articles, preferred_sources)
```

### Adjust Summary Length
Edit `summarizer.py`:
```python
summary = summarizer.summarize_article(text, num_sentences=5)
```

### Modify Chart Style
Edit `timeline.py` to customize the Plotly chart colors and layout.

## API Endpoints

The application provides these endpoints:

- `GET /` - Main page
- `POST /search` - Search for news articles
  ```json
  {
    "keyword": "climate change",
    "days_back": 30,
    "max_articles": 20
  }
  ```
- `GET /health` - Health check

## Dependencies

Core packages:
- **Flask**: Web framework
- **gnews**: Google News API wrapper
- **newspaper3k**: Article extraction
- **beautifulsoup4**: HTML parsing
- **plotly**: Interactive visualizations
- **requests**: HTTP library

See `requirements.txt` for complete list.

## Limitations

- Google News API has rate limits
- Some news sites block automated scraping
- Summarization is extractive (selects existing sentences)
- Timeline accuracy depends on article metadata

## Future Enhancements

Potential improvements:
- 🔐 Add user authentication
- 💾 Database for caching results
- 📧 Email alerts for new articles
- 🌍 Multi-language support
- 📊 Advanced analytics dashboard
- 🤖 Use transformers for abstractive summarization

## License

This project is provided as-is for educational purposes.

## Acknowledgments

- Google News for news data
- Plotly for visualization library
- Flask community for excellent documentation

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the configuration settings
3. Ensure all dependencies are installed correctly

---

**Built with ❤️ using Flask, Python, and modern web technologies**

"""
Flask Web Application for News Crawler
Provides web interface for searching and visualizing news stories
"""

from flask import Flask, render_template, request, jsonify
import logging
from news_crawler import NewsCrawler
from summarizer import TextSummarizer
from timeline import TimelineGenerator
import config
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY

# Initialize components
crawler = NewsCrawler(
    language=config.DEFAULT_LANGUAGE,
    country=config.DEFAULT_COUNTRY,
    max_results=config.MAX_ARTICLES
)
summarizer = TextSummarizer()
timeline_generator = TimelineGenerator()


@app.route('/')
def index():
    """Render the home page"""
    return render_template('index.html')


@app.route('/search', methods=['POST'])
def search():
    """
    Handle news search request
    
    Expected JSON payload:
    {
        "keyword": "search term",
        "days_back": 30 (optional),
        "max_articles": 20 (optional)
    }
    """
    try:
        data = request.get_json()
        keyword = data.get('keyword', '').strip()
        
        if not keyword:
            return jsonify({'error': 'Please provide a search keyword'}), 400
        
        days_back = int(data.get('days_back', 30))
        max_articles = int(data.get('max_articles', config.MAX_ARTICLES))
        
        # Update crawler max results
        crawler.max_results = max_articles
        
        logger.info(f"Searching for: {keyword} (days_back={days_back})")
        
        # Fetch articles
        articles = crawler.search_news(keyword, days_back=days_back)
        
        if not articles:
            return jsonify({
                'error': 'No articles found',
                'message': f'No news articles found for "{keyword}". This could be due to:\n• No recent news matching your keyword\n• Network connectivity issues\n• Try different keywords or extend the date range\n• Try more general search terms'
            }), 404
        
        # Create story summary
        story_summary = summarizer.create_story_summary(articles)
        
        # Summarize individual articles
        for article in articles:
            text = article.get('full_text', '') or article.get('description', '')
            article['summary'] = summarizer.summarize_article(text, num_sentences=2)
        
        # Create timeline
        timeline_data = timeline_generator.create_timeline(articles)
        
        # Get coverage statistics
        coverage_stats = timeline_generator.get_coverage_stats(articles)
        
        # Prepare response
        response = {
            'success': True,
            'keyword': keyword,
            'story_summary': story_summary,
            'timeline': timeline_data,
            'coverage_stats': coverage_stats,
            'articles': [
                {
                    'title': article['title'],
                    'publisher': article['publisher'],
                    'published_date': article['published_date'].strftime('%Y-%m-%d %H:%M'),
                    'url': article['url'],
                    'description': article.get('description', ''),
                    'summary': article.get('summary', '')
                }
                for article in articles
            ]
        }
        
        return jsonify(response)
        
    except ValueError as e:
        logger.error(f"Invalid input: {str(e)}")
        return jsonify({'error': 'Invalid input parameters'}), 400
        
    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your request'}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'news-crawler'})


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    # Create cache directory if it doesn't exist
    if config.ENABLE_CACHE and not os.path.exists(config.CACHE_DIR):
        os.makedirs(config.CACHE_DIR)
    
    # Run the application
    app.run(
        debug=config.DEBUG,
        host='0.0.0.0',
        port=5000
    )

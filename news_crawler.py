"""
News Crawler Module
Fetches news articles from Google News based on user keywords
"""

import logging
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import time
import config
import re
from urllib.parse import quote_plus, urlparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NewsCrawler:
    """Fetches news articles from Google News"""
    
    def __init__(self, language='en', country='US', max_results=20):
        """
        Initialize the news crawler
        
        Args:
            language: Language code (default: 'en')
            country: Country code (default: 'US')
            max_results: Maximum number of articles to fetch
        """
        self.language = language
        self.country = country
        self.max_results = max_results
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
    def search_news(self, keyword, days_back=30):
        """
        Search for news articles by keyword
        
        Args:
            keyword: Search keyword
            days_back: Number of days to look back (default: 30)
            
        Returns:
            List of article dictionaries
        """
        try:
            logger.info(f"Searching for news about: {keyword}")
            
            # Try GNews library first
            articles = self._fetch_with_gnews(keyword, days_back)
            
            # If GNews fails, try direct scraping
            if not articles or len(articles) < 3:
                logger.info("GNews returned insufficient results, trying direct scraping...")
                articles = self._fetch_with_scraping(keyword, days_back)
            
            if not articles:
                logger.warning(f"No articles found for keyword: {keyword}")
                return []
            
            logger.info(f"Found {len(articles)} articles")
            
            # Limit to max_results
            articles = articles[:self.max_results]
            
            # Sort by published date (newest first)
            articles.sort(key=lambda x: x['published_date'], reverse=True)
            
            logger.info(f"Successfully processed {len(articles)} articles")
            return articles
            
        except Exception as e:
            logger.error(f"Error searching news: {str(e)}")
            return []
    
    def _fetch_with_gnews(self, keyword, days_back):
        """Fetch articles using GNews library"""
        try:
            from gnews import GNews
            
            google_news = GNews(
                language=self.language,
                country=self.country,
                max_results=self.max_results
            )
            
            # Set time period
            start_date = datetime.now() - timedelta(days=days_back)
            end_date = datetime.now()
            google_news.start_date = start_date
            google_news.end_date = end_date
            
            # Get news articles
            raw_articles = google_news.get_news(keyword)
            
            if not raw_articles:
                return []
            
            # Process articles
            processed_articles = []
            for idx, article in enumerate(raw_articles):
                try:
                    processed_article = self._process_gnews_article(article, idx)
                    if processed_article:
                        processed_articles.append(processed_article)
                    
                    # Rate limiting
                    time.sleep(0.3)
                    
                except Exception as e:
                    logger.error(f"Error processing GNews article {idx}: {str(e)}")
                    continue
            
            return processed_articles
            
        except Exception as e:
            logger.error(f"GNews fetch failed: {str(e)}")
            return []
    
    def _fetch_with_scraping(self, keyword, days_back):
        """Fetch articles by scraping Google News directly"""
        try:
            # Build Google News search URL
            query = quote_plus(keyword)
            url = f"https://news.google.com/search?q={query}&hl=en-US&gl=US&ceid=US:en"
            
            logger.info(f"Fetching from: {url}")
            
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find article elements
            articles = []
            article_elements = soup.find_all('article')
            
            for idx, element in enumerate(article_elements[:self.max_results]):
                try:
                    article_data = self._parse_article_element(element, idx)
                    if article_data:
                        articles.append(article_data)
                except Exception as e:
                    logger.error(f"Error parsing article element {idx}: {str(e)}")
                    continue
            
            return articles
            
        except Exception as e:
            logger.error(f"Scraping failed: {str(e)}")
            return []
    
    def _parse_article_element(self, element, index):
        """Parse a single article element from Google News HTML"""
        try:
            # Find title
            title_elem = element.find('a', class_=lambda x: x and 'gPFEn' in str(x))
            if not title_elem:
                title_elem = element.find('h3') or element.find('h4')
            
            title = title_elem.get_text(strip=True) if title_elem else "No Title"
            
            # Find URL
            url = "https://news.google.com" + title_elem['href'] if title_elem and title_elem.get('href') else "#"
            
            # Find source/publisher
            source_elem = element.find('a', {'data-n-tid': True})
            if not source_elem:
                source_elem = element.find('div', class_=lambda x: x and 'vr1PYe' in str(x))
            
            publisher = source_elem.get_text(strip=True) if source_elem else "Unknown"
            
            # Find time
            time_elem = element.find('time')
            published_date = datetime.now()
            
            if time_elem and time_elem.get('datetime'):
                try:
                    published_date = datetime.fromisoformat(time_elem['datetime'].replace('Z', '+00:00'))
                except:
                    published_date = self._parse_relative_time(time_elem.get_text(strip=True))
            else:
                time_text = element.find('div', class_=lambda x: x and 'UOVeFe' in str(x))
                if time_text:
                    published_date = self._parse_relative_time(time_text.get_text(strip=True))
            
            # Find description/snippet
            description = ""
            snippet_elem = element.find('p') or element.find('span', class_=lambda x: x and 'xBbh9' in str(x))
            if snippet_elem:
                description = snippet_elem.get_text(strip=True)
            
            return {
                'id': index,
                'title': title,
                'description': description,
                'url': url,
                'publisher': publisher,
                'published_date': published_date,
                'full_text': description
            }
            
        except Exception as e:
            logger.error(f"Error parsing article element: {str(e)}")
            return None
    
    def _parse_relative_time(self, time_str):
        """Parse relative time strings like '2 hours ago' into datetime"""
        try:
            time_str = time_str.lower()
            now = datetime.now()
            
            if 'minute' in time_str or 'min' in time_str:
                minutes = int(re.search(r'\d+', time_str).group())
                return now - timedelta(minutes=minutes)
            elif 'hour' in time_str:
                hours = int(re.search(r'\d+', time_str).group())
                return now - timedelta(hours=hours)
            elif 'day' in time_str:
                days = int(re.search(r'\d+', time_str).group())
                return now - timedelta(days=days)
            elif 'week' in time_str:
                weeks = int(re.search(r'\d+', time_str).group())
                return now - timedelta(weeks=weeks)
            elif 'month' in time_str:
                months = int(re.search(r'\d+', time_str).group())
                return now - timedelta(days=months*30)
            else:
                return now
        except:
            return datetime.now()
    
    def _process_gnews_article(self, article_data, index):
        """
        Process and extract detailed information from a GNews article
        
        Args:
            article_data: Article data from GNews
            index: Article index
            
        Returns:
            Processed article dictionary
        """
        try:
            url = article_data.get('url')
            
            # Try to get full article content (but don't block on it)
            full_text = article_data.get('description', '')
            
            # Parse published date
            published_date = article_data.get('published date')
            if isinstance(published_date, str):
                try:
                    published_date = datetime.strptime(published_date, '%a, %d %b %Y %H:%M:%S %Z')
                except:
                    try:
                        published_date = datetime.strptime(published_date, '%Y-%m-%d %H:%M:%S')
                    except:
                        published_date = datetime.now()
            elif not isinstance(published_date, datetime):
                published_date = datetime.now()
            
            # Get publisher info
            publisher_info = article_data.get('publisher', {})
            if isinstance(publisher_info, dict):
                publisher = publisher_info.get('title', 'Unknown')
            else:
                publisher = str(publisher_info) if publisher_info else 'Unknown'
            
            return {
                'id': index,
                'title': article_data.get('title', 'No Title'),
                'description': article_data.get('description', ''),
                'url': url,
                'publisher': publisher,
                'published_date': published_date,
                'full_text': full_text[:5000] if full_text else article_data.get('description', '')
            }
            
        except Exception as e:
            logger.error(f"Error in _process_gnews_article: {str(e)}")
            return None
    
    def filter_by_sources(self, articles, sources):
        """
        Filter articles by news sources
        
        Args:
            articles: List of article dictionaries
            sources: List of preferred source names
            
        Returns:
            Filtered list of articles
        """
        if not sources:
            return articles
        
        filtered = [
            article for article in articles
            if any(source.lower() in article['publisher'].lower() for source in sources)
        ]
        
        logger.info(f"Filtered to {len(filtered)} articles from preferred sources")
        return filtered


def main():
    """Test the news crawler"""
    print("Testing News Crawler...")
    print("=" * 80)
    
    crawler = NewsCrawler(max_results=10)
    articles = crawler.search_news("technology", days_back=7)
    
    if articles:
        print(f"\nSuccessfully fetched {len(articles)} articles!\n")
        for article in articles[:5]:  # Show first 5
            print(f"Title: {article['title']}")
            print(f"Source: {article['publisher']}")
            print(f"Date: {article['published_date'].strftime('%Y-%m-%d %H:%M')}")
            print(f"URL: {article['url'][:80]}...")
            print("-" * 80)
    else:
        print("\nNo articles found. This might be due to:")
        print("1. Internet connection issues")
        print("2. Google News blocking automated requests")
        print("3. No recent news for the search term")
        print("\nTry running the Flask app and testing through the web interface.")


if __name__ == "__main__":
    main()

"""
Timeline Generator Module
Creates timeline visualizations of news stories
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict
import plotly.graph_objects as go
import plotly.utils
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TimelineGenerator:
    """Generates timeline visualizations from news articles"""
    
    def __init__(self):
        """Initialize the timeline generator"""
        pass
    
    def create_timeline(self, articles):
        """
        Create a timeline from articles
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Dictionary with timeline data and Plotly figure JSON
        """
        if not articles:
            return {
                'events': [],
                'chart_json': None,
                'date_range': ''
            }
        
        try:
            # Group articles by date
            events_by_date = self._group_by_date(articles)
            
            # Create events list
            events = self._create_events(events_by_date)
            
            # Create Plotly timeline chart
            chart_json = self._create_plotly_timeline(events)
            
            # Get date range
            dates = [article['published_date'] for article in articles if 'published_date' in article]
            if dates:
                date_range = f"{min(dates).strftime('%B %d, %Y')} - {max(dates).strftime('%B %d, %Y')}"
            else:
                date_range = "Date range unavailable"
            
            return {
                'events': events,
                'chart_json': chart_json,
                'date_range': date_range
            }
            
        except Exception as e:
            logger.error(f"Error creating timeline: {str(e)}")
            return {
                'events': [],
                'chart_json': None,
                'date_range': ''
            }
    
    def _group_by_date(self, articles):
        """Group articles by date"""
        events_by_date = defaultdict(list)
        
        for article in articles:
            date = article.get('published_date')
            if isinstance(date, datetime):
                date_key = date.strftime('%Y-%m-%d')
                events_by_date[date_key].append(article)
        
        return events_by_date
    
    def _create_events(self, events_by_date):
        """Create timeline events from grouped articles"""
        events = []
        
        for date_str, articles in sorted(events_by_date.items()):
            try:
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                
                # Get main headline for this date
                main_article = articles[0]  # Most relevant article
                
                event = {
                    'date': date_str,
                    'date_formatted': date_obj.strftime('%B %d, %Y'),
                    'article_count': len(articles),
                    'main_headline': main_article.get('title', 'No title'),
                    'main_source': main_article.get('publisher', 'Unknown'),
                    'articles': [
                        {
                            'title': article.get('title', 'No title'),
                            'source': article.get('publisher', 'Unknown'),
                            'url': article.get('url', '#'),
                            'description': article.get('description', '')[:200]
                        }
                        for article in articles
                    ]
                }
                
                events.append(event)
                
            except Exception as e:
                logger.error(f"Error processing event for {date_str}: {str(e)}")
                continue
        
        return events
    
    def _create_plotly_timeline(self, events):
        """
        Create a Plotly timeline visualization
        
        Args:
            events: List of event dictionaries
            
        Returns:
            JSON string of Plotly figure
        """
        if not events:
            return None
        
        try:
            # Prepare data for plotting
            dates = [event['date'] for event in events]
            article_counts = [event['article_count'] for event in events]
            headlines = [event['main_headline'][:50] + '...' if len(event['main_headline']) > 50 
                        else event['main_headline'] for event in events]
            
            # Create hover text
            hover_texts = [
                f"<b>{event['date_formatted']}</b><br>" +
                f"Articles: {event['article_count']}<br>" +
                f"<i>{event['main_headline'][:80]}...</i>"
                for event in events
            ]
            
            # Create figure
            fig = go.Figure()
            
            # Add scatter plot for events
            fig.add_trace(go.Scatter(
                x=dates,
                y=article_counts,
                mode='lines+markers',
                marker=dict(
                    size=12,
                    color=article_counts,
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Article Count"),
                    line=dict(width=2, color='white')
                ),
                line=dict(width=2, color='rgba(100, 149, 237, 0.5)'),
                text=headlines,
                hovertext=hover_texts,
                hoverinfo='text',
                name='News Coverage'
            ))
            
            # Update layout
            fig.update_layout(
                title={
                    'text': 'News Story Timeline',
                    'x': 0.5,
                    'xanchor': 'center'
                },
                xaxis=dict(
                    title='Date',
                    type='date',
                    tickformat='%b %d, %Y',
                    tickangle=-45,
                    showgrid=True,
                    gridcolor='rgba(128, 128, 128, 0.2)'
                ),
                yaxis=dict(
                    title='Number of Articles',
                    showgrid=True,
                    gridcolor='rgba(128, 128, 128, 0.2)'
                ),
                plot_bgcolor='rgba(240, 240, 240, 0.5)',
                paper_bgcolor='white',
                hovermode='closest',
                height=500,
                margin=dict(l=50, r=50, t=80, b=100)
            )
            
            # Convert to JSON
            chart_json = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
            return chart_json
            
        except Exception as e:
            logger.error(f"Error creating Plotly timeline: {str(e)}")
            return None
    
    def get_coverage_stats(self, articles):
        """
        Get statistics about news coverage
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Dictionary with coverage statistics
        """
        if not articles:
            return {
                'total_articles': 0,
                'unique_sources': 0,
                'date_span_days': 0,
                'avg_articles_per_day': 0
            }
        
        try:
            dates = [article['published_date'] for article in articles if 'published_date' in article]
            sources = set(article.get('publisher', 'Unknown') for article in articles)
            
            if dates:
                date_span = (max(dates) - min(dates)).days + 1
                avg_per_day = len(articles) / max(date_span, 1)
            else:
                date_span = 0
                avg_per_day = 0
            
            return {
                'total_articles': len(articles),
                'unique_sources': len(sources),
                'date_span_days': date_span,
                'avg_articles_per_day': round(avg_per_day, 1)
            }
            
        except Exception as e:
            logger.error(f"Error calculating coverage stats: {str(e)}")
            return {
                'total_articles': len(articles),
                'unique_sources': 0,
                'date_span_days': 0,
                'avg_articles_per_day': 0
            }


def main():
    """Test the timeline generator"""
    # Create sample data
    sample_articles = [
        {
            'title': 'Breaking News Article 1',
            'publisher': 'Reuters',
            'published_date': datetime.now() - timedelta(days=5),
            'description': 'Sample description',
            'url': 'http://example.com/1'
        },
        {
            'title': 'Follow-up Article 2',
            'publisher': 'BBC',
            'published_date': datetime.now() - timedelta(days=3),
            'description': 'Sample description',
            'url': 'http://example.com/2'
        },
        {
            'title': 'Latest Update Article 3',
            'publisher': 'CNN',
            'published_date': datetime.now() - timedelta(days=1),
            'description': 'Sample description',
            'url': 'http://example.com/3'
        }
    ]
    
    generator = TimelineGenerator()
    timeline = generator.create_timeline(sample_articles)
    
    print(f"Created timeline with {len(timeline['events'])} events")
    print(f"Date range: {timeline['date_range']}")


if __name__ == "__main__":
    main()

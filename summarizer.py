"""
Text Summarization Module
Creates summaries of news articles and overall story summaries
"""

import logging
from collections import Counter
import re
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TextSummarizer:
    """Summarizes news articles using extractive summarization"""
    
    def __init__(self):
        """Initialize the summarizer"""
        self.stop_words = set([
            'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from',
            'has', 'he', 'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the',
            'to', 'was', 'will', 'with', 'said', 'says', 'can', 'been', 'have',
            'had', 'has', 'this', 'but', 'their', 'which', 'they', 'would', 'there'
        ])
    
    def summarize_article(self, text, num_sentences=3):
        """
        Create a summary of a single article
        
        Args:
            text: Article text
            num_sentences: Number of sentences in summary
            
        Returns:
            Summary string
        """
        if not text or len(text.strip()) < 50:
            return text
        
        try:
            sentences = self._split_sentences(text)
            
            if len(sentences) <= num_sentences:
                return text
            
            # Score sentences
            scored_sentences = self._score_sentences(sentences)
            
            # Select top sentences
            top_sentences = sorted(scored_sentences, key=lambda x: x[1], reverse=True)[:num_sentences]
            
            # Sort by original order
            top_sentences.sort(key=lambda x: x[2])
            
            summary = ' '.join([sent[0] for sent in top_sentences])
            return summary
            
        except Exception as e:
            logger.error(f"Error summarizing article: {str(e)}")
            return text[:500] + "..."
    
    def create_story_summary(self, articles):
        """
        Create an overall summary of the news story from multiple articles
        
        Args:
            articles: List of article dictionaries
            
        Returns:
            Dictionary with story summary and key points
        """
        if not articles:
            return {
                'summary': 'No articles found for this query.',
                'key_points': [],
                'article_count': 0,
                'date_range': '',
                'main_sources': []
            }
        
        try:
            # Combine all article texts
            all_text = ' '.join([
                article.get('full_text', '') or article.get('description', '')
                for article in articles
            ])
            
            # Extract key information
            key_phrases = self._extract_key_phrases(all_text)
            
            # Get date range
            dates = [article['published_date'] for article in articles if 'published_date' in article]
            if dates:
                date_range = f"{min(dates).strftime('%B %d, %Y')} - {max(dates).strftime('%B %d, %Y')}"
            else:
                date_range = "Date range unavailable"
            
            # Get main sources
            sources = [article.get('publisher', 'Unknown') for article in articles]
            source_counts = Counter(sources)
            main_sources = [source for source, count in source_counts.most_common(5)]
            
            # Create summary
            summary = self._create_overall_summary(articles, key_phrases)
            
            return {
                'summary': summary,
                'key_points': key_phrases[:10],
                'article_count': len(articles),
                'date_range': date_range,
                'main_sources': main_sources
            }
            
        except Exception as e:
            logger.error(f"Error creating story summary: {str(e)}")
            return {
                'summary': f'Found {len(articles)} articles on this topic.',
                'key_points': [],
                'article_count': len(articles),
                'date_range': '',
                'main_sources': []
            }
    
    def _split_sentences(self, text):
        """Split text into sentences"""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        return sentences
    
    def _score_sentences(self, sentences):
        """
        Score sentences based on word frequency
        
        Returns:
            List of tuples (sentence, score, original_index)
        """
        # Calculate word frequencies
        word_freq = Counter()
        for sentence in sentences:
            words = self._tokenize(sentence)
            words = [w for w in words if w.lower() not in self.stop_words]
            word_freq.update(words)
        
        # Score sentences
        scored = []
        for idx, sentence in enumerate(sentences):
            words = self._tokenize(sentence)
            words = [w for w in words if w.lower() not in self.stop_words]
            
            if len(words) > 0:
                score = sum(word_freq[word] for word in words) / len(words)
                scored.append((sentence, score, idx))
        
        return scored
    
    def _tokenize(self, text):
        """Tokenize text into words"""
        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        return words
    
    def _extract_key_phrases(self, text, top_n=10):
        """Extract key phrases from text"""
        words = self._tokenize(text)
        words = [w for w in words if w not in self.stop_words and len(w) > 3]
        
        word_freq = Counter(words)
        key_words = [word for word, count in word_freq.most_common(top_n)]
        
        return key_words
    
    def _create_overall_summary(self, articles, key_phrases):
        """Create an overall summary from multiple articles"""
        if not articles:
            return "No articles available."
        
        # Get the most recent article's description
        recent_article = max(articles, key=lambda x: x.get('published_date', datetime.min))
        base_summary = recent_article.get('description', '')
        
        if not base_summary:
            base_summary = recent_article.get('full_text', '')[:300]
        
        # Add context about coverage
        num_articles = len(articles)
        sources_mentioned = len(set(article.get('publisher', 'Unknown') for article in articles))
        
        context = f"Based on {num_articles} articles from {sources_mentioned} news sources, "
        
        if key_phrases:
            context += f"key topics include: {', '.join(key_phrases[:5])}. "
        
        return context + base_summary[:400]


def main():
    """Test the summarizer"""
    summarizer = TextSummarizer()
    
    test_text = """
    Artificial intelligence has made significant advances in recent years. 
    Machine learning models are now being used in various industries. 
    The technology is transforming healthcare, finance, and transportation.
    Many experts believe AI will continue to revolutionize our daily lives.
    However, concerns about ethics and job displacement remain important topics.
    Researchers are working on making AI more transparent and accountable.
    """
    
    summary = summarizer.summarize_article(test_text, num_sentences=2)
    print("Summary:", summary)


if __name__ == "__main__":
    main()

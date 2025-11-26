# Configuration settings for the News Crawler application

# Flask settings
SECRET_KEY = 'your-secret-key-here-change-in-production'
DEBUG = True

# News crawler settings
MAX_ARTICLES = 20  # Maximum number of articles to fetch per query
DEFAULT_LANGUAGE = 'en'
DEFAULT_COUNTRY = 'US'

# Summarization settings
MAX_SUMMARY_LENGTH = 150  # Maximum length of summary in words
MIN_SUMMARY_LENGTH = 50   # Minimum length of summary in words

# Timeline settings
TIMELINE_DATE_FORMAT = '%Y-%m-%d'

# Cache settings
ENABLE_CACHE = True
CACHE_DIR = 'cache'
CACHE_EXPIRY_HOURS = 24

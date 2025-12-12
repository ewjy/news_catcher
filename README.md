# Keyword Timeline (Google News)

A simple Flask web app to fetch Google News RSS for a keyword, filter by time range, and display a timeline graph of article counts per day.

## Features
- Enter keyword
- Select time range (Last 7/30 days or custom)
- Limit number of articles fetched
- Line chart of articles per day
- List of matching articles with links

## Setup

### Requirements
- Python 3.9+
- Windows (or any OS with Python)

### Install
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

## Run
```bash
set FLASK_APP=app/app.py
python app/app.py
```
Then open http://localhost:5000 in your browser.

## Notes
- Uses Google News RSS search endpoint and filters client-side by date.
- If you need stricter time filtering, you can add multiple requests across days and merge, but RSS usually provides enough recent items.

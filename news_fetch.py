import os
import sys
import requests
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration: Insert your API keys here or set them as environment variables.
# ---------------------------------------------------------------------------
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "YOUR_NEWSAPI_KEY")
GUARDIAN_KEY = os.environ.get("GUARDIAN_KEY", "YOUR_GUARDIAN_API_KEY")
GNEWS_KEY = os.environ.get("GNEWS_KEY", "YOUR_GNEWS_API_KEY")

# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------
def validate_date(date_str):
    """Validate the input date format YYYY-MM-DD."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def create_directory_for_date(date_str):
    """Create a directory for the given date if it doesn't exist."""
    if not os.path.exists(date_str):
        os.makedirs(date_str)

def save_article_to_file(date_str, article, index):
    """Save a single article to a text file."""
    filename = f"{article['source']}_{index:05d}.txt"
    filepath = os.path.join(date_str, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"Title: {article['title']}\n")
        f.write(f"Author: {article['author']}\n")
        f.write(f"Source: {article['source']}\n")
        f.write(f"Published: {article['published_at']}\n")
        f.write(f"URL: {article['url']}\n")
        f.write("----------------------------------------\n")
        f.write(article['text'] or "")
    return filepath

def normalize_article(source_name, title, author, published_at, url, text):
    """Return a standardized article dictionary."""
    return {
        "source": source_name,
        "title": title or "No Title",
        "author": author or "Unknown",
        "published_at": published_at or "Unknown",
        "url": url or "No URL",
        "text": text or ""
    }

# ---------------------------------------------------------------------------
# API Clients
# ---------------------------------------------------------------------------

def fetch_newsapi_articles(date_str, query):
    if not NEWSAPI_KEY or NEWSAPI_KEY == "YOUR_NEWSAPI_KEY":
        return []
    url = "https://newsapi.org/v2/everything"
    from_date = f"{date_str}T00:00:00"
    to_date = f"{date_str}T23:59:59"
    page = 1
    page_size = 50
    articles = []

    while True:
        params = {
            "apiKey": NEWSAPI_KEY,
            "from": from_date,
            "to": to_date,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "page": page,
            "q": query  # use passed-in query
        }
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            break
        data = resp.json()
        fetched = data.get("articles", [])
        if not fetched:
            break
        for a in fetched:
            article = normalize_article(
                source_name="newsapi",
                title=a.get("title"),
                author=a.get("author"),
                published_at=a.get("publishedAt"),
                url=a.get("url"),
                text=a.get("content") or a.get("description") or ""
            )
            articles.append(article)
        total_results = data.get("totalResults", 0)
        if page * page_size >= total_results:
            break
        page += 1

    return articles

def fetch_guardian_articles(date_str):
    if not GUARDIAN_KEY or GUARDIAN_KEY == "YOUR_GUARDIAN_API_KEY":
        return []
    url = "https://content.guardianapis.com/search"
    page = 1
    page_size = 50
    articles = []

    while True:
        params = {
            "api-key": GUARDIAN_KEY,
            "from-date": date_str,
            "to-date": date_str,
            "show-fields": "headline,bodyText",
            "page-size": page_size,
            "page": page
        }
        resp = requests.get(url, params=params)
        if resp.status_code != 200:
            break
        data = resp.json().get("response", {})
        results = data.get("results", [])
        if not results:
            break
        for r in results:
            fields = r.get("fields", {})
            text = fields.get("bodyText", "")
            title = fields.get("headline", r.get("webTitle"))
            article = normalize_article(
                source_name="guardian",
                title=title,
                author="Unknown",
                published_at=r.get("webPublicationDate"),
                url=r.get("webUrl"),
                text=text
            )
            articles.append(article)
        current_page = data.get("currentPage")
        total_pages = data.get("pages")
        if current_page >= total_pages:
            break
        page += 1

    return articles

def fetch_gnews_articles(date_str, query):
    if not GNEWS_KEY or GNEWS_KEY == "YOUR_GNEWS_API_KEY":
        return []
    url = "https://gnews.io/api/v4/search"
    
    # Remove 'from'/'to' parameters and date filtering; just fetch whatever is available
    params = {
        "token": GNEWS_KEY,
        "lang": "en",
        "max": 100,
        "q": query
    }

    resp = requests.get(url, params=params)
    articles = []
    if resp.status_code == 200:
        data = resp.json()
        fetched = data.get("articles", [])
        # Directly save all fetched articles
        for a in fetched:
            published_at = a.get("publishedAt", "")
            article = normalize_article(
                source_name="gnews",
                title=a.get("title"),
                author=(a.get("source", {}).get("name") or "Unknown"),
                published_at=published_at,
                url=a.get("url"),
                text=a.get("content") or a.get("description") or ""
            )
            articles.append(article)
    return articles



# ---------------------------------------------------------------------------
# Main Program
# ---------------------------------------------------------------------------
def main():
    if len(sys.argv) < 2:
        print("Usage: python news_fetch.py YYYY-MM-DD [search_term]")
        sys.exit(1)

    date_str = sys.argv[1]
    if not validate_date(date_str):
        print("Error: Date must be in YYYY-MM-DD format.")
        sys.exit(1)
    
    # If search term not provided, default to "news"
    query = sys.argv[2] if len(sys.argv) > 2 else "news"

    create_directory_for_date(date_str)

    all_articles = []
    # Fetch from NewsAPI with query
    all_articles.extend(fetch_newsapi_articles(date_str, query))
    # Fetch from Guardian (no query needed)
    all_articles.extend(fetch_guardian_articles(date_str))
    # Fetch from GNews with query
    all_articles.extend(fetch_gnews_articles(date_str, query))

    # Save articles
    count = 1
    for article in all_articles:
        save_article_to_file(date_str, article, count)
        count += 1

    print(f"Saved {len(all_articles)} articles for {date_str} in '{date_str}' directory.")

if __name__ == "__main__":
    main()

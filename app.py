from flask import Flask, jsonify
from flask_cors import CORS
import requests
from textblob import TextBlob
import schedule
import time
import threading
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()  # Loads environment variables from a .env file

app = Flask(__name__)
CORS(app)  # This allows your frontend to talk to the backend

# In-memory storage for mentions (for demo purposes. Use a database like SQLite or PostgreSQL for a real project)
mentions_data = []

# --- Configuration (Get your FREE API keys and replace these) ---
NEWS_API_KEY = os.getenv('NEWS_API_KEY', 'YOUR_NEWS_API_KEY_HERE')  # Get from https://newsapi.org/
REDDIT_CLIENT_ID = os.getenv('REDDIT_CLIENT_ID', 'YOUR_REDDIT_CLIENT_ID')
REDDIT_CLIENT_SECRET = os.getenv('REDDIT_CLIENT_SECRET', 'YOUR_REDDIT_CLIENT_SECRET')

# --- Function to fetch news articles ---
def fetch_news_mentions(brand_name="Apple"):
    url = f"https://newsapi.org/v2/everything?q={brand_name}&sortBy=publishedAt&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(url)
        articles = response.json().get('articles', [])
        for article in articles:
            mention = {
                "id": f"news_{article['publishedAt']}",
                "text": f"{article['title']}. {article['description']}",
                "source": "news",
                "url": article['url'],
                "timestamp": article['publishedAt'],
                "sentiment": analyze_sentiment(f"{article['title']} {article['description']}"),
            }
            # Avoid duplicates for demo
            if mention not in mentions_data:
                mentions_data.append(mention)
        print(f"Fetched {len(articles)} news mentions.")
    except Exception as e:
        print(f"Error fetching news: {e}")

# --- Function to fetch Reddit posts ---
def fetch_reddit_mentions(brand_name="Apple", subreddit="technology", limit=10):
    # Reddit API requires authentication
    auth = requests.auth.HTTPBasicAuth(REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET)
    data = {
        'grant_type': 'password',
        'username': 'YOUR_REDDIT_USERNAME',  # Replace with your Reddit username
        'password': 'YOUR_REDDIT_PASSWORD'   # Replace with your Reddit password
    }
    headers = {'User-Agent': 'BrandTrackerBot/0.0.1'}
    try:
        # Get access token
        res = requests.post('https://www.reddit.com/api/v1/access_token', auth=auth, data=data, headers=headers)
        token = res.json().get('access_token')
        headers['Authorization'] = f'bearer {token}'

        # Fetch posts
        url = f"https://oauth.reddit.com/r/{subreddit}/search?q={brand_name}&restrict_sr=1&limit={limit}"
        response = requests.get(url, headers=headers)
        posts = response.json().get('data', {}).get('children', [])
        for post in posts:
            post_data = post['data']
            mention = {
                "id": f"reddit_{post_data['created']}",
                "text": f"{post_data['title']}. {post_data['selftext']}",
                "source": "reddit",
                "url": f"https://reddit.com{post_data['permalink']}",
                "timestamp": datetime.fromtimestamp(post_data['created']).isoformat(),
                "sentiment": analyze_sentiment(f"{post_data['title']} {post_data['selftext']}"),
            }
            if mention not in mentions_data:
                mentions_data.append(mention)
        print(f"Fetched {len(posts)} Reddit mentions.")
    except Exception as e:
        print(f"Error fetching Reddit data: {e}")

# --- Function for Sentiment Analysis ---
def analyze_sentiment(text):
    analysis = TextBlob(text)
    # TextBlob returns polarity between -1 (negative) and +1 (positive)
    polarity = analysis.sentiment.polarity
    if polarity > 0.1:
        return "positive"
    elif polarity < -0.1:
        return "negative"
    else:
        return "neutral"

# --- Function to check for spikes (Simple logic for demo) ---
def check_for_spikes():
    # Simple logic: if mentions in the last hour are 50% more than the previous hour, it's a spike.
    # For a real project, use a more robust statistical method.
    print("Checking for spikes... (Spike logic would be implemented here)")

# --- Scheduler to run data fetching periodically ---
def run_scheduler():
    schedule.every(10).minutes.do(fetch_news_mentions)
    schedule.every(10).minutes.do(fetch_reddit_mentions)
    schedule.every(1).hours.do(check_for_spikes)
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- API Routes to serve data to the frontend ---
@app.route('/api/mentions', methods=['GET'])
def get_mentions():
    # Return the mentions, sorted by newest first
    sorted_mentions = sorted(mentions_data, key=lambda x: x['timestamp'], reverse=True)
    return jsonify(sorted_mentions)

@app.route('/api/stats', methods=['GET'])
def get_stats():
    total = len(mentions_data)
    positive = len([m for m in mentions_data if m['sentiment'] == 'positive'])
    negative = len([m for m in mentions_data if m['sentiment'] == 'negative'])
    neutral = len([m for m in mentions_data if m['sentiment'] == 'neutral'])
    return jsonify({
        'total_mentions': total,
        'positive_mentions': positive,
        'negative_mentions': negative,
        'neutral_mentions': neutral
    })

# --- Start the application ---
if __name__ == '__main__':
    # Fetch initial data
    fetch_news_mentions()
    fetch_reddit_mentions()
    # Start the scheduler in a separate thread so it doesn't block the Flask app
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    # Run the Flask app
    app.run(debug=True, port=5000)
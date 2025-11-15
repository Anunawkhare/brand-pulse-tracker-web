from flask import Flask, jsonify, render_template
from flask_cors import CORS
import requests
from textblob import TextBlob
import schedule
import time
import threading
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)

# In-memory storage for mentions
mentions_data = []

# --- Configuration with your API Key ---
NEWS_API_KEY = 'dfde3889176e43c29d9a84d25955ecc0'


# --- Demo Data ---
def generate_demo_mentions():
    demo_mentions = [
        {
            "id": "demo_1",
            "text": "Apple launches new iPhone with amazing features!",
            "source": "demo",
            "url": "https://example.com",
            "timestamp": datetime.now().isoformat(),
            "sentiment": "positive"
        },
        {
            "id": "demo_2",
            "text": "Customers reporting issues with Apple's latest update.",
            "source": "demo",
            "url": "https://example.com",
            "timestamp": datetime.now().isoformat(),
            "sentiment": "negative"
        },
        {
            "id": "demo_3",
            "text": "Apple stock reaches all-time high in market.",
            "source": "demo",
            "url": "https://example.com",
            "timestamp": datetime.now().isoformat(),
            "sentiment": "positive"
        }
    ]

    for mention in demo_mentions:
        mentions_data.append(mention)

    print("✅ Loaded demo data")


# --- Fetch News ---
def fetch_news_mentions(brand_name="Apple"):
    try:
        url = f"https://newsapi.org/v2/everything?q={brand_name}&language=en&pageSize=10&apiKey={NEWS_API_KEY}"
        response = requests.get(url)
        print(f"NewsAPI Status: {response.status_code}")

        if response.status_code == 200:
            articles = response.json().get('articles', [])
            for article in articles:
                if article['title'] and article['title'] != '[Removed]':
                    mention = {
                        "id": f"news_{article['publishedAt']}",
                        "text": article['title'],
                        "source": "news",
                        "url": article['url'],
                        "timestamp": article['publishedAt'],
                        "sentiment": analyze_sentiment(article['title'])
                    }
                    mentions_data.append(mention)
            print(f"✅ Added {len(articles)} news mentions")
        else:
            print(f"❌ NewsAPI Error: {response.status_code}")
    except Exception as e:
        print(f"❌ News error: {e}")


# --- Sentiment Analysis ---
def analyze_sentiment(text):
    try:
        analysis = TextBlob(text)
        polarity = analysis.sentiment.polarity
        if polarity > 0.1:
            return "positive"
        elif polarity < -0.1:
            return "negative"
        else:
            return "neutral"
    except:
        return "neutral"


# --- Routes ---
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BrandPulse Tracker</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    </head>
    <body class="bg-gray-100">
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-3xl font-bold text-center mb-8">🎯 BrandPulse Tracker</h1>

            <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8" id="stats">
                <div class="bg-white p-4 rounded shadow text-center">
                    <h3 class="font-semibold">Total Mentions</h3>
                    <p class="text-2xl" id="total">0</p>
                </div>
                <div class="bg-white p-4 rounded shadow text-center">
                    <h3 class="font-semibold">Positive</h3>
                    <p class="text-2xl text-green-600" id="positive">0</p>
                </div>
                <div class="bg-white p-4 rounded shadow text-center">
                    <h3 class="font-semibold">Negative</h3>
                    <p class="text-2xl text-red-600" id="negative">0</p>
                </div>
                <div class="bg-white p-4 rounded shadow text-center">
                    <h3 class="font-semibold">Neutral</h3>
                    <p class="text-2xl text-gray-600" id="neutral">0</p>
                </div>
            </div>

            <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                <div class="bg-white p-4 rounded shadow">
                    <h2 class="text-xl font-semibold mb-4">Sentiment Analysis</h2>
                    <canvas id="chart" height="250"></canvas>
                </div>

                <div class="bg-white p-4 rounded shadow">
                    <h2 class="text-xl font-semibold mb-4">Recent Mentions</h2>
                    <div id="mentions" class="space-y-3 max-h-96 overflow-y-auto">
                        <p class="text-center text-gray-500">Loading...</p>
                    </div>
                </div>
            </div>

            <div class="mt-8 text-center">
                <button onclick="loadData()" class="bg-blue-500 text-white px-6 py-2 rounded">Refresh Data</button>
            </div>
        </div>

        <script>
            let chart = null;

            async function loadData() {
                try {
                    const [stats, mentions] = await Promise.all([
                        fetch('/api/stats').then(r => r.json()),
                        fetch('/api/mentions').then(r => r.json())
                    ]);

                    // Update stats
                    document.getElementById('total').textContent = stats.total_mentions;
                    document.getElementById('positive').textContent = stats.positive_mentions;
                    document.getElementById('negative').textContent = stats.negative_mentions;
                    document.getElementById('neutral').textContent = stats.neutral_mentions;

                    // Update chart
                    updateChart(stats);

                    // Update mentions
                    updateMentions(mentions);

                } catch (error) {
                    console.error('Error:', error);
                }
            }

            function updateChart(stats) {
                const ctx = document.getElementById('chart').getContext('2d');
                if (chart) chart.destroy();

                chart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: ['Positive', 'Negative', 'Neutral'],
                        datasets: [{
                            data: [stats.positive_mentions, stats.negative_mentions, stats.neutral_mentions],
                            backgroundColor: ['#10B981', '#EF4444', '#6B7280']
                        }]
                    }
                });
            }

            function updateMentions(mentions) {
                const container = document.getElementById('mentions');
                if (mentions.length === 0) {
                    container.innerHTML = '<p class="text-center text-gray-500">No mentions found</p>';
                    return;
                }

                container.innerHTML = mentions.slice(0, 10).map(mention => `
                    <div class="border rounded p-3">
                        <div class="flex justify-between">
                            <span class="text-sm bg-gray-100 px-2 py-1 rounded">${mention.source}</span>
                            <span class="text-sm ${
                                mention.sentiment === 'positive' ? 'text-green-600' :
                                mention.sentiment === 'negative' ? 'text-red-600' : 'text-gray-600'
                            }">${mention.sentiment}</span>
                        </div>
                        <p class="mt-2 text-sm">${mention.text}</p>
                        <div class="flex justify-between mt-2 text-xs text-gray-500">
                            <a href="${mention.url}" target="_blank" class="text-blue-500">View Source</a>
                            <span>${new Date(mention.timestamp).toLocaleTimeString()}</span>
                        </div>
                    </div>
                `).join('');
            }

            // Load data on page load
            loadData();
            // Auto-refresh every 30 seconds
            setInterval(loadData, 30000);
        </script>
    </body>
    </html>
    """


@app.route('/api/mentions')
def get_mentions():
    return jsonify(mentions_data[:20])


@app.route('/api/stats')
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


@app.route('/api/health')
def health():
    return jsonify({"status": "healthy", "mentions": len(mentions_data)})


# --- Scheduler ---
def run_scheduler():
    schedule.every(5).minutes.do(fetch_news_mentions)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    print("🚀 Starting BrandPulse Tracker...")
    print("📊 Dashboard: http://127.0.0.1:5000")

    # Load data
    generate_demo_mentions()
    fetch_news_mentions()

    # Start scheduler
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()

    # Run app
    app.run(debug=True, port=5000)
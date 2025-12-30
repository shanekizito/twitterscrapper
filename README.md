# Twitter Scraper API

A headless Twitter (X) scraping API built with FastAPI and Selenium. This service provides endpoints to scrape Twitter profiles, tweets, and perform influencer discovery and analytics.

## Features

- **Profile Scraping**: Extract comprehensive Twitter profile information including bio, followers, following, and verified status
- **Tweet Scraping**: Scrape tweets from any public Twitter account with engagement metrics
- **Influencer Discovery**: Discover influencers through network analysis and following lists
- **Analytics Engine**: Built-in sentiment analysis and engagement metrics
- **Background Jobs**: Asynchronous processing for long-running scraping tasks
- **CORS Enabled**: Ready for frontend integration

## Tech Stack

- **FastAPI**: Modern, fast web framework for building APIs
- **Selenium**: Browser automation with undetected Chrome driver
- **BeautifulSoup4**: HTML parsing and data extraction
- **TextBlob**: Natural language processing and sentiment analysis
- **Pydantic**: Data validation using Python type annotations
- **Uvicorn**: ASGI server for production deployment

## Installation

### Prerequisites

- Python 3.8 or higher
- Chrome browser installed
- Node.js (for axios dependency)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/twitterscrapper.git
cd twitterscrapper
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Install Node.js dependencies:
```bash
npm install
```

4. Create a `.env` file in the root directory (optional):
```env
# Environment Variables
TWITTER_USERNAME=your_username
TWITTER_PASSWORD=your_password
PROXY_URL=
```

## Usage

### Start the API Server

```bash
python main.py
```

The server will start on `http://localhost:8000`

### API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### API Endpoints

#### Health Check
```
GET /
```

#### Get Profile
```
GET /profile/{username}
```
Returns comprehensive profile information for a Twitter user.

#### Scrape Tweets
```
POST /tweets
```
Body:
```json
{
  "username": "elonmusk",
  "max_tweets": 20
}
```

#### Analyze Tweets
```
POST /analyze
```
Body:
```json
{
  "username": "username",
  "tweets": [...],
  "profile": {...}
}
```

Returns sentiment analysis, engagement metrics, top hashtags, mentions, and tweet type distribution.

#### Discover Influencers
```
POST /discover
```
Body:
```json
{
  "usernames": ["elonmusk", "BillGates"],
  "user_id": "optional_user_id",
  "callback_url": "optional_callback_url"
}
```

Starts a background job to discover influencers through network analysis.

#### Get Job Status
```
GET /jobs/{job_id}
```

Check the status of a background discovery or sync job.

#### Sync Tweets
```
POST /sync-tweets
```
Body:
```json
{
  "usernames": ["user1", "user2"],
  "callback_url": "https://your-backend.com/callback",
  "user_id": "user123"
}
```

## Project Structure

```
twitterscrapper/
├── main.py                 # FastAPI application and routes
├── requirements.txt        # Python dependencies
├── package.json           # Node.js dependencies
├── .env                   # Environment variables (not in git)
├── scraper/               # Scraping modules
│   ├── core.py           # Core Twitter scraper
│   └── ...               # Other scraper utilities
├── analytics/            # Analytics engine
│   └── engine.py         # Sentiment and engagement analysis
├── models/               # Data models
│   └── data_models.py    # Pydantic models for tweets and profiles
└── jobs/                 # Background job handlers
    └── tweet_sync.py     # Tweet synchronization job
```

## Features in Detail

### Headless Browser Automation
Uses undetected Chrome driver to bypass bot detection and scrape Twitter data reliably.

### Background Job Processing
Long-running tasks like influencer discovery run in the background with job status tracking.

### Sentiment Analysis
Automatically analyzes tweet sentiment using TextBlob for positive, negative, and neutral classification.

### Engagement Metrics
Calculates engagement rates, average likes, retweets, and replies per tweet.

### Network Discovery
Discovers influencers by analyzing following lists and performing network traversal.

## Environment Variables

- `TWITTER_USERNAME`: (Optional) Twitter username for authentication
- `TWITTER_PASSWORD`: (Optional) Twitter password for authentication
- `PROXY_URL`: (Optional) Proxy server URL for requests

## Development

### Running in Development Mode

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Testing the API

Use the built-in Swagger UI at `/docs` or tools like Postman, curl, or HTTPie:

```bash
# Get profile
curl http://localhost:8000/profile/elonmusk

# Scrape tweets
curl -X POST http://localhost:8000/tweets \
  -H "Content-Type: application/json" \
  -d '{"username": "elonmusk", "max_tweets": 10}'
```

## Notes

- This scraper uses browser automation, so it requires Chrome to be installed
- Scraping large amounts of data may take time due to rate limiting and page load times
- Use responsibly and respect Twitter's Terms of Service
- For production use, consider implementing Redis for job storage instead of in-memory storage

## License

MIT License - feel free to use this project for your own purposes.

## Contributing

need to add instagram tracking and news sites

Contributions are welcome! Please feel free to submit a Pull Request.

## Disclaimer

This tool is for educational purposes only. Users are responsible for ensuring their use complies with Twitter's Terms of Service and applicable laws.

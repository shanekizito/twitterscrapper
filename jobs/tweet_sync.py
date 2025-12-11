import logging
import requests
from typing import List
from scraper.core import TwitterScraper
from models.data_models import Tweet

logger = logging.getLogger(__name__)

def sync_influencer_tweets(username: str, scraper: TwitterScraper) -> List[Tweet]:
    """Scrape recent tweets for a specific influencer"""
    try:
        logger.info(f"Syncing tweets for @{username}")
        tweets = scraper.scrape_tweets(username, count=20)
        return tweets
    except Exception as e:
        logger.error(f"Error syncing tweets for @{username}: {str(e)}")
        return []

def run_tweet_sync_job(job_id: str, usernames: List[str], callback_url: str, user_id: str):
    """Background task to sync tweets for multiple influencers"""
    logger.info(f"Starting sync job {job_id} for {len(usernames)} influencers")
    
    scraper = TwitterScraper(headless=True)
    total_tweets = 0
    
    try:
        for username in usernames:
            tweets = sync_influencer_tweets(username, scraper)
            if tweets:
                # Send to Next.js API to save
                try:
                    payload = {
                        "username": username,
                        "tweets": [t.dict() for t in tweets],
                        "user_id": user_id
                    }
                    # Assuming callback_url is something like http://localhost:3000/api/tweets/save
                    response = requests.post(callback_url, json=payload)
                    if response.status_code == 200:
                        logger.info(f"Saved {len(tweets)} tweets for @{username}")
                        total_tweets += len(tweets)
                    else:
                        logger.error(f"Failed to save tweets for @{username}: {response.text}")
                except Exception as e:
                    logger.error(f"Error sending tweets to API for @{username}: {str(e)}")
            
    finally:
        scraper.close()
        logger.info(f"Sync job {job_id} complete. Total tweets saved: {total_tweets}")

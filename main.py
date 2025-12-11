from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import uvicorn
import os
import uuid
from datetime import datetime

from scraper.core import TwitterScraper
from analytics.engine import TwitterAnalyzer
from models.data_models import Tweet, Profile

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Twitter Headless Scraper API")

# CRITICAL: Add CORS middleware FIRST, before any routes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

analyzer = TwitterAnalyzer()

# In-memory job storage (use Redis/database in production)
jobs: Dict[str, Dict[str, Any]] = {}

# Request Models
class ScrapeRequest(BaseModel):
    username: str
    max_tweets: int = 20

class AnalyticsRequest(BaseModel):
    username: str
    tweets: List[Tweet]
    profile: Optional[Profile] = None

class DiscoverRequest(BaseModel):
    usernames: List[str]

class SyncRequest(BaseModel):
    usernames: List[str]
    callback_url: str
    user_id: str

from jobs.tweet_sync import run_tweet_sync_job

@app.get("/")
def read_root():
    return {"status": "online", "service": "Twitter Headless Scraper"}

@app.get("/profile/{username}", response_model=Profile)
def get_profile(username: str):
    scraper = TwitterScraper(headless=True)
    try:
        logger.info(f"Received request to scrape profile: {username}")
        profile = scraper.scrape_profile(username)
        if not profile:
            logger.error(f"Failed to scrape profile for {username}")
            raise HTTPException(status_code=404, detail="Profile not found or scraping failed")
        logger.info(f"Successfully scraped profile: {username}")
        return profile
    except Exception as e:
        logger.error(f"Unexpected error in get_profile: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        scraper.close()

@app.post("/tweets", response_model=List[Tweet])
def get_tweets(request: ScrapeRequest):
    scraper = TwitterScraper(headless=True)
    try:
        logger.info(f"Received request to scrape tweets for: {request.username}")
        tweets = scraper.scrape_tweets(request.username, request.max_tweets)
        logger.info(f"Successfully scraped {len(tweets)} tweets for {request.username}")
        return tweets
    except Exception as e:
        logger.error(f"Unexpected error in get_tweets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        scraper.close()

@app.post("/analyze")
def analyze_tweets(request: AnalyticsRequest):
    sentiment = analyzer.analyze_sentiment(request.tweets)
    hashtags = analyzer.get_top_hashtags(request.tweets)
    
    engagement = {}
    if request.profile:
        engagement = analyzer.calculate_engagement(request.profile, request.tweets)
    
    tweet_types = analyzer.get_tweet_type_distribution(request.tweets)
    mentions = analyzer.get_top_mentions(request.tweets)
        
    return {
        "sentiment": sentiment,
        "engagement": engagement,
        "top_hashtags": hashtags,
        "top_mentions": mentions,
        "tweet_types": tweet_types
    }

class DiscoverRequest(BaseModel):
    usernames: List[str]
    user_id: Optional[str] = None
    callback_url: Optional[str] = None

def run_discovery_job(job_id: str, usernames: List[str], user_id: Optional[str] = None, callback_url: Optional[str] = None):
    """Background task to run influencer discovery"""
    try:
        jobs[job_id]["status"] = "running"
        jobs[job_id]["started_at"] = datetime.now().isoformat()
        
        logger.info("="*80)
        logger.info(f"🚀 JOB {job_id}: STARTING DISCOVERY")
        logger.info(f"📝 Usernames: {usernames}")
        logger.info("="*80)
            
        scraper = TwitterScraper(headless=True)
        discovered_profiles = []
        seen_usernames = set()
        
        try:
            # 1. Scrape Seed Profiles
            logger.info("\n" + "="*80)
            logger.info("PHASE 1: Scraping seed profiles")
            logger.info("="*80)
            
            for idx, username in enumerate(usernames, 1):
                if username in seen_usernames:
                    logger.warning(f"⚠️  [{idx}/{len(usernames)}] Skipping duplicate: @{username}")
                    continue
                    
                logger.info(f"\n🔍 [{idx}/{len(usernames)}] Scraping seed profile: @{username}")
                jobs[job_id]["progress"] = f"Scraping seed profile {idx}/{len(usernames)}: @{username}"
                
                try:
                    profile = scraper.scrape_profile(username)
                    if profile:
                        discovered_profiles.append(profile)
                        seen_usernames.add(profile.username)
                        logger.info(f"   ✅ Success! Followers: {profile.followers_count:,}")
                        
                        # Scrape and save tweets immediately if user_id and callback_url are provided
                        if user_id and callback_url:
                            try:
                                logger.info(f"   🐦 Scraping recent tweets for @{username}...")
                                tweets = scraper.scrape_tweets(username, count=10)
                                if tweets:
                                    payload = {
                                        "username": username,
                                        "tweets": [t.dict() for t in tweets],
                                        "user_id": user_id
                                    }
                                    resp = requests.post(callback_url, json=payload)
                                    if resp.status_code == 200:
                                        logger.info(f"      ✅ Saved {len(tweets)} tweets")
                                    else:
                                        logger.error(f"      ❌ Failed to save tweets: {resp.text}")
                            except Exception as te:
                                logger.error(f"      ❌ Error scraping tweets: {str(te)}")
                                
                    else:
                        logger.error(f"   ❌ Failed to scrape @{username}")
                except Exception as e:
                    logger.error(f"   ❌ Error scraping @{username}: {str(e)}")
                    
            logger.info(f"\n✅ Phase 1 complete: Scraped {len(discovered_profiles)} seed profiles")
            
            # 2. Discover Network
            logger.info("\n" + "="*80)
            logger.info("PHASE 2: Discovering network from following lists")
            logger.info("="*80)
            
            target_total = 25
            profiles_before_discovery = len(discovered_profiles)
            
            for idx, username in enumerate(usernames, 1):
                if len(discovered_profiles) >= target_total:
                    logger.info(f"\n🎯 Reached target of {target_total} profiles.")
                    break
                    
                logger.info(f"\n🔍 [{idx}/{len(usernames)}] Discovering network for: @{username}")
                jobs[job_id]["progress"] = f"Discovering network {idx}/{len(usernames)}: @{username}"
                
                try:
                    logger.info(f"   📡 Fetching following list...")
                    following = scraper.scrape_following(username, max_count=10)
                    logger.info(f"   ✅ Found {len(following)} accounts")
                    
                    count = 0
                    target_per_seed = 4
                    
                    for f_idx, p in enumerate(following, 1):
                        if p.username not in seen_usernames and len(discovered_profiles) < target_total:
                            logger.info(f"   🔎 [{f_idx}/{len(following)}] Deep scraping: @{p.username}")
                            jobs[job_id]["progress"] = f"Network {idx}/{len(usernames)}: Scraping @{p.username} ({len(discovered_profiles)}/{target_total})"
                            
                            try:
                                full_p = scraper.scrape_profile(p.username)
                                if full_p:
                                    discovered_profiles.append(full_p)
                                    seen_usernames.add(full_p.username)
                                    count += 1
                                    logger.info(f"      ✅ Added! Total: {len(discovered_profiles)}")
                                else:
                                    logger.warning(f"      ⚠️  Failed")
                            except Exception as e:
                                logger.error(f"      ❌ Error: {str(e)}")
                                
                            if count >= target_per_seed:
                                logger.info(f"   ✅ Reached {target_per_seed} from @{username}")
                                break
                                
                except Exception as e:
                    logger.error(f"   ❌ Error: {str(e)}")
            
            new_discoveries = len(discovered_profiles) - profiles_before_discovery
            logger.info(f"\n✅ Phase 2 complete: Discovered {new_discoveries} additional profiles")
                            
        finally:
            logger.info("\n🔒 Closing browser...")
            scraper.close()
            logger.info("✅ Browser closed")
            
        # Sort by followers count
        logger.info("\n📊 Sorting profiles...")
        discovered_profiles.sort(key=lambda x: x.followers_count, reverse=True)
        final_profiles = discovered_profiles[:25]
        
        logger.info("\n" + "="*80)
        logger.info(f"🎉 JOB {job_id}: COMPLETE!")
        logger.info(f"📊 Discovered: {len(discovered_profiles)}, Returning: {len(final_profiles)}")
        logger.info("="*80)
        
        # Convert to dict for JSON serialization
        profiles_dict = [p.model_dump() for p in final_profiles]
        
        jobs[job_id]["status"] = "completed"
        jobs[job_id]["result"] = profiles_dict
        jobs[job_id]["progress"] = f"Completed! Discovered {len(final_profiles)} profiles"
        jobs[job_id]["completed_at"] = datetime.now().isoformat()
        
    except Exception as e:
        logger.error(f"\n❌ JOB {job_id} FAILED: {str(e)}", exc_info=True)
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        jobs[job_id]["completed_at"] = datetime.now().isoformat()

@app.post("/discover")
def start_discovery_job(request: DiscoverRequest, background_tasks: BackgroundTasks):
    """Start a background discovery job and return job ID immediately"""
    if not request.usernames:
        raise HTTPException(status_code=400, detail="At least 1 username is required")
    
    # Create job
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id,
        "status": "pending",
        "progress": "Job created, starting soon...",
        "usernames": request.usernames,
        "created_at": datetime.now().isoformat(),
        "result": None,
        "error": None
    }
    
    # Start background task
    background_tasks.add_task(run_discovery_job, job_id, request.usernames, request.user_id, request.callback_url)
    
    logger.info(f"✅ Created job {job_id} for {len(request.usernames)} usernames")
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Discovery job started. Poll /jobs/{job_id} for status."
    }

@app.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    """Get the status of a discovery job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs[job_id]
    
    return {
        "id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "created_at": job["created_at"],
        "started_at": job.get("started_at"),
        "completed_at": job.get("completed_at"),
        "result": job.get("result") if job["status"] == "completed" else None,
        "error": job.get("error")
    }

@app.post("/sync-tweets")
def start_tweet_sync_job(request: SyncRequest, background_tasks: BackgroundTasks):
    """Start a background job to sync tweets for multiple influencers"""
    if not request.usernames:
        raise HTTPException(status_code=400, detail="Usernames list cannot be empty")
    
    # Create job
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "id": job_id,
        "status": "pending",
        "type": "sync_tweets",
        "progress": "Job created, starting soon...",
        "usernames": request.usernames,
        "created_at": datetime.now().isoformat(),
    }
    
    # Start background task
    background_tasks.add_task(run_tweet_sync_job, job_id, request.usernames, request.callback_url, request.user_id)
    
    logger.info(f"✅ Created sync job {job_id} for {len(request.usernames)} influencers")
    
    return {
        "job_id": job_id,
        "status": "pending",
        "message": "Tweet sync job started."
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

import time
import random
import logging
import re
# Patch distutils for Python 3.12+ compatibility
import sys
if sys.version_info >= (3, 12):
    import setuptools
    try:
        from setuptools import distutils
    except ImportError:
        import distutils
    sys.modules['distutils'] = distutils

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from typing import List, Optional

from .config import HEADLESS, WINDOW_SIZE, PAGE_LOAD_TIMEOUT, SCROLL_PAUSE_TIME
from .utils import parse_count, extract_hashtags, extract_mentions
from models.data_models import Profile, Tweet

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwitterScraper:
    def __init__(self, headless: bool = HEADLESS):
        self.headless = headless
        self.driver = self._setup_driver()

    def _setup_driver(self):
        options = uc.ChromeOptions()
        if self.headless:
            options.add_argument('--headless=new')
        
        options.add_argument(f'--window-size={WINDOW_SIZE}')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        
        driver = uc.Chrome(options=options)
        return driver

    def _wait_random(self, min_delay: float = 2.0, max_delay: float = 5.0):
        time.sleep(random.uniform(min_delay, max_delay))

    def _extract_profile_data(self, soup) -> dict:
        """Extract profile data from page source"""
        profile_data = {
            'full_name': None,
            'bio': None,
            'location': None,
            'website': None,
            'join_date': None,
            'followers_count': 0,
            'following_count': 0,
            'tweets_count': 0,
            'is_verified': False,
            'profile_image_url': None,
            'banner_image_url': None
        }
        
        try:
            # Log the header text to see what we're working with
            header = soup.find('div', {'data-testid': 'primaryColumn'})
            if header:
                logger.info(f"Header text found: {header.get_text()[:100]}...")
            
            # Full name
            name_tag = soup.find('div', {'data-testid': 'UserName'})
            if name_tag:
                full_name = name_tag.find('span', string=True).get_text(strip=True)
                profile_data['full_name'] = full_name
            
            # Bio/Description
            # Try standard testid, then fallback to looking for the element with dir="auto" in the header
            bio_el = soup.find('div', {'data-testid': 'UserDescription'})
            if bio_el:
                profile_data['bio'] = bio_el.get_text(strip=True)
            else:
                # Fallback: sometimes bio is just a span under the username
                # This is risky but might catch cases where testid is missing
                pass
            
            # Verification
            verified_icon = soup.find('svg', {'data-testid': 'icon-verified'})
            profile_data['is_verified'] = verified_icon is not None
            
            # Profile Image - Strict selector
            # Look for the image inside the primary column that has 'profile_images' in src
            # and is likely the main avatar (usually larger size or specific class)
            images = soup.find_all('img', src=re.compile(r'profile_images'))
            for img in images:
                src = img.get('src', '')
                # Filter out tiny avatars often found in "Followed by" sections
                if '200x200' in src or '400x400' in src:
                    profile_data['profile_image_url'] = src
                    break
            
            # Fallback for profile image if no high-res found
            if not profile_data['profile_image_url'] and images:
                profile_data['profile_image_url'] = images[0]['src']

            # Banner
            banner = soup.find('img', src=re.compile(r'profile_banners'))
            if banner:
                profile_data['banner_image_url'] = banner['src']
            
            # Location
            loc = soup.find('span', {'data-testid': 'UserLocation'})
            if loc:
                profile_data['location'] = loc.get_text(strip=True)
                
            # Join Date
            join = soup.find('span', {'data-testid': 'UserJoinDate'})
            if join:
                profile_data['join_date'] = join.get_text(strip=True)

            # Tweet Count - Try multiple strategies
            # Strategy 1: Look for "X posts" text in the header specifically
            # The header is usually a sticky bar at the top
            header_text = ""
            primary_col = soup.find('div', {'data-testid': 'primaryColumn'})
            if primary_col:
                # Get just the top part (header)
                header_div = primary_col.find('div', recursive=False)
                if header_div:
                    header_text = header_div.get_text()
            
            # If we couldn't isolate the header, just grab the first 500 chars of the body
            if not header_text:
                header_text = soup.get_text()[:500]

            logger.info(f"Scanning for tweet count in: {header_text[:100]}...")

            # Regex to find "229.5K posts" or "1,242 posts"
            # Allow for optional space, case insensitive
            # We look for a number at the start of the string or preceded by whitespace
            count_match = re.search(r'(?:^|\s)([\d,.KMB]+)\s*(?:posts|tweets)', header_text, re.IGNORECASE)
            if count_match:
                count_str = count_match.group(1)
                logger.info(f"Found tweet count match: {count_str}")
                profile_data['tweets_count'] = parse_count(count_str)
            
            # Strategy 2: Look for any element containing "posts" or "tweets" that starts with a number
            if profile_data['tweets_count'] == 0:
                candidates = soup.find_all(string=re.compile(r'\d+.*\s(posts|tweets)', re.IGNORECASE))
                for c in candidates:
                    # Check if it looks like a header count (short length)
                    if len(c) < 20:
                        match = re.search(r'([\d,.KMB]+)', c)
                        if match:
                            profile_data['tweets_count'] = parse_count(match.group(1))
                            logger.info(f"Found tweet count via text search: {match.group(1)}")
                            break
            
            # Followers/Following
            # Look for links with specific hrefs
            following_link = soup.find('a', href=re.compile(r'/following$'))
            if following_link:
                text = following_link.get_text(strip=True)
                match = re.search(r'^([\d,.KMB]+)', text)
                if match:
                    profile_data['following_count'] = parse_count(match.group(1))
            
            followers_link = soup.find('a', href=re.compile(r'/verified_followers$')) or soup.find('a', href=re.compile(r'/followers$'))
            if followers_link:
                text = followers_link.get_text(strip=True)
                match = re.search(r'^([\d,.KMB]+)', text)
                if match:
                    profile_data['followers_count'] = parse_count(match.group(1))

            logger.info(f"Extracted profile data: {profile_data}")

        except Exception as e:
            logger.error(f"Error extracting profile data: {e}")
        
        return profile_data

    def scrape_profile(self, username: str) -> Optional[Profile]:
        url = f"https://twitter.com/{username}"
        logger.info(f"Scraping profile: {url}")
        
        try:
            self.driver.get(url)
            self._wait_random(5, 7)
            
            # Scroll slightly to ensure elements load
            self.driver.execute_script("window.scrollTo(0, 150)")
            time.sleep(1)
            
            soup = BeautifulSoup(self.driver.page_source, 'lxml')
            profile_data = self._extract_profile_data(soup)
            
            return Profile(
                username=username,
                full_name=profile_data['full_name'],
                bio=profile_data['bio'],
                description=profile_data['bio'],
                location=profile_data['location'],
                website=profile_data['website'],
                join_date=profile_data['join_date'],
                followers_count=profile_data['followers_count'],
                following_count=profile_data['following_count'],
                tweets_count=profile_data['tweets_count'],
                is_verified=profile_data['is_verified'],
                profile_image_url=profile_data['profile_image_url'],
                banner_image_url=profile_data['banner_image_url']
            )
            
        except Exception as e:
            logger.error(f"Error scraping profile {username}: {e}")
            return None

    def _parse_tweet_element(self, tweet_el, username) -> Optional[Tweet]:
        """Parse a single tweet element"""
        try:
            # Debug: Log the first 100 chars of the tweet element text to see what's in there
            # logger.info(f"Raw tweet element text: {tweet_el.get_text()[:50]}...")

            # Tweet Text
            # STRICT: Only look inside data-testid="tweetText"
            text_el = tweet_el.find('div', {'data-testid': 'tweetText'})
            text = ""
            if text_el:
                text = text_el.get_text(strip=True)
            
            # If text is empty, it might be an image/video only tweet.
            # We explicitly DO NOT want to grab other text (like metrics) as fallback.
            
            # Timestamp
            time_el = tweet_el.find('time')
            timestamp = time_el['datetime'] if time_el else None
            
            # Metrics
            # Use aria-labels for most accurate counts
            likes = 0
            retweets = 0
            replies = 0
            views = 0
            
            # Helper to extract number from aria-label or text
            def extract_metric(element, pattern):
                if not element:
                    return 0
                
                # Try aria-label first
                label = element.get('aria-label', '')
                if label:
                    match = re.search(pattern, label, re.IGNORECASE)
                    if match:
                        return int(match.group(1))
                
                # Fallback: Try text content
                text = element.get_text(strip=True)
                if text:
                    # Look for simple number (e.g. "100", "1.2K")
                    # Be careful not to grab "Reply" text
                    match = re.search(r'([\d,.KMB]+)', text)
                    if match:
                        return parse_count(match.group(1))
                return 0

            # Likes
            like_el = tweet_el.find('button', {'data-testid': 'like'})
            likes = extract_metric(like_el, r'(\d+)\s+likes?')
            
            # Retweets
            rt_el = tweet_el.find('button', {'data-testid': 'retweet'})
            retweets = extract_metric(rt_el, r'(\d+)\s+reposts?')
            
            # Replies
            reply_el = tweet_el.find('button', {'data-testid': 'reply'})
            replies = extract_metric(reply_el, r'(\d+)\s+replies?')
            
            # Views (often just a link with 'analytics' in href)
            views_el = tweet_el.find('a', href=re.compile(r'/analytics'))
            if views_el:
                # Text usually "23M Views" or just "23M"
                v_text = views_el.get_text(strip=True)
                match = re.search(r'([\d,.KMB]+)', v_text)
                if match:
                    views = parse_count(match.group(1))

            # Reply info
            is_reply = False
            reply_to = None
            reply_div = tweet_el.find('div', string=re.compile(r'Replying to'))
            if reply_div:
                is_reply = True
                link = reply_div.find_next('a')
                if link:
                    reply_to = link.get_text(strip=True)

            return Tweet(
                text=text,
                username=username,
                timestamp=timestamp,
                likes=likes,
                retweets=retweets,
                replies=replies,
                views=views,
                is_reply=is_reply,
                reply_to=reply_to
            )

        except Exception as e:
            logger.error(f"Error parsing tweet: {e}")
            return None

    def scrape_tweets(self, username: str, max_tweets: int = 20) -> List[Tweet]:
        url = f"https://twitter.com/{username}"
        logger.info(f"Scraping tweets for: {username}")
        tweets = []
        seen_texts = set()  # Deduplication
        
        try:
            self.driver.get(url)
            self._wait_random(3, 5)
            
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 10
            
            while len(tweets) < max_tweets and scroll_attempts < max_scroll_attempts:
                soup = BeautifulSoup(self.driver.page_source, 'lxml')
                tweet_elements = soup.find_all('article', attrs={'data-testid': 'tweet'})
                
                for tweet_el in tweet_elements:
                    if len(tweets) >= max_tweets:
                        break
                    
                    parsed_tweet = self._parse_tweet_element(tweet_el, username)
                    if parsed_tweet and parsed_tweet.text not in seen_texts:
                        tweets.append(parsed_tweet)
                        seen_texts.add(parsed_tweet.text)
                        logger.info(f"Parsed tweet {len(tweets)}: {parsed_tweet.text[:50]}...")
                
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self._wait_random(SCROLL_PAUSE_TIME, SCROLL_PAUSE_TIME + 2)
                
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                last_height = new_height
            
            logger.info(f"Successfully scraped {len(tweets)} tweets")
            return tweets
            
        except Exception as e:
            logger.error(f"Error scraping tweets for {username}: {e}")
            return tweets

    def scrape_following(self, username: str, max_count: int = 20) -> List[Profile]:
        url = f"https://twitter.com/{username}/following"
        logger.info(f"Scraping following for: {username}")
        profiles = []
        seen_usernames = set()
        
        try:
            self.driver.get(url)
            self._wait_random(3, 5)
            
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 10
            
            while len(profiles) < max_count and scroll_attempts < max_scroll_attempts:
                soup = BeautifulSoup(self.driver.page_source, 'lxml')
                user_cells = soup.find_all('div', {'data-testid': 'UserCell'})
                
                for cell in user_cells:
                    if len(profiles) >= max_count:
                        break
                    
                    try:
                        # Extract username
                        user_link = cell.find('a', href=True)
                        if not user_link:
                            continue
                            
                        handle = user_link['href'].strip('/')
                        if handle in seen_usernames:
                            continue
                            
                        # Extract Name
                        name_div = cell.find('div', dir='auto')
                        name = name_div.get_text(strip=True) if name_div else handle
                        
                        # Extract Bio
                        bio = ""
                        # Bio is usually in a div with dir="auto" below the name, but harder to target generically without testid
                        # We'll skip bio for now or try a generic approach
                        
                        # Extract Image
                        img = cell.find('img', src=True)
                        avatar = img['src'] if img else None
                        
                        # Create Profile object (simplified)
                        profile = Profile(
                            username=handle,
                            full_name=name,
                            profile_image_url=avatar,
                            followers_count=0, # Can't easily get this from list view
                            following_count=0,
                            tweets_count=0,
                            is_verified=False
                        )
                        
                        profiles.append(profile)
                        seen_usernames.add(handle)
                        
                    except Exception as e:
                        logger.warning(f"Error parsing user cell: {e}")
                        continue
                
                # Scroll down
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                self._wait_random(SCROLL_PAUSE_TIME, SCROLL_PAUSE_TIME + 2)
                
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                last_height = new_height
                
            logger.info(f"Successfully scraped {len(profiles)} following")
            return profiles
            
        except Exception as e:
            logger.error(f"Error scraping following for {username}: {e}")
            return profiles

    def close(self):
        self.driver.quit()

import pandas as pd
from textblob import TextBlob
from typing import List, Dict, Any
from collections import Counter
from models.data_models import Tweet, Profile

class TwitterAnalyzer:
    def __init__(self):
        pass

    def analyze_sentiment(self, tweets: List[Tweet]) -> Dict[str, Any]:
        """Analyzes sentiment of tweets using TextBlob."""
        if not tweets:
            return {
                "positive_count": 0,
                "neutral_count": 0,
                "negative_count": 0,
                "positive_pct": 0,
                "neutral_pct": 0,
                "negative_pct": 0,
                "average_polarity": 0
            }

        sentiments = []
        positive = 0
        negative = 0
        neutral = 0
        
        for tweet in tweets:
            blob = TextBlob(tweet.text)
            polarity = blob.sentiment.polarity
            sentiments.append(polarity)
            
            if polarity > 0.1:
                positive += 1
            elif polarity < -0.1:
                negative += 1
            else:
                neutral += 1

        total = len(tweets)
        avg_polarity = sum(sentiments) / total if total > 0 else 0

        return {
            "positive_count": positive,
            "neutral_count": neutral,
            "negative_count": negative,
            "positive_pct": round((positive / total) * 100, 2) if total > 0 else 0,
            "neutral_pct": round((neutral / total) * 100, 2) if total > 0 else 0,
            "negative_pct": round((negative / total) * 100, 2) if total > 0 else 0,
            "average_polarity": round(avg_polarity, 4)
        }

    def calculate_engagement(self, profile: Profile, tweets: List[Tweet]) -> Dict[str, float]:
        """Calculates engagement metrics with correct formulas."""
        if not tweets:
            return {
                "engagement_rate": 0,
                "avg_likes": 0,
                "avg_retweets": 0,
                "avg_replies": 0,
                "avg_views": 0,
                "total_interactions": 0,
                "total_impressions": 0
            }

        total_likes = sum(t.likes for t in tweets)
        total_retweets = sum(t.retweets for t in tweets)
        total_replies = sum(t.replies for t in tweets)
        total_views = sum(t.views for t in tweets if t.views)
        total_interactions = total_likes + total_retweets + total_replies
        
        num_tweets = len(tweets)
        avg_likes = total_likes / num_tweets
        avg_retweets = total_retweets / num_tweets
        avg_replies = total_replies / num_tweets
        avg_views = total_views / num_tweets if total_views > 0 else 0
        
        # Corrected Engagement Rate: (Total Interactions / Total Impressions) * 100
        # If views are available, use them; otherwise use followers * num_tweets as proxy
        if total_views > 0:
            engagement_rate = (total_interactions / total_views) * 100
        else:
            # Fallback: (Total Interactions / (Followers * Num Tweets)) * 100
            followers = max(profile.followers_count, 1)
            engagement_rate = (total_interactions / (followers * num_tweets)) * 100
        
        # Conversion rate is typically engagement leading to action (like/retweet/reply relative to views)
        conversion_rate = 0
        if total_views > 0:
            conversion_rate = (total_interactions / total_views) * 100

        return {
            "engagement_rate": round(min(engagement_rate, 100), 2),  # Cap at 100%
            "conversion_rate": round(min(conversion_rate, 100), 2),
            "avg_likes": round(avg_likes, 2),
            "avg_retweets": round(avg_retweets, 2),
            "avg_replies": round(avg_replies, 2),
            "avg_views": round(avg_views, 2),
            "total_interactions": total_interactions,
            "total_impressions": total_views
        }

    def get_top_hashtags(self, tweets: List[Tweet], top_n: int = 10) -> List[tuple]:
        """Returns top N hashtags with counts."""
        all_hashtags = []
        for tweet in tweets:
            all_hashtags.extend(tweet.hashtags)
        
        return Counter(all_hashtags).most_common(top_n)
    
    def get_top_mentions(self, tweets: List[Tweet], top_n: int = 10) -> List[tuple]:
        """Returns top N mentions with counts."""
        all_mentions = []
        for tweet in tweets:
            all_mentions.extend(tweet.mentions)
        
        return Counter(all_mentions).most_common(top_n)
    
    def get_tweet_type_distribution(self, tweets: List[Tweet]) -> Dict[str, int]:
        """Calculate distribution of original tweets vs replies."""
        original = sum(1 for t in tweets if not t.is_reply)
        replies = sum(1 for t in tweets if t.is_reply)
        
        return {
            "original_tweets": original,
            "replies": replies,
            "original_pct": round((original / len(tweets)) * 100, 2) if tweets else 0,
            "replies_pct": round((replies / len(tweets)) * 100, 2) if tweets else 0
        }

    def export_to_csv(self, tweets: List[Tweet], filename: str):
        """Exports tweets to CSV."""
        df = pd.DataFrame([t.dict() for t in tweets])
        df.to_csv(filename, index=False)
        return filename

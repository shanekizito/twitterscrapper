from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class Tweet(BaseModel):
    id: Optional[str] = None
    text: str
    username: str
    full_name: Optional[str] = None
    timestamp: Optional[str] = None  # Changed to string for easier parsing
    likes: int = 0
    retweets: int = 0
    replies: int = 0
    views: Optional[int] = 0
    bookmarks: int = 0
    quotes: int = 0
    hashtags: List[str] = Field(default_factory=list)
    mentions: List[str] = Field(default_factory=list)
    media_urls: List[str] = Field(default_factory=list)
    is_verified: bool = False
    is_reply: bool = False
    reply_to: Optional[str] = None
    profile_image: Optional[str] = None
    url: Optional[str] = None

class Profile(BaseModel):
    username: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    followers_count: int = 0
    following_count: int = 0
    tweets_count: int = 0
    join_date: Optional[str] = None
    is_verified: bool = False
    profile_image_url: Optional[str] = None
    banner_image_url: Optional[str] = None
    description: Optional[str] = None  # Alias for bio

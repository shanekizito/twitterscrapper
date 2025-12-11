# Scraper Configuration

# Browser Settings
HEADLESS = True
WINDOW_SIZE = "1920,1080"
USER_AGENT_ROTATION = True

# Timeouts (seconds)
PAGE_LOAD_TIMEOUT = 30
ELEMENT_WAIT_TIMEOUT = 10
SCROLL_PAUSE_TIME = 2.0

# Selectors (2024)
SELECTORS = {
    "profile": {
        "username": '[data-testid="UserName"]',
        "description": '[data-testid="UserDescription"]',
        "join_date": '[data-testid="UserJoinDate"]',
        "followers": 'a[href$="/verified_followers"]', # Approximate, needs refinement
        "following": 'a[href$="/following"]'
    },
    "tweet": {
        "container": '[data-testid="tweet"]',
        "text": '[data-testid="tweetText"]',
        "timestamp": 'time',
        "stats": {
            "reply": '[data-testid="reply"]',
            "retweet": '[data-testid="retweet"]',
            "like": '[data-testid="like"]',
            "view": '[data-testid="app-text-transition-container"]' # Often used for views
        }
    },
    "login": {
        "username_field": 'input[autocomplete="username"]',
        "password_field": 'input[autocomplete="current-password"]',
        "next_button": '//span[text()="Next"]', # XPath often more stable for text
        "login_button": '//span[text()="Log in"]'
    }
}

# Anti-Detection
MIN_DELAY = 2
MAX_DELAY = 5

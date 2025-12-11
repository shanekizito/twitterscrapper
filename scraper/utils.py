import re
from datetime import datetime

def parse_count(count_str: str) -> int:
    """Converts string counts like '1.2K' to integers."""
    if not count_str:
        return 0
    
    count_str = count_str.strip().upper()
    multiplier = 1
    
    if count_str.endswith('K'):
        multiplier = 1000
        count_str = count_str[:-1]
    elif count_str.endswith('M'):
        multiplier = 1000000
        count_str = count_str[:-1]
    elif count_str.endswith('B'):
        multiplier = 1000000000
        count_str = count_str[:-1]
        
    try:
        return int(float(count_str.replace(',', '')) * multiplier)
    except ValueError:
        return 0

def extract_hashtags(text: str) -> list:
    """Extracts hashtags from text."""
    return re.findall(r"#(\w+)", text)

def extract_mentions(text: str) -> list:
    """Extracts mentions from text."""
    return re.findall(r"@(\w+)", text)

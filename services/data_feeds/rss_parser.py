"""RSS and SEC filing parser placeholder."""
from __future__ import annotations

from typing import List

import feedparser


def fetch_feed_entries(url: str) -> List[dict]:
    """Fetch entries from RSS feed."""
    feed = feedparser.parse(url)
    return [entry for entry in feed.entries]

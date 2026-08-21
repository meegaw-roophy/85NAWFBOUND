"""
News, Quotes, and Updates API
==============================
Provides daily quotes, countdowns, tips, and announcements.
Content is managed via JSON data file for easy updates.
"""

from fastapi import APIRouter, Depends
from app.core.deps import get_current_user
from app.db.models import User
from pydantic import BaseModel
from typing import List, Optional
import json
import os
from datetime import datetime

router = APIRouter(prefix="/news", tags=["news"])

# Path to news data file
NEWS_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "news.json")


def load_news_data():
    """Load news items from JSON file."""
    try:
        with open(NEWS_DATA_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("news_items", [])
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []


class NewsItem(BaseModel):
    id: int
    type: str  # quote, countdown, tip, announcement
    title: str
    content: str
    author: Optional[str] = None
    created_at: str
    priority: str  # high, medium, low
    deadline: Optional[str] = None


class NewsResponse(BaseModel):
    items: List[NewsItem]
    total: int


@router.get("/all", response_model=NewsResponse)
async def get_all_news(current_user: User = Depends(get_current_user)):
    """Get all news items (quotes, countdowns, tips, announcements)."""
    items = load_news_data()
    
    # Sort by created_at descending (newest first)
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return NewsResponse(
        items=[NewsItem(**item) for item in items],
        total=len(items)
    )


@router.get("/latest", response_model=NewsItem)
async def get_latest_news(current_user: User = Depends(get_current_user)):
    """Get the most recent news item."""
    items = load_news_data()
    
    if not items:
        return NewsItem(
            id=0,
            type="announcement",
            title="No updates",
            content="Check back later for new quotes, tips, and announcements.",
            created_at=datetime.utcnow().isoformat(),
            priority="low"
        )
    
    # Sort by created_at descending and return first
    items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return NewsItem(**items[0])


@router.get("/quotes", response_model=NewsResponse)
async def get_quotes(current_user: User = Depends(get_current_user)):
    """Get only quote-type news items."""
    items = load_news_data()
    quotes = [item for item in items if item.get("type") == "quote"]
    
    quotes.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return NewsResponse(
        items=[NewsItem(**item) for item in quotes],
        total=len(quotes)
    )


@router.get("/countdowns", response_model=NewsResponse)
async def get_countdowns(current_user: User = Depends(get_current_user)):
    """Get only countdown-type news items."""
    items = load_news_data()
    countdowns = [item for item in items if item.get("type") == "countdown"]
    
    countdowns.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    
    return NewsResponse(
        items=[NewsItem(**item) for item in countdowns],
        total=len(countdowns)
    )

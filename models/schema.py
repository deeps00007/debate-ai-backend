from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserProfile(BaseModel):
    user_id: str
    subscription: str = "free"
    daily_debate_count: int = 0
    last_debate_date: str = ""


class DebateSchema(BaseModel):
    debate_id: Optional[str] = None
    user_id: str
    topic: str
    difficulty: str
    status: str = "active"
    turn_count: int = 0
    created_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None


class MessageSchema(BaseModel):
    debate_id: str
    speaker: str
    text: str
    turn_index: int


class FeedbackSchema(BaseModel):
    debate_id: str
    communication_score: int
    persuasion_score: int
    logic_score: int
    words_per_minute: int
    filler_word_count: int
    total_turns: int
    summary: str
    tips: list[str]

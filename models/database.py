from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, Field, Relationship
import json

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    password_hash: str
    name: str
    role: str = Field(default="user") # 'user' or 'admin'
    tokens: int = Field(default=100)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    favorites: List["Favorite"] = Relationship(back_populates="user")
    history_records: List["SearchHistory"] = Relationship(back_populates="user")

class Video(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    platform_id: str = Field(index=True)
    platform: str
    title: Optional[str] = None
    author: str
    thumbnail_url: str
    video_url: str
    views: int = 0
    likes: int = 0
    comments: int = 0
    engagement_rate: float = 0.0
    discovered_at: datetime = Field(default_factory=datetime.utcnow)

class Favorite(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    video_url: str = Field(index=True)
    video_data: str # JSON representation of the video dict
    saved_at: datetime = Field(default_factory=datetime.utcnow)

    user: User = Relationship(back_populates="favorites")

class SearchHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    query: str
    results_count: int = 0
    preview_thumbnails: str = "[]" # JSON list of up to 4 thumbnail URLs
    searched_at: datetime = Field(default_factory=datetime.utcnow)

    user: User = Relationship(back_populates="history_records")

class RadarKeyword(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    keyword: str = Field(unique=True, index=True)
    active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

class Video(BaseModel):
    """Model representing a YouTube video."""
    
    video_id: str = Field(..., description="YouTube video ID")
    title: str = Field(..., description="Video title")
    description: Optional[str] = Field(None, description="Video description")
    published_at: datetime = Field(..., description="Publication date")
    channel_id: str = Field(..., description="Channel ID")
    view_count: Optional[int] = Field(None, description="View count")
    like_count: Optional[int] = Field(None, description="Like count") 
    comment_count: Optional[int] = Field(None, description="Comment count")
    scraped_at: datetime = Field(default_factory=datetime.now, description="Timestamp when video was scraped")

    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "dQw4w9WgXcQ",
                "title": "Rick Astley - Never Gonna Give You Up (Official Music Video)",
                "description": "Official music video for Rick Astley - Never Gonna Give You Up...",
                "published_at": "2009-10-25T06:57:33Z",
                "channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
                "view_count": 1234567890,
                "like_count": 12345678,
                "comment_count": 123456,
                "scraped_at": "2023-01-01T12:00:00Z"
            }
        }


class Comment(BaseModel):
    """Model representing a YouTube comment."""
    
    comment_id: str = Field(..., description="YouTube comment ID")
    video_id: str = Field(..., description="ID of video containing comment")
    parent_comment_id: Optional[str] = Field(None, description="ID of parent comment (for replies)")
    author: str = Field(..., description="Comment author name")
    author_channel_id: Optional[str] = Field(None, description="Comment author's channel ID")
    text: str = Field(..., description="Comment text")
    published_at: datetime = Field(..., description="Publication date")
    like_count: int = Field(0, description="Like count")
    is_reply: bool = Field(False, description="Whether this is a reply to another comment")
    scraped_at: datetime = Field(default_factory=datetime.now, description="Timestamp when comment was scraped")

    class Config:
        json_schema_extra = {
            "example": {
                "comment_id": "UgzNgVP1PI14W9CIx_x4AaABAg",
                "video_id": "dQw4w9WgXcQ",
                "parent_comment_id": None,
                "author": "Example User",
                "author_channel_id": "UCuAXFkgsw1L7xaCfnd5JJOw",
                "text": "This is a comment on the video.",
                "published_at": "2023-01-01T12:00:00Z",
                "like_count": 123,
                "is_reply": False,
                "scraped_at": "2023-01-02T12:00:00Z"
            }
        } 
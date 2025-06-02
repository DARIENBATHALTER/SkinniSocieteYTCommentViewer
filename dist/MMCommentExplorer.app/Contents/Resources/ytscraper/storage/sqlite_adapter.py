import os
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Set, Dict, Any, Optional

from ..models.data_models import Video, Comment
from .storage_adapter import StorageAdapter


class SQLiteAdapter(StorageAdapter):
    """SQLite implementation of the storage adapter."""
    
    def __init__(self, db_path: str):
        """Initialize SQLite adapter.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        if not self.db_path.parent.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = None
        self.cursor = None
    
    def initialize(self) -> None:
        """Initialize SQLite database schema."""
        self.conn = sqlite3.connect(self.db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        
        # Enable foreign keys
        self.cursor.execute("PRAGMA foreign_keys = ON")
        
        # Create videos table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            published_at TIMESTAMP NOT NULL,
            channel_id TEXT NOT NULL,
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            scraped_at TIMESTAMP NOT NULL
        )
        """)
        
        # Create comments table
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            comment_id TEXT PRIMARY KEY,
            video_id TEXT NOT NULL,
            parent_comment_id TEXT,
            author TEXT NOT NULL,
            author_channel_id TEXT,
            text TEXT NOT NULL,
            published_at TIMESTAMP NOT NULL,
            like_count INTEGER NOT NULL,
            is_reply BOOLEAN NOT NULL,
            scraped_at TIMESTAMP NOT NULL,
            FOREIGN KEY (video_id) REFERENCES videos(video_id),
            FOREIGN KEY (parent_comment_id) REFERENCES comments(comment_id)
        )
        """)
        
        # Create index on video_id in comments table
        self.cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_comments_video_id ON comments(video_id)
        """)
        
        # Create index on parent_comment_id in comments table
        self.cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON comments(parent_comment_id)
        """)
        
        # Create index on author in comments table
        self.cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_comments_author ON comments(author)
        """)
        
        self.conn.commit()
    
    def _video_to_row(self, video: Video) -> Dict[str, Any]:
        """Convert Video object to database row.
        
        Args:
            video: Video object
            
        Returns:
            Dictionary with database column values
        """
        return {
            'video_id': video.video_id,
            'title': video.title,
            'description': video.description,
            'published_at': video.published_at,
            'channel_id': video.channel_id,
            'view_count': video.view_count,
            'like_count': video.like_count,
            'comment_count': video.comment_count,
            'scraped_at': video.scraped_at
        }
    
    def _comment_to_row(self, comment: Comment) -> Dict[str, Any]:
        """Convert Comment object to database row.
        
        Args:
            comment: Comment object
            
        Returns:
            Dictionary with database column values
        """
        return {
            'comment_id': comment.comment_id,
            'video_id': comment.video_id,
            'parent_comment_id': comment.parent_comment_id,
            'author': comment.author,
            'author_channel_id': comment.author_channel_id,
            'text': comment.text,
            'published_at': comment.published_at,
            'like_count': comment.like_count,
            'is_reply': comment.is_reply,
            'scraped_at': comment.scraped_at
        }
    
    def save_videos(self, videos: List[Video]) -> None:
        """Save videos to SQLite database.
        
        Args:
            videos: List of Video objects to save
        """
        if not videos:
            return
        
        video_rows = [self._video_to_row(video) for video in videos]
        
        # Using INSERT OR REPLACE to update existing records
        placeholders = ', '.join(['?'] * len(video_rows[0]))
        columns = ', '.join(video_rows[0].keys())
        
        for video_row in video_rows:
            self.cursor.execute(
                f"INSERT OR REPLACE INTO videos ({columns}) VALUES ({placeholders})",
                list(video_row.values())
            )
        
        self.conn.commit()
    
    def save_comments(self, comments: List[Comment]) -> None:
        """Save comments to SQLite database.
        
        Args:
            comments: List of Comment objects to save
        """
        if not comments:
            return
        
        comment_rows = [self._comment_to_row(comment) for comment in comments]
        
        # Using INSERT OR REPLACE to update existing records
        placeholders = ', '.join(['?'] * len(comment_rows[0]))
        columns = ', '.join(comment_rows[0].keys())
        
        for comment_row in comment_rows:
            self.cursor.execute(
                f"INSERT OR REPLACE INTO comments ({columns}) VALUES ({placeholders})",
                list(comment_row.values())
            )
        
        self.conn.commit()
    
    def get_saved_video_ids(self) -> Set[str]:
        """Get IDs of videos that have already been saved.
        
        Returns:
            Set of saved video IDs
        """
        self.cursor.execute("SELECT video_id FROM videos")
        return {row[0] for row in self.cursor.fetchall()}
    
    def get_video_comment_count(self, video_id: str) -> int:
        """Get number of comments saved for a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Number of comments saved for the video
        """
        self.cursor.execute(
            "SELECT COUNT(*) FROM comments WHERE video_id = ?",
            (video_id,)
        )
        return self.cursor.fetchone()[0]
    
    def get_total_comment_count(self) -> int:
        """Get total number of comments saved.
        
        Returns:
            Total number of comments
        """
        self.cursor.execute("SELECT COUNT(*) FROM comments")
        return self.cursor.fetchone()[0]
    
    def get_total_video_count(self) -> int:
        """Get total number of videos saved.
        
        Returns:
            Total number of videos
        """
        self.cursor.execute("SELECT COUNT(*) FROM videos")
        return self.cursor.fetchone()[0]
    
    def search_comments(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Search comments for a query string.
        
        Args:
            query: Search query
            limit: Maximum number of results to return
            
        Returns:
            List of matching comments with video information
        """
        search_term = f"%{query}%"
        
        self.cursor.execute("""
        SELECT 
            c.comment_id, c.video_id, c.parent_comment_id, c.author, 
            c.text, c.published_at, c.like_count, c.is_reply,
            v.title as video_title, v.published_at as video_published_at
        FROM 
            comments c
        JOIN 
            videos v ON c.video_id = v.video_id
        WHERE 
            c.text LIKE ? OR c.author LIKE ?
        ORDER BY 
            c.published_at DESC
        LIMIT ?
        """, (search_term, search_term, limit))
        
        results = []
        for row in self.cursor.fetchall():
            result = dict(row)
            result['published_at'] = result['published_at'].isoformat()
            result['video_published_at'] = result['video_published_at'].isoformat()
            results.append(result)
        
        return results
    
    def close(self) -> None:
        """Close SQLite connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None 
#!/usr/bin/env python3
"""
Simple Video Scraper for Skinni Societie Comment Viewer

Scrapes comments from two specific YouTube videos:
- https://www.youtube.com/watch?v=vxBMePfysQk
- https://www.youtube.com/watch?v=2JkkwEzHIcQ
"""

import os
import sys
import logging
import sqlite3
from pathlib import Path
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("skinni_scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Target video IDs
VIDEO_IDS = [
    "vxBMePfysQk",  # Video 1
    "2JkkwEzHIcQ"   # Video 2
]

class SkinniVideoScraper:
    """Simple scraper for the two target videos."""
    
    def __init__(self, api_key):
        """Initialize the scraper with YouTube API key."""
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.db_path = Path("data/youtube_comments.db")
        self.setup_database()
    
    def setup_database(self):
        """Create database directory and tables if they don't exist."""
        self.db_path.parent.mkdir(exist_ok=True)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Create videos table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                title TEXT,
                description TEXT,
                published_at TEXT,
                duration TEXT,
                view_count INTEGER,
                like_count INTEGER,
                comment_count INTEGER,
                tags TEXT,
                category_id TEXT,
                channel_title TEXT,
                thumbnail_url TEXT,
                language TEXT
            )
        """)
        
        # Create comments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                comment_id TEXT PRIMARY KEY,
                video_id TEXT,
                parent_comment_id TEXT,
                author TEXT,
                text TEXT,
                published_at TEXT,
                updated_at TEXT,
                like_count INTEGER,
                is_reply INTEGER DEFAULT 0,
                channel_owner_liked INTEGER DEFAULT 0,
                FOREIGN KEY (video_id) REFERENCES videos (video_id)
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def get_video_details(self, video_id):
        """Get video details from YouTube API."""
        try:
            request = self.youtube.videos().list(
                part='snippet,statistics',
                id=video_id
            )
            response = request.execute()
            
            if not response.get('items'):
                logger.error(f"Video not found: {video_id}")
                return None
            
            item = response['items'][0]
            snippet = item['snippet']
            statistics = item.get('statistics', {})
            
            return {
                'video_id': video_id,
                'title': snippet['title'],
                'description': snippet.get('description', ''),
                'published_at': snippet['publishedAt'],
                'duration': '',  # Would need contentDetails for this
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'comment_count': int(statistics.get('commentCount', 0)),
                'tags': ','.join(snippet.get('tags', [])),
                'category_id': snippet.get('categoryId', ''),
                'channel_title': snippet['channelTitle'],
                'thumbnail_url': snippet['thumbnails']['high']['url'] if 'thumbnails' in snippet else '',
                'language': snippet.get('defaultLanguage', 'en')
            }
        except HttpError as e:
            logger.error(f"Error fetching video details for {video_id}: {e}")
            return None
    
    def save_video(self, video_data):
        """Save video data to database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO videos 
            (video_id, title, description, published_at, duration, view_count, 
             like_count, comment_count, tags, category_id, channel_title, 
             thumbnail_url, language)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            video_data['video_id'], video_data['title'], video_data['description'],
            video_data['published_at'], video_data['duration'], video_data['view_count'],
            video_data['like_count'], video_data['comment_count'], video_data['tags'],
            video_data['category_id'], video_data['channel_title'], 
            video_data['thumbnail_url'], video_data['language']
        ))
        
        conn.commit()
        conn.close()
        logger.info(f"Saved video: {video_data['title']}")
    
    def get_video_comments(self, video_id):
        """Get all comments for a video."""
        comments = []
        next_page = None
        
        while True:
            try:
                request = self.youtube.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    maxResults=100,
                    pageToken=next_page,
                    order='time'
                )
                response = request.execute()
                
                for item in response.get('items', []):
                    # Main comment
                    comment = item['snippet']['topLevelComment']['snippet']
                    comment_data = {
                        'comment_id': item['snippet']['topLevelComment']['id'],
                        'video_id': video_id,
                        'parent_comment_id': None,
                        'author': comment['authorDisplayName'],
                        'text': comment['textDisplay'],
                        'published_at': comment['publishedAt'],
                        'updated_at': comment.get('updatedAt', comment['publishedAt']),
                        'like_count': comment['likeCount'],
                        'is_reply': 0,
                        'channel_owner_liked': 1 if comment.get('authorChannelId', {}).get('value') else 0
                    }
                    comments.append(comment_data)
                    
                    # Replies
                    if 'replies' in item:
                        for reply_item in item['replies']['comments']:
                            reply = reply_item['snippet']
                            reply_data = {
                                'comment_id': reply_item['id'],
                                'video_id': video_id,
                                'parent_comment_id': item['snippet']['topLevelComment']['id'],
                                'author': reply['authorDisplayName'],
                                'text': reply['textDisplay'],
                                'published_at': reply['publishedAt'],
                                'updated_at': reply.get('updatedAt', reply['publishedAt']),
                                'like_count': reply['likeCount'],
                                'is_reply': 1,
                                'channel_owner_liked': 1 if reply.get('authorChannelId', {}).get('value') else 0
                            }
                            comments.append(reply_data)
                
                next_page = response.get('nextPageToken')
                if not next_page:
                    break
                    
                logger.info(f"Fetched {len(comments)} comments so far for video {video_id}")
                
            except HttpError as e:
                logger.error(f"Error fetching comments for {video_id}: {e}")
                break
        
        return comments
    
    def save_comments(self, comments):
        """Save comments to database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        for comment in comments:
            cursor.execute("""
                INSERT OR REPLACE INTO comments 
                (comment_id, video_id, parent_comment_id, author, text, 
                 published_at, updated_at, like_count, is_reply, channel_owner_liked)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                comment['comment_id'], comment['video_id'], comment['parent_comment_id'],
                comment['author'], comment['text'], comment['published_at'],
                comment['updated_at'], comment['like_count'], comment['is_reply'],
                comment['channel_owner_liked']
            ))
        
        conn.commit()
        conn.close()
        logger.info(f"Saved {len(comments)} comments to database")
    
    def scrape_videos(self):
        """Scrape all target videos."""
        logger.info("Starting Skinni Societie video scraping...")
        total_comments = 0
        
        for i, video_id in enumerate(VIDEO_IDS, 1):
            logger.info(f"Processing video {i}/{len(VIDEO_IDS)}: {video_id}")
            
            # Get video details
            video_data = self.get_video_details(video_id)
            if not video_data:
                logger.error(f"Skipping video {video_id} - could not fetch details")
                continue
            
            # Save video data
            self.save_video(video_data)
            
            # Get and save comments
            comments = self.get_video_comments(video_id)
            if comments:
                self.save_comments(comments)
                total_comments += len(comments)
            
            logger.info(f"Completed video {video_id}: {len(comments)} comments")
        
        logger.info(f"Scraping complete! Total comments: {total_comments}")
        return total_comments

def main():
    """Main entry point."""
    # Get API key from environment or .env file
    api_key = os.environ.get('YOUTUBE_API_KEY')
    
    if not api_key:
        # Try to load from .env file
        env_file = Path('.env')
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.startswith('YOUTUBE_API_KEY='):
                        api_key = line.split('=', 1)[1].strip()
                        break
    
    if not api_key:
        logger.error("YouTube API key not found. Please set YOUTUBE_API_KEY environment variable or add it to .env file")
        sys.exit(1)
    
    # Run scraper
    scraper = SkinniVideoScraper(api_key)
    try:
        total_comments = scraper.scrape_videos()
        logger.info(f"✅ Skinni Societie scraping completed successfully! Total comments: {total_comments}")
    except Exception as e:
        logger.error(f"❌ Scraping failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
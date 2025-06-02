import time
import logging
from datetime import datetime
from typing import Dict, List, Iterator, Optional, Any, Union

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from ..config.config_service import ConfigService

# Configure logger
logger = logging.getLogger(__name__)

class YouTubeApiError(Exception):
    """Base exception for YouTube API errors."""
    pass

class QuotaExceededError(YouTubeApiError):
    """Exception raised when YouTube API quota is exceeded."""
    pass

class YouTubeApiService:
    """Service for interacting with the YouTube Data API."""
    
    # YouTube API quota costs for different operations
    QUOTA_COSTS = {
        "channels.list": 1,
        "playlistItems.list": 1,
        "videos.list": 1,
        "commentThreads.list": 1,
        "comments.list": 1
    }
    
    def __init__(self, config_service: ConfigService):
        """Initialize YouTube API service.
        
        Args:
            config_service: Configuration service for API key and settings
        """
        self.config = config_service
        self.youtube = build('youtube', 'v3', developerKey=self.config.get_api_key())
        self.request_delay = self.config.get_request_delay()
    
    def _execute_api_request(self, request, operation: str) -> Dict[str, Any]:
        """Execute an API request with rate limiting and error handling.
        
        Args:
            request: The API request object
            operation: The operation name for quota tracking
            
        Returns:
            The API response
            
        Raises:
            QuotaExceededError: If the API quota is exceeded
            YouTubeApiError: For other API errors
        """
        # Check if we should stop due to quota limits
        if self.config.should_stop_for_quota():
            raise QuotaExceededError("API quota safety margin reached")
        
        # Apply rate limiting delay
        if self.request_delay > 0:
            time.sleep(self.request_delay)
        
        try:
            response = request.execute()
            
            # Update quota usage
            quota_cost = self.QUOTA_COSTS.get(operation, 1)
            self.config.update_quota_usage(quota_cost)
            
            return response
            
        except HttpError as e:
            if e.resp.status == 403 and "quotaExceeded" in str(e):
                raise QuotaExceededError(f"YouTube API quota exceeded: {e}")
            elif e.resp.status >= 500:
                # Server error, retry after delay
                logger.warning(f"YouTube API server error: {e}. Retrying after delay.")
                time.sleep(5)  # Longer delay for server errors
                return self._execute_api_request(request, operation)
            else:
                raise YouTubeApiError(f"YouTube API error: {e}")
    
    def get_channel_uploads_playlist(self, channel_id: str) -> str:
        """Get the uploads playlist ID for a channel.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            Uploads playlist ID
        """
        request = self.youtube.channels().list(
            part='contentDetails',
            id=channel_id
        )
        
        response = self._execute_api_request(request, "channels.list")
        
        if not response.get('items'):
            raise YouTubeApiError(f"Channel not found: {channel_id}")
        
        return response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    def get_videos_from_playlist(self, playlist_id: str) -> Iterator[Dict[str, Any]]:
        """Get all videos from a playlist.
        
        Args:
            playlist_id: YouTube playlist ID
            
        Yields:
            Video information dictionaries
        """
        next_page = None
        total_results = 0
        max_videos = self.config.get_max_videos()
        
        while True:
            request = self.youtube.playlistItems().list(
                part='contentDetails,snippet',
                playlistId=playlist_id,
                maxResults=50,
                pageToken=next_page
            )
            
            response = self._execute_api_request(request, "playlistItems.list")
            
            for item in response.get('items', []):
                yield {
                    'video_id': item['contentDetails']['videoId'],
                    'title': item['snippet']['title'],
                    'description': item['snippet'].get('description'),
                    'published_at': item['snippet']['publishedAt'],
                    'channel_id': item['snippet']['channelId']
                }
                
                total_results += 1
                if max_videos > 0 and total_results >= max_videos:
                    return
            
            next_page = response.get('nextPageToken')
            if not next_page:
                break
    
    def get_video_details(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """Get detailed information for videos.
        
        Args:
            video_ids: List of YouTube video IDs (up to 50)
            
        Returns:
            List of video detail dictionaries
        """
        if not video_ids:
            return []
        
        # YouTube API allows up to 50 video IDs per request
        if len(video_ids) > 50:
            video_ids = video_ids[:50]
        
        request = self.youtube.videos().list(
            part='snippet,statistics',
            id=','.join(video_ids)
        )
        
        response = self._execute_api_request(request, "videos.list")
        
        results = []
        for item in response.get('items', []):
            snippet = item['snippet']
            statistics = item.get('statistics', {})
            
            results.append({
                'video_id': item['id'],
                'title': snippet['title'],
                'description': snippet.get('description'),
                'published_at': snippet['publishedAt'],
                'channel_id': snippet['channelId'],
                'view_count': int(statistics.get('viewCount', 0)) if statistics.get('viewCount') else None,
                'like_count': int(statistics.get('likeCount', 0)) if statistics.get('likeCount') else None,
                'comment_count': int(statistics.get('commentCount', 0)) if statistics.get('commentCount') else None
            })
        
        return results
    
    def get_video_comments(self, video_id: str, include_replies: bool = False) -> Iterator[Dict[str, Any]]:
        """Get all comments for a video.
        
        Args:
            video_id: YouTube video ID
            include_replies: Whether to include replies to comments
            
        Yields:
            Comment dictionaries
        """
        next_page = None
        
        while True:
            try:
                request = self.youtube.commentThreads().list(
                    part='snippet',
                    videoId=video_id,
                    maxResults=100,
                    pageToken=next_page,
                    textFormat='plainText'
                )
                
                response = self._execute_api_request(request, "commentThreads.list")
                
                for item in response.get('items', []):
                    comment_thread_id = item['id']
                    comment = item['snippet']['topLevelComment']
                    snippet = comment['snippet']
                    
                    yield {
                        'comment_id': comment['id'],
                        'video_id': video_id,
                        'parent_comment_id': None,
                        'author': snippet.get('authorDisplayName', ''),
                        'author_channel_id': snippet.get('authorChannelId', {}).get('value'),
                        'text': snippet.get('textDisplay', ''),
                        'published_at': snippet.get('publishedAt'),
                        'like_count': snippet.get('likeCount', 0),
                        'is_reply': False
                    }
                    
                    # Get replies if requested and available
                    if include_replies and item['snippet']['totalReplyCount'] > 0:
                        yield from self._get_comment_replies(video_id, comment_thread_id)
                
                next_page = response.get('nextPageToken')
                if not next_page:
                    break
                
            except YouTubeApiError as e:
                # Log error and continue with next video if comments are disabled
                if "commentsDisabled" in str(e):
                    logger.warning(f"Comments are disabled for video {video_id}")
                    break
                else:
                    raise
    
    def _get_comment_replies(self, video_id: str, comment_thread_id: str) -> Iterator[Dict[str, Any]]:
        """Get all replies to a comment thread.
        
        Args:
            video_id: YouTube video ID
            comment_thread_id: YouTube comment thread ID
            
        Yields:
            Reply comment dictionaries
        """
        next_page = None
        
        while True:
            request = self.youtube.comments().list(
                part='snippet',
                parentId=comment_thread_id,
                maxResults=100,
                pageToken=next_page,
                textFormat='plainText'
            )
            
            response = self._execute_api_request(request, "comments.list")
            
            for item in response.get('items', []):
                snippet = item['snippet']
                
                yield {
                    'comment_id': item['id'],
                    'video_id': video_id,
                    'parent_comment_id': snippet.get('parentId'),
                    'author': snippet.get('authorDisplayName', ''),
                    'author_channel_id': snippet.get('authorChannelId', {}).get('value'),
                    'text': snippet.get('textDisplay', ''),
                    'published_at': snippet.get('publishedAt'),
                    'like_count': snippet.get('likeCount', 0),
                    'is_reply': True
                }
            
            next_page = response.get('nextPageToken')
            if not next_page:
                break 
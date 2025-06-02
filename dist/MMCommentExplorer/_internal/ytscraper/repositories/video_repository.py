import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Iterator

from ..api.youtube_api_service import YouTubeApiService
from ..models.data_models import Video
from ..storage.storage_adapter import StorageAdapter

# Configure logger
logger = logging.getLogger(__name__)

class VideoRepository:
    """Repository for fetching and storing YouTube videos."""
    
    def __init__(self, api_service: YouTubeApiService, storage: StorageAdapter):
        """Initialize video repository.
        
        Args:
            api_service: YouTube API service
            storage: Storage adapter
        """
        self.api = api_service
        self.storage = storage
        self._processed_videos = set()
    
    def get_channel_uploads_playlist(self, channel_id: str) -> str:
        """Get the uploads playlist ID for a channel.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            Uploads playlist ID
        """
        logger.info(f"Getting uploads playlist for channel: {channel_id}")
        return self.api.get_channel_uploads_playlist(channel_id)
    
    def get_videos_from_channel(self, channel_id: str, skip_existing: bool = True) -> Iterator[Video]:
        """Get all videos from a channel.
        
        Args:
            channel_id: YouTube channel ID
            skip_existing: Whether to skip videos that have already been processed
            
        Yields:
            Video objects
        """
        logger.info(f"Getting videos for channel: {channel_id}")
        
        # Get uploads playlist ID
        playlist_id = self.get_channel_uploads_playlist(channel_id)
        logger.info(f"Found uploads playlist: {playlist_id}")
        
        # Get saved video IDs from storage
        saved_video_ids = self.storage.get_saved_video_ids() if skip_existing else set()
        video_batch = []
        batch_size = 50  # YouTube API allows up to 50 video IDs per request
        
        for video_data in self.api.get_videos_from_playlist(playlist_id):
            video_id = video_data['video_id']
            
            # Skip already processed videos if requested
            if video_id in saved_video_ids or video_id in self._processed_videos:
                logger.debug(f"Skipping already processed video: {video_id}")
                continue
            
            # Add to batch for detailed info lookup
            video_batch.append(video_id)
            
            # Process batch when it reaches batch size
            if len(video_batch) >= batch_size:
                yield from self._process_video_batch(video_batch)
                video_batch = []
        
        # Process any remaining videos
        if video_batch:
            yield from self._process_video_batch(video_batch)
    
    def _process_video_batch(self, video_ids: List[str]) -> Iterator[Video]:
        """Process a batch of video IDs to get detailed information.
        
        Args:
            video_ids: List of video IDs
            
        Yields:
            Video objects with detailed information
        """
        # Get detailed video information
        videos_data = self.api.get_video_details(video_ids)
        
        for video_data in videos_data:
            # Create Video object
            try:
                published_at = datetime.fromisoformat(video_data['published_at'].replace('Z', '+00:00'))
                
                video = Video(
                    video_id=video_data['video_id'],
                    title=video_data['title'],
                    description=video_data.get('description'),
                    published_at=published_at,
                    channel_id=video_data['channel_id'],
                    view_count=video_data.get('view_count'),
                    like_count=video_data.get('like_count'),
                    comment_count=video_data.get('comment_count'),
                    scraped_at=datetime.now()
                )
                
                # Mark as processed
                self._processed_videos.add(video.video_id)
                
                yield video
                
            except Exception as e:
                logger.error(f"Error processing video {video_data.get('video_id', 'unknown')}: {e}")
    
    def save_videos(self, videos: List[Video]) -> None:
        """Save videos to storage.
        
        Args:
            videos: List of Video objects to save
        """
        if not videos:
            return
        
        logger.info(f"Saving {len(videos)} videos to storage")
        self.storage.save_videos(videos)
    
    def get_processed_video_ids(self) -> set:
        """Get IDs of videos that have been processed in this session.
        
        Returns:
            Set of processed video IDs
        """
        return self._processed_videos 
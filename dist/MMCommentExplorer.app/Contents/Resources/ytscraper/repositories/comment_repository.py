import logging
from datetime import datetime
from typing import List, Dict, Any, Iterator

from ..api.youtube_api_service import YouTubeApiService
from ..models.data_models import Comment
from ..storage.storage_adapter import StorageAdapter

# Configure logger
logger = logging.getLogger(__name__)

class CommentRepository:
    """Repository for fetching and storing YouTube comments."""
    
    def __init__(self, api_service: YouTubeApiService, storage: StorageAdapter):
        """Initialize comment repository.
        
        Args:
            api_service: YouTube API service
            storage: Storage adapter
        """
        self.api = api_service
        self.storage = storage
        self._batch_size = 100  # Number of comments to process in a batch
    
    def get_comments_for_video(self, video_id: str, include_replies: bool = False) -> Iterator[Comment]:
        """Get all comments for a video.
        
        Args:
            video_id: YouTube video ID
            include_replies: Whether to include comment replies
            
        Yields:
            Comment objects
        """
        logger.info(f"Getting comments for video: {video_id}")
        
        try:
            comment_batch = []
            
            for comment_data in self.api.get_video_comments(video_id, include_replies):
                try:
                    # Parse dates from ISO format
                    published_at = datetime.fromisoformat(comment_data['published_at'].replace('Z', '+00:00'))
                    
                    # Create Comment object
                    comment = Comment(
                        comment_id=comment_data['comment_id'],
                        video_id=comment_data['video_id'],
                        parent_comment_id=comment_data.get('parent_comment_id'),
                        author=comment_data['author'],
                        author_channel_id=comment_data.get('author_channel_id'),
                        text=comment_data['text'],
                        published_at=published_at,
                        like_count=comment_data.get('like_count', 0),
                        is_reply=comment_data.get('is_reply', False),
                        scraped_at=datetime.now()
                    )
                    
                    comment_batch.append(comment)
                    
                    # Process batch when it reaches batch size
                    if len(comment_batch) >= self._batch_size:
                        for c in comment_batch:
                            yield c
                        # Save batch
                        self.save_comments(comment_batch)
                        comment_batch = []
                        
                except Exception as e:
                    logger.error(f"Error processing comment {comment_data.get('comment_id', 'unknown')}: {e}")
                    continue
            
            # Process any remaining comments
            for c in comment_batch:
                yield c
            
            # Save final batch
            if comment_batch:
                self.save_comments(comment_batch)
                
        except Exception as e:
            logger.error(f"Error getting comments for video {video_id}: {e}")
    
    def save_comments(self, comments: List[Comment]) -> None:
        """Save comments to storage.
        
        Args:
            comments: List of Comment objects to save
        """
        if not comments:
            return
        
        logger.debug(f"Saving {len(comments)} comments to storage")
        self.storage.save_comments(comments) 
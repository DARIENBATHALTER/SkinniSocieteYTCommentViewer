from abc import ABC, abstractmethod
from typing import List, Set, Dict, Any

from ..models.data_models import Video, Comment


class StorageAdapter(ABC):
    """Abstract base class for storage adapters."""
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize storage (create tables, directories, etc.)."""
        pass
    
    @abstractmethod
    def save_videos(self, videos: List[Video]) -> None:
        """Save videos to storage.
        
        Args:
            videos: List of Video objects to save
        """
        pass
    
    @abstractmethod
    def save_comments(self, comments: List[Comment]) -> None:
        """Save comments to storage.
        
        Args:
            comments: List of Comment objects to save
        """
        pass
    
    @abstractmethod
    def get_saved_video_ids(self) -> Set[str]:
        """Get IDs of videos that have already been saved.
        
        Returns:
            Set of saved video IDs
        """
        pass
    
    @abstractmethod
    def get_video_comment_count(self, video_id: str) -> int:
        """Get number of comments saved for a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Number of comments saved for the video
        """
        pass
    
    @abstractmethod
    def get_total_comment_count(self) -> int:
        """Get total number of comments saved.
        
        Returns:
            Total number of comments
        """
        pass
    
    @abstractmethod
    def get_total_video_count(self) -> int:
        """Get total number of videos saved.
        
        Returns:
            Total number of videos
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """Close storage connections and perform cleanup."""
        pass 
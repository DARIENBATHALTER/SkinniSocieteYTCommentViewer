import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Set, Dict, Any, Optional, Union

from ..models.data_models import Video, Comment
from .storage_adapter import StorageAdapter


class JSONAdapter(StorageAdapter):
    """JSON implementation of the storage adapter."""
    
    def __init__(self, storage_path: str, use_jsonl: bool = False):
        """Initialize JSON adapter.
        
        Args:
            storage_path: Directory for JSON files
            use_jsonl: Whether to use JSONL format (line-delimited JSON)
        """
        self.storage_path = Path(storage_path)
        self.use_jsonl = use_jsonl
        
        self.videos_file = self.storage_path / ("videos.jsonl" if use_jsonl else "videos.json")
        self.comments_file = self.storage_path / ("comments.jsonl" if use_jsonl else "comments.json")
        
        # In-memory cache of saved video IDs for faster lookups
        self._saved_video_ids = set()
        self._comment_counts = {}
        self._total_comment_count = 0
    
    def initialize(self) -> None:
        """Initialize JSON storage."""
        # Create directory if it doesn't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # If files exist, load existing data to build cache
        if self.videos_file.exists():
            self._load_video_cache()
        
        if self.comments_file.exists():
            self._load_comment_counts()
    
    def _load_video_cache(self) -> None:
        """Load video IDs from existing JSON file into cache."""
        if not self.videos_file.exists():
            return
        
        if self.use_jsonl:
            with open(self.videos_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        video = json.loads(line)
                        self._saved_video_ids.add(video['video_id'])
                    except json.JSONDecodeError:
                        continue
        else:
            try:
                with open(self.videos_file, 'r', encoding='utf-8') as f:
                    videos = json.load(f)
                    self._saved_video_ids = {v['video_id'] for v in videos}
            except (json.JSONDecodeError, FileNotFoundError):
                self._saved_video_ids = set()
    
    def _load_comment_counts(self) -> None:
        """Load comment counts from existing JSON file into cache."""
        if not self.comments_file.exists():
            return
        
        comment_counts = {}
        total_count = 0
        
        if self.use_jsonl:
            with open(self.comments_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        comment = json.loads(line)
                        video_id = comment['video_id']
                        comment_counts[video_id] = comment_counts.get(video_id, 0) + 1
                        total_count += 1
                    except json.JSONDecodeError:
                        continue
        else:
            try:
                with open(self.comments_file, 'r', encoding='utf-8') as f:
                    comments = json.load(f)
                    for comment in comments:
                        video_id = comment['video_id']
                        comment_counts[video_id] = comment_counts.get(video_id, 0) + 1
                        total_count += 1
            except (json.JSONDecodeError, FileNotFoundError):
                pass
        
        self._comment_counts = comment_counts
        self._total_comment_count = total_count
    
    def _model_to_dict(self, model: Union[Video, Comment]) -> Dict[str, Any]:
        """Convert model to dictionary with serializable values.
        
        Args:
            model: Pydantic model
            
        Returns:
            Dictionary with serialized values
        """
        data = model.model_dump()
        
        # Convert datetime objects to ISO format strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        
        return data
    
    def save_videos(self, videos: List[Video]) -> None:
        """Save videos to JSON file.
        
        Args:
            videos: List of Video objects to save
        """
        if not videos:
            return
        
        # Convert videos to dictionaries
        video_dicts = [self._model_to_dict(video) for video in videos]
        
        if self.use_jsonl:
            # Append to JSONL file
            with open(self.videos_file, 'a', encoding='utf-8') as f:
                for video in video_dicts:
                    # Update cache
                    self._saved_video_ids.add(video['video_id'])
                    f.write(json.dumps(video) + '\n')
        else:
            # Load existing data, update, and save
            existing_videos = []
            if self.videos_file.exists():
                try:
                    with open(self.videos_file, 'r', encoding='utf-8') as f:
                        existing_videos = json.load(f)
                except json.JSONDecodeError:
                    existing_videos = []
            
            # Create lookup of existing videos
            existing_video_dict = {v['video_id']: v for v in existing_videos}
            
            # Update existing videos or add new ones
            for video in video_dicts:
                existing_video_dict[video['video_id']] = video
                self._saved_video_ids.add(video['video_id'])
            
            # Write back to file
            with open(self.videos_file, 'w', encoding='utf-8') as f:
                json.dump(list(existing_video_dict.values()), f, ensure_ascii=False, indent=2)
    
    def save_comments(self, comments: List[Comment]) -> None:
        """Save comments to JSON file.
        
        Args:
            comments: List of Comment objects to save
        """
        if not comments:
            return
        
        # Convert comments to dictionaries
        comment_dicts = [self._model_to_dict(comment) for comment in comments]
        
        if self.use_jsonl:
            # Append to JSONL file
            with open(self.comments_file, 'a', encoding='utf-8') as f:
                for comment in comment_dicts:
                    # Update cache
                    video_id = comment['video_id']
                    self._comment_counts[video_id] = self._comment_counts.get(video_id, 0) + 1
                    self._total_comment_count += 1
                    f.write(json.dumps(comment) + '\n')
        else:
            # Load existing data, update, and save
            existing_comments = []
            if self.comments_file.exists():
                try:
                    with open(self.comments_file, 'r', encoding='utf-8') as f:
                        existing_comments = json.load(f)
                except json.JSONDecodeError:
                    existing_comments = []
            
            # Create lookup of existing comments
            existing_comment_dict = {c['comment_id']: c for c in existing_comments}
            
            # Update existing comments or add new ones
            for comment in comment_dicts:
                if comment['comment_id'] not in existing_comment_dict:
                    # This is a new comment
                    video_id = comment['video_id']
                    self._comment_counts[video_id] = self._comment_counts.get(video_id, 0) + 1
                    self._total_comment_count += 1
                
                existing_comment_dict[comment['comment_id']] = comment
            
            # Write back to file
            with open(self.comments_file, 'w', encoding='utf-8') as f:
                json.dump(list(existing_comment_dict.values()), f, ensure_ascii=False, indent=2)
    
    def get_saved_video_ids(self) -> Set[str]:
        """Get IDs of videos that have already been saved.
        
        Returns:
            Set of saved video IDs
        """
        return self._saved_video_ids
    
    def get_video_comment_count(self, video_id: str) -> int:
        """Get number of comments saved for a video.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Number of comments saved for the video
        """
        return self._comment_counts.get(video_id, 0)
    
    def get_total_comment_count(self) -> int:
        """Get total number of comments saved.
        
        Returns:
            Total number of comments
        """
        return self._total_comment_count
    
    def get_total_video_count(self) -> int:
        """Get total number of videos saved.
        
        Returns:
            Total number of videos
        """
        return len(self._saved_video_ids)
    
    def close(self) -> None:
        """Clean up resources."""
        # JSON adapter doesn't need to close any connections
        pass 
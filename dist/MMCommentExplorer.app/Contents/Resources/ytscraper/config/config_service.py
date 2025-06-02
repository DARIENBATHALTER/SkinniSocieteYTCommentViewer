import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

class ConfigService:
    """Service for managing configuration and runtime state."""
    
    def __init__(self, env_file: str = None):
        """Initialize configuration service.
        
        Args:
            env_file: Optional path to .env file
        """
        # Load environment variables
        load_dotenv(env_file)
        
        # Initialize quota tracking
        self._quota_used = 0
        self._checkpoint_file = Path("checkpoint.json")
        
        # Create data directory if it doesn't exist
        data_dir = Path(self.get_storage_path())
        data_dir.mkdir(parents=True, exist_ok=True)
    
    def get_api_key(self) -> str:
        """Get YouTube API key from environment."""
        api_key = os.getenv("YOUTUBE_API_KEY")
        if not api_key:
            raise ValueError("YOUTUBE_API_KEY not set in environment variables")
        return api_key
    
    def get_storage_type(self) -> str:
        """Get storage type from environment."""
        return os.getenv("STORAGE_TYPE", "sqlite")
    
    def get_storage_path(self) -> str:
        """Get storage path from environment."""
        return os.getenv("STORAGE_PATH", "data")
    
    def get_include_replies(self) -> bool:
        """Whether to include comment replies."""
        return os.getenv("INCLUDE_REPLIES", "false").lower() == "true"
    
    def get_max_videos(self) -> int:
        """Get maximum number of videos to process (0 = unlimited)."""
        return int(os.getenv("MAX_VIDEOS", "0"))
    
    def get_request_delay(self) -> float:
        """Get delay between API requests in seconds."""
        return float(os.getenv("REQUEST_DELAY", "0.5"))
    
    def get_quota_limit(self) -> int:
        """Get daily quota limit."""
        return int(os.getenv("QUOTA_LIMIT", "10000"))
    
    def get_quota_safety_margin(self) -> int:
        """Get quota safety margin."""
        return int(os.getenv("QUOTA_SAFETY_MARGIN", "500"))
    
    def get_quota_remaining(self) -> int:
        """Get remaining API quota."""
        return self.get_quota_limit() - self._quota_used
    
    def should_stop_for_quota(self) -> bool:
        """Check if scraping should stop due to quota limits."""
        return self.get_quota_remaining() <= self.get_quota_safety_margin()
    
    def update_quota_usage(self, units: int) -> None:
        """Update quota usage.
        
        Args:
            units: Number of quota units to add to usage
        """
        self._quota_used += units
    
    def get_checkpoint(self) -> Dict[str, Any]:
        """Get checkpoint data for resuming scraping."""
        if not self._checkpoint_file.exists():
            return {"processed_videos": [], "quota_used": 0}
        
        try:
            with open(self._checkpoint_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {"processed_videos": [], "quota_used": 0}
    
    def save_checkpoint(self, processed_videos: list, additional_data: Optional[Dict] = None) -> None:
        """Save checkpoint data for resuming scraping.
        
        Args:
            processed_videos: List of processed video IDs
            additional_data: Additional data to save in checkpoint
        """
        checkpoint_data = {
            "processed_videos": processed_videos,
            "quota_used": self._quota_used
        }
        
        if additional_data:
            checkpoint_data.update(additional_data)
        
        with open(self._checkpoint_file, "w") as f:
            json.dump(checkpoint_data, f) 
import logging
import time
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

from tqdm import tqdm

from .api.youtube_api_service import YouTubeApiService, QuotaExceededError
from .config.config_service import ConfigService
from .models.data_models import Video, Comment
from .repositories.video_repository import VideoRepository
from .repositories.comment_repository import CommentRepository
from .storage.storage_adapter import StorageAdapter
from .storage.storage_factory import StorageFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("ytscraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class YouTubeScraper:
    """Main class for orchestrating the YouTube scraping process."""
    
    def __init__(self, config_service: Optional[ConfigService] = None, env_file: Optional[str] = None):
        """Initialize the YouTube scraper.
        
        Args:
            config_service: Optional pre-configured ConfigService
            env_file: Optional path to .env file for configuration
        """
        # Flag for graceful shutdown
        self.should_stop = False
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        
        # Initialize components
        self.config = config_service or ConfigService(env_file)
        self.api = YouTubeApiService(self.config)
        self.storage = StorageFactory.create_storage_adapter(self.config)
        self.storage.initialize()
        
        self.video_repo = VideoRepository(self.api, self.storage)
        self.comment_repo = CommentRepository(self.api, self.storage)
        
        # Load checkpoint if resuming
        checkpoint = self.config.get_checkpoint()
        self._processed_videos = set(checkpoint.get('processed_videos', []))
        if checkpoint.get('quota_used'):
            # Restore quota usage from checkpoint
            self.config._quota_used = checkpoint.get('quota_used', 0)
        
        logger.info(f"Initialized scraper with {len(self._processed_videos)} previously processed videos")
        logger.info(f"Current quota usage: {self.config._quota_used}/{self.config.get_quota_limit()}")
    
    def _handle_signal(self, signum, frame):
        """Handle termination signals to allow graceful shutdown.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.should_stop = True
    
    def scrape_channel(self, channel_id: str) -> None:
        """Scrape all videos and comments from a YouTube channel.
        
        Args:
            channel_id: YouTube channel ID
        """
        logger.info(f"Starting scrape of channel: {channel_id}")
        start_time = time.time()
        
        try:
            # First get all videos
            videos = list(self._get_videos(channel_id))
            
            if not videos:
                logger.warning(f"No new videos found for channel {channel_id}")
                return
            
            logger.info(f"Found {len(videos)} new videos to process")
            
            # Then get comments for each video
            comment_count = self._get_comments_for_videos(videos)
            
            # Save checkpoint
            self._save_checkpoint()
            
            # Log results
            elapsed_time = time.time() - start_time
            logger.info(f"Scrape complete in {elapsed_time:.2f} seconds")
            logger.info(f"Processed {len(videos)} videos with {comment_count} comments")
            logger.info(f"Total videos in storage: {self.storage.get_total_video_count()}")
            logger.info(f"Total comments in storage: {self.storage.get_total_comment_count()}")
            logger.info(f"Remaining API quota: {self.config.get_quota_remaining()}/{self.config.get_quota_limit()}")
            
        except QuotaExceededError as e:
            logger.warning(f"API quota exceeded: {e}")
            logger.info("Saving checkpoint for resuming later")
            self._save_checkpoint()
            
        except Exception as e:
            logger.error(f"Error scraping channel {channel_id}: {e}", exc_info=True)
            logger.info("Saving checkpoint for resuming later")
            self._save_checkpoint()
            
        finally:
            # Ensure storage is closed properly
            self.storage.close()
    
    def _get_videos(self, channel_id: str) -> List[Video]:
        """Get videos from a channel.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            List of Video objects
        """
        videos = []
        batch_size = 10  # Save every 10 videos
        video_batch = []
        
        try:
            # Create progress bar for videos
            with tqdm(desc="Fetching videos", unit="video") as pbar:
                for video in self.video_repo.get_videos_from_channel(channel_id):
                    # Skip already processed videos
                    if video.video_id in self._processed_videos:
                        continue
                    
                    video_batch.append(video)
                    videos.append(video)
                    self._processed_videos.add(video.video_id)
                    pbar.update(1)
                    
                    # Save batch periodically
                    if len(video_batch) >= batch_size:
                        self.video_repo.save_videos(video_batch)
                        video_batch = []
                        self._save_checkpoint()
                    
                    # Check if we should stop
                    if self.should_stop or self.config.should_stop_for_quota():
                        logger.info("Stopping video fetch due to interrupt or quota limit")
                        break
            
            # Save any remaining videos
            if video_batch:
                self.video_repo.save_videos(video_batch)
                
        except Exception as e:
            logger.error(f"Error fetching videos: {e}", exc_info=True)
            # Save what we have so far
            if video_batch:
                self.video_repo.save_videos(video_batch)
            
        return videos
    
    def _get_comments_for_videos(self, videos: List[Video]) -> int:
        """Get comments for a list of videos.
        
        Args:
            videos: List of Video objects
            
        Returns:
            Total number of comments processed
        """
        total_comments = 0
        include_replies = self.config.get_include_replies()
        
        try:
            # Create progress bar for videos
            with tqdm(total=len(videos), desc="Fetching comments", unit="video") as pbar:
                for video in videos:
                    video_comment_count = 0
                    
                    # Get comments for video
                    for comment in self.comment_repo.get_comments_for_video(video.video_id, include_replies):
                        video_comment_count += 1
                        total_comments += 1
                    
                    logger.info(f"Processed {video_comment_count} comments for video {video.video_id}")
                    pbar.update(1)
                    
                    # Save checkpoint periodically
                    if total_comments % 1000 == 0:
                        self._save_checkpoint()
                    
                    # Check if we should stop
                    if self.should_stop or self.config.should_stop_for_quota():
                        logger.info("Stopping comment fetch due to interrupt or quota limit")
                        break
                        
        except Exception as e:
            logger.error(f"Error fetching comments: {e}", exc_info=True)
        
        return total_comments
    
    def _save_checkpoint(self) -> None:
        """Save checkpoint for resuming later."""
        logger.debug("Saving checkpoint")
        self.config.save_checkpoint(list(self._processed_videos))


def main():
    """Main entry point for the scraper."""
    if len(sys.argv) < 2:
        print("Usage: python -m ytscraper <channel_id> [env_file]")
        sys.exit(1)
        
    channel_id = sys.argv[1]
    env_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    scraper = YouTubeScraper(env_file=env_file)
    scraper.scrape_channel(channel_id)


if __name__ == "__main__":
    main() 
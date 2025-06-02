#!/usr/bin/env python3
"""
YouTube Comment Scraper

A tool to scrape all comments from a YouTube channel's videos.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

from ytscraper.scraper import YouTubeScraper

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Scrape comments from all videos on a YouTube channel"
    )
    parser.add_argument(
        "channel_id",
        help="YouTube channel ID to scrape (e.g., 'UCUORv_qpgmg8N5plVqlYjXg')"
    )
    parser.add_argument(
        "-e", "--env-file",
        help="Path to .env file with configuration"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "-c", "--create-env",
        action="store_true",
        help="Create a template .env file if it doesn't exist"
    )
    
    return parser.parse_args()

def create_env_template():
    """Create a template .env file."""
    env_file = Path(".env")
    
    if env_file.exists():
        print(f".env file already exists at {env_file.absolute()}")
        return
    
    template = """# YouTube API Key (required)
YOUTUBE_API_KEY=your_api_key_here

# Storage configuration
STORAGE_TYPE=sqlite  # Options: sqlite, json, jsonl
STORAGE_PATH=data    # Directory for output files

# Scraper configuration
INCLUDE_REPLIES=false  # Whether to fetch replies to comments
MAX_VIDEOS=0           # 0 = no limit, otherwise limit to this number
REQUEST_DELAY=0.5      # Delay between API requests in seconds

# Quota management
QUOTA_LIMIT=10000      # Daily quota limit (default for YouTube API)
QUOTA_SAFETY_MARGIN=500  # Stop when remaining quota falls below this
"""
    
    with open(env_file, "w") as f:
        f.write(template)
    
    print(f"Created template .env file at {env_file.absolute()}")
    print("Please edit it to add your YouTube API key and adjust settings as needed.")

def main():
    """Main entry point."""
    args = parse_args()
    
    # Create .env template if requested
    if args.create_env:
        create_env_template()
        if not os.path.exists(".env"):
            return
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("ytscraper.log"),
            logging.StreamHandler()
        ]
    )
    
    # Run the scraper
    try:
        scraper = YouTubeScraper(env_file=args.env_file)
        scraper.scrape_channel(args.channel_id)
    except KeyboardInterrupt:
        print("\nScraping interrupted by user. Progress has been saved.")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
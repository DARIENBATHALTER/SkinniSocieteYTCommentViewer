import os
import json
import sqlite3
import threading
import uuid
import sys
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, render_template, jsonify, request, g, send_file, send_from_directory
import logging
import time
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# PostgreSQL support for Heroku
try:
    import psycopg2
    from urllib.parse import urlparse
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

# Import scraper components
from ytscraper.scraper import YouTubeScraper
from ytscraper.config.config_service import ConfigService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = DATABASE_URL and POSTGRES_AVAILABLE

if USE_POSTGRES:
    logger.info("🐘 Using PostgreSQL database (Heroku)")
    # Parse DATABASE_URL for PostgreSQL
    url = urlparse(DATABASE_URL)
    DB_CONFIG = {
        'host': url.hostname,
        'port': url.port,
        'user': url.username,
        'password': url.password,
        'database': url.path[1:]  # Remove leading slash
    }
else:
    logger.info("🗃️  Using SQLite database (local)")
    # Determine the base directory for data files
    def get_base_dir():
        """Get the base directory for data files, works in both dev and bundled environments"""
        try:
            if getattr(sys, 'frozen', False):
                # Running in PyInstaller bundle
                return Path(sys._MEIPASS)
            else:
                # Running in development
                return Path(__file__).parent
        except Exception as e:
            logger.error(f"Error determining base directory: {e}")
            # Fallback to current directory
            return Path.cwd()

    BASE_DIR = get_base_dir()
    DB_PATH = str(BASE_DIR / "data" / "youtube_comments.db")
    
    print(f"🗃️  Database path: {DB_PATH}")
    print(f"📁 Base directory: {BASE_DIR}")

    # Verify database exists
    if not os.path.exists(DB_PATH):
        logger.warning(f"⚠️  Database not found at: {DB_PATH}")
        logger.warning(f"📂 Contents of base directory: {list(BASE_DIR.iterdir()) if BASE_DIR.exists() else 'Base dir does not exist'}")
        if (BASE_DIR / "data").exists():
            logger.warning(f"📂 Contents of data directory: {list((BASE_DIR / 'data').iterdir())}")
        logger.warning("🔄 App will start anyway - database may be created later")
    else:
        logger.info(f"✅ Database found at: {DB_PATH}")

app = Flask(__name__)

# Global variables for scraping progress
scraping_status = {
    'active': False,
    'progress': 0,
    'total': 0,
    'current_task': '',
    'logs': [],
    'start_time': None,
    'error': None
}

# Medical Medium Channel ID (from the scraped data)
MEDICAL_MEDIUM_CHANNEL_ID = "UCUORv_qpgmg8N5plVqlYjXg"

def get_db():
    """Get database connection"""
    db = getattr(g, '_database', None)
    if db is None:
        try:
            if USE_POSTGRES:
                db = g._database = psycopg2.connect(**DB_CONFIG)
                # PostgreSQL doesn't have row_factory, we'll handle this in queries
            else:
                db = g._database = sqlite3.connect(DB_PATH)
                db.row_factory = sqlite3.Row
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            if USE_POSTGRES:
                logger.error(f"📍 PostgreSQL connection details: {DB_CONFIG['host']}:{DB_CONFIG['port']}")
            else:
                logger.error(f"📍 Attempted SQLite path: {DB_PATH}")
            # Return None so endpoints can handle the failure gracefully
            return None
    return db

def dict_from_row(row, cursor=None):
    """Convert database row to dictionary, handling both SQLite and PostgreSQL"""
    if USE_POSTGRES and cursor:
        # PostgreSQL: use cursor description to get column names
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    else:
        # SQLite: row is already dict-like due to row_factory
        return dict(row)

def adapt_query(query):
    """Adapt query syntax for the database type"""
    if USE_POSTGRES:
        # Convert SQLite ? placeholders to PostgreSQL %s
        placeholder_count = query.count('?')
        for i in range(placeholder_count):
            query = query.replace('?', '%s', 1)
    return query

@app.teardown_appcontext
def close_connection(exception):
    """Close database connection when app context ends"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    """Serve the main SPA page"""
    return render_template('index.html')

@app.route('/api/videos')
def get_videos():
    """Get all videos with pagination"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 20, type=int)
    offset = (page - 1) * limit
    sort_by = request.args.get('sort_by', 'published_at')
    sort_order = request.args.get('sort_order', 'desc')
    search = request.args.get('search', '')
    
    # Validate sort parameters
    valid_sort_fields = ['published_at', 'view_count', 'comment_count']
    valid_sort_orders = ['asc', 'desc']
    
    if sort_by not in valid_sort_fields:
        sort_by = 'published_at'
    if sort_order not in valid_sort_orders:
        sort_order = 'desc'
    
    db = get_db()
    cursor = db.cursor()
    
    # Build the query
    count_query = "SELECT COUNT(*) FROM videos"
    query = f"""
        SELECT 
            video_id, title, description, published_at, 
            view_count, like_count, comment_count
        FROM 
            videos
    """
    
    params = []
    
    # Add search if provided
    if search:
        search_condition = " WHERE title LIKE ? OR description LIKE ?"
        count_query += search_condition
        query += search_condition
        params.extend([f"%{search}%", f"%{search}%"])
    
    # Add sorting
    query += f" ORDER BY {sort_by} {sort_order}"
    
    # Add pagination
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    # Get total count
    if search:
        cursor.execute(count_query, [f"%{search}%", f"%{search}%"])
    else:
        cursor.execute(count_query)
    total = cursor.fetchone()[0]
    
    # Get videos
    cursor.execute(query, params)
    
    videos = []
    for row in cursor.fetchall():
        video = dict(row)
        # Convert datetime to string for JSON serialization
        if isinstance(video['published_at'], datetime):
            video['published_at'] = video['published_at'].isoformat()
        # Add thumbnail URL
        video['thumbnail'] = f"https://img.youtube.com/vi/{video['video_id']}/mqdefault.jpg"
        videos.append(video)
    
    return jsonify({
        'videos': videos,
        'total': total,
        'page': page,
        'limit': limit,
        'pages': (total + limit - 1) // limit,
        'sort_by': sort_by,
        'sort_order': sort_order
    })

@app.route('/api/videos/<video_id>/comments')
def get_comments(video_id):
    """Get comments for a specific video with filtering"""
    # Get query parameters
    search = request.args.get('search', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)
    sort_by_likes = request.args.get('sort_by_likes', 'desc')  # Default to most liked
    has_replies = request.args.get('has_replies', '') == 'true'
    include_replies = request.args.get('include_replies', 'true') == 'true'
    debug_mode = request.args.get('debug', '') == 'true'
    
    db = get_db()
    cursor = db.cursor()
    
    # Debug: Check database schema and sample data
    cursor.execute("PRAGMA table_info(comments)")
    columns = [column[1] for column in cursor.fetchall()]
    print(f"Comments table columns: {columns}")
    
    # Check if is_reply field exists
    has_is_reply_field = 'is_reply' in columns
    
    # Sample some comments with parent-child relationships
    cursor.execute("""
        SELECT comment_id, parent_comment_id, is_reply, author, substr(text, 1, 50) as sample_text
        FROM comments 
        WHERE video_id = ? 
        ORDER BY parent_comment_id IS NOT NULL DESC
        LIMIT 20
    """, [video_id])
    sample_comments = cursor.fetchall()
    if debug_mode:
        print(f"Sample comments for video {video_id}: {[dict(r) for r in sample_comments]}")
    
    # Get a sample of parent comment IDs to check if they exist
    parent_ids = set()
    for comment in sample_comments:
        if comment['parent_comment_id']:
            parent_ids.add(comment['parent_comment_id'])
    
    if parent_ids and debug_mode:
        placeholders = ','.join('?' for _ in parent_ids)
        cursor.execute(f"""
            SELECT comment_id, parent_comment_id, is_reply, author
            FROM comments 
            WHERE comment_id IN ({placeholders})
        """, list(parent_ids))
        parent_comments = cursor.fetchall()
        print(f"Parent comments lookup: {[dict(r) for r in parent_comments]}")
    
    # Count total replies for this video
    cursor.execute("""
        SELECT COUNT(*) 
        FROM comments 
        WHERE video_id = ? AND parent_comment_id IS NOT NULL AND parent_comment_id != ''
    """, [video_id])
    total_replies = cursor.fetchone()[0]
    print(f"Total replies for video {video_id}: {total_replies}")
    
    # Count comments with replies
    cursor.execute("""
        SELECT COUNT(*) FROM comments c
        WHERE c.video_id = ? AND EXISTS (
            SELECT 1 FROM comments child 
            WHERE child.parent_comment_id = c.comment_id
        )
    """, [video_id])
    comments_with_replies = cursor.fetchone()[0]
    print(f"Comments with replies for video {video_id}: {comments_with_replies}")
    
    # Check if author_channel_id column exists (for channel owner likes)
    has_author_channel_id = 'author_channel_id' in columns
    
    # Build query
    query = """
        SELECT 
            c.comment_id, c.video_id, c.parent_comment_id, c.author, 
            c.text, c.published_at, c.like_count
    """
    
    # Add is_reply field if it exists
    if has_is_reply_field:
        query += ", c.is_reply"
    else:
        query += ", CASE WHEN c.parent_comment_id IS NOT NULL AND c.parent_comment_id != '' THEN 1 ELSE 0 END as is_reply"
    
    # Check if channel owner likes field exists and add it to the query
    channel_likes_join = ""
    if 'channel_owner_liked' in columns:
        query += ", c.channel_owner_liked"
    
    query += """
        FROM 
            comments c
        WHERE 
            c.video_id = ?
    """
    
    # Only get top-level comments if we're including replies separately
    if include_replies:
        query += " AND (c.parent_comment_id IS NULL OR c.parent_comment_id = '')"
    
    params = [video_id]
    
    # Add search filter if provided
    if search:
        query += " AND c.text LIKE ?"
        params.append(f"%{search}%")
    
    # Add date filters if provided
    if start_date:
        query += " AND c.published_at >= ?"
        params.append(start_date)
    if end_date:
        query += " AND c.published_at <= ?"
        params.append(end_date)
    
    # Add filter for comments with replies
    if has_replies:
        # Check if there are actual reply comments in the database
        check_query = """
            SELECT COUNT(*) FROM comments 
            WHERE video_id = ? AND parent_comment_id IS NOT NULL AND parent_comment_id != ''
        """
        cursor.execute(check_query, [video_id])
        reply_count = cursor.fetchone()[0]
        print(f"Reply count from check_query: {reply_count}")
        
        if reply_count > 0:
            query += """ AND EXISTS (
                SELECT 1 FROM comments child 
                WHERE child.parent_comment_id = c.comment_id
            )"""
        else:
            # If no replies exist, add an impossible condition to return no results
            # when the filter is applied but no replies exist
            if debug_mode:
                print("No replies exist, adding impossible condition")
            query += " AND 0 = 1"
    
    # Add order, limit and offset
    print(f"Sorting by: {sort_by_likes}")
    
    if sort_by_likes == 'desc':
        query += " ORDER BY c.like_count DESC, c.published_at DESC"
        print("Sorting by most likes")
    elif sort_by_likes == 'asc':
        query += " ORDER BY c.like_count ASC, c.published_at DESC"
        print("Sorting by least likes")
    elif sort_by_likes == 'recent' or sort_by_likes == '':
        query += " ORDER BY c.published_at DESC"
        print("Sorting by most recent")
    else:
        query += " ORDER BY c.published_at DESC"
        print(f"Unknown sort value: {sort_by_likes}, defaulting to most recent")
    
    query += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    
    if debug_mode:
        print(f"Main query: {query}")
        print(f"Params: {params}")
    
    cursor.execute(query, params)
    
    comments = []
    for row in cursor.fetchall():
        comment = dict(row)
        # Convert datetime to string for JSON serialization
        if isinstance(comment['published_at'], datetime):
            comment['published_at'] = comment['published_at'].isoformat()
        
        # Check if comment has replies
        cursor.execute(
            "SELECT COUNT(*) FROM comments WHERE parent_comment_id = ?",
            (comment['comment_id'],)
        )
        reply_count = cursor.fetchone()[0]
        comment['has_replies'] = reply_count > 0
        comment['reply_count'] = reply_count
        
        # Get replies if needed
        if include_replies and reply_count > 0:
            replies_query = """
                SELECT 
                    comment_id, video_id, parent_comment_id, author,
                    text, published_at, like_count
            """
            
            # Add is_reply field if it exists
            if has_is_reply_field:
                replies_query += ", is_reply"
            else:
                replies_query += ", 1 as is_reply"
            
            # Add channel owner likes field if it exists
            if 'channel_owner_liked' in columns:
                replies_query += ", channel_owner_liked"
                
            replies_query += """
                FROM comments
                WHERE parent_comment_id = ?
                ORDER BY published_at ASC
            """
            
            if debug_mode:
                print(f"Replies query for comment {comment['comment_id']}: {replies_query}")
            cursor.execute(replies_query, (comment['comment_id'],))
            
            replies = []
            for reply_row in cursor.fetchall():
                reply = dict(reply_row)
                # Convert datetime to string for JSON serialization
                if isinstance(reply['published_at'], datetime):
                    reply['published_at'] = reply['published_at'].isoformat()
                
                replies.append(reply)
                
            comment['replies'] = replies
            if debug_mode:
                print(f"Found {len(replies)} replies for comment {comment['comment_id']}")
        else:
            comment['replies'] = []
        
        comments.append(comment)
    
    # Get total count for this video - ALWAYS count ALL comments (not just top-level)
    count_query = "SELECT COUNT(*) FROM comments WHERE video_id = ?"
    count_params = [video_id]
    
    # Apply the same filters to count query (but NOT the include_replies filter)
    if search:
        count_query += " AND text LIKE ?"
        count_params.append(f"%{search}%")
    
    if start_date:
        count_query += " AND published_at >= ?"
        count_params.append(start_date)
    if end_date:
        count_query += " AND published_at <= ?"
        count_params.append(end_date)
    
    # Only apply has_replies filter if explicitly requested
    if has_replies:
        if reply_count > 0:
            count_query += """ AND EXISTS (
                SELECT 1 FROM comments child 
                WHERE child.parent_comment_id = comments.comment_id
            )"""
        else:
            count_query += " AND 0 = 1"
    
    cursor.execute(count_query, count_params)
    total = cursor.fetchone()[0]
    
    # Get channel info to determine channel owner
    cursor.execute("SELECT channel_id FROM videos WHERE video_id = ?", (video_id,))
    row = cursor.fetchone()
    channel_id = row['channel_id'] if row else None
    
    response_data = {
        'comments': comments,
        'total': total,
        'video_id': video_id,
        'channel_id': channel_id,
        'has_channel_owner_liked_data': 'channel_owner_liked' in columns,
        'total_replies_in_video': total_replies,
        'comments_with_replies': comments_with_replies
    }
    
    return jsonify(response_data)

@app.route('/api/videos/<video_id>')
def get_video(video_id):
    """Get details for a specific video"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("""
        SELECT 
            video_id, title, description, published_at, 
            view_count, like_count, comment_count, channel_id
        FROM 
            videos
        WHERE 
            video_id = ?
    """, (video_id,))
    
    row = cursor.fetchone()
    if not row:
        return jsonify({'error': 'Video not found'}), 404
    
    video = dict(row)
    # Convert datetime to string for JSON serialization
    if isinstance(video['published_at'], datetime):
        video['published_at'] = video['published_at'].isoformat()
    # Add thumbnail URL
    video['thumbnail'] = f"https://img.youtube.com/vi/{video['video_id']}/mqdefault.jpg"
    
    return jsonify(video)

@app.route('/api/videos/comment-data/<comment_id>')
def get_comment_data(comment_id):
    """Get comment data for client-side PNG generation"""
    db = get_db()
    cursor = db.cursor()
    
    # First check what columns exist in the comments table
    cursor.execute("PRAGMA table_info(comments)")
    columns = [column[1] for column in cursor.fetchall()]
    has_channel_owner_liked = 'channel_owner_liked' in columns
    
    # Build query based on available columns
    base_query = """
        SELECT 
            c.comment_id, c.video_id, c.parent_comment_id, c.author, 
            c.text, c.published_at, c.like_count
    """
    
    if 'is_reply' in columns:
        base_query += ", c.is_reply"
    else:
        base_query += ", CASE WHEN c.parent_comment_id IS NOT NULL AND c.parent_comment_id != '' THEN 1 ELSE 0 END as is_reply"
    
    if has_channel_owner_liked:
        base_query += ", c.channel_owner_liked"
    
    base_query += """, v.title as video_title
        FROM 
            comments c
        JOIN 
            videos v ON c.video_id = v.video_id
        WHERE 
            c.comment_id = ?
    """
    
    cursor.execute(base_query, (comment_id,))
    
    row = cursor.fetchone()
    if not row:
        return jsonify({'error': 'Comment not found'}), 404
    
    comment = dict(row)
    # Convert datetime to string for JSON serialization
    if isinstance(comment['published_at'], datetime):
        comment['published_at'] = comment['published_at'].isoformat()
    
    # Set channel_owner_liked if not present
    if not has_channel_owner_liked:
        comment['channel_owner_liked'] = False
    else:
        comment['channel_owner_liked'] = bool(comment.get('channel_owner_liked', False))
    
    return jsonify(comment)

def format_number(num):
    """Format large numbers with K, M suffixes"""
    if num is None:
        return "0"
    
    num = int(num)
    if num < 1000:
        return str(num)
    elif num < 1000000:
        return f"{num/1000:.1f}K".replace('.0K', 'K')
    else:
        return f"{num/1000000:.1f}M".replace('.0M', 'M')

@app.template_filter('format_number')
def format_number_filter(num):
    return format_number(num)

# Scraping API endpoints
class ScrapingLogHandler(logging.Handler):
    """Custom log handler to capture scraper logs"""
    def emit(self, record):
        global scraping_status
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'level': record.levelname,
            'message': self.format(record)
        }
        scraping_status['logs'].append(log_entry)
        # Keep only last 100 log entries
        if len(scraping_status['logs']) > 100:
            scraping_status['logs'] = scraping_status['logs'][-100:]

def run_scraper():
    """Run the scraper in a background thread"""
    global scraping_status
    
    try:
        scraping_status.update({
            'active': True,
            'progress': 0,
            'total': 0,
            'current_task': 'Initializing scraper...',
            'logs': [],
            'start_time': datetime.now().isoformat(),
            'error': None
        })
        
        # Set up logging to capture scraper output
        logger = logging.getLogger('ytscraper')
        logger.setLevel(logging.INFO)
        handler = ScrapingLogHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(handler)
        
        # Initialize scraper - but avoid signal handlers in threads
        # Check if API key is available (should be set by launcher when bundled)
        api_key = os.environ.get('YOUTUBE_API_KEY')
        if not api_key:
            # API key not found - try loading .env file for development mode
            if not getattr(sys, 'frozen', False):
                logger.info("Running in development mode - attempting to load .env file")
                try:
                    from dotenv import load_dotenv
                    load_dotenv('.env')
                    api_key = os.environ.get('YOUTUBE_API_KEY')
                    if api_key:
                        logger.info(f"API key loaded from .env file (length: {len(api_key)} chars)")
                    else:
                        logger.error("YOUTUBE_API_KEY not found in .env file")
                except Exception as e:
                    logger.error(f"Error loading .env file: {e}")
            
            if not api_key:
                logger.error("YOUTUBE_API_KEY not found in environment variables")
                logger.error("Make sure the API key is properly configured")
                raise ValueError("YOUTUBE_API_KEY not found in environment variables")
        else:
            logger.info(f"API key found and loaded (length: {len(api_key)} chars)")
        
        # Initialize ConfigService (pass None to avoid dotenv issues)
        config = ConfigService(None)
        
        # Create a custom scraper class that doesn't use signals
        class ThreadSafeScraper(YouTubeScraper):
            def __init__(self, config_service):
                # Initialize without signal handlers
                self.should_stop = False
                self.config = config_service
                from ytscraper.api.youtube_api_service import YouTubeApiService
                from ytscraper.storage.storage_factory import StorageFactory
                from ytscraper.repositories.video_repository import VideoRepository
                from ytscraper.repositories.comment_repository import CommentRepository
                
                self.api = YouTubeApiService(self.config)
                self.storage = StorageFactory.create_storage_adapter(self.config)
                self.storage.initialize()
                
                self.video_repo = VideoRepository(self.api, self.storage)
                self.comment_repo = CommentRepository(self.api, self.storage)
                
                # Load checkpoint if resuming
                checkpoint = self.config.get_checkpoint()
                self._processed_videos = set(checkpoint.get('processed_videos', []))
                if checkpoint.get('quota_used'):
                    self.config._quota_used = checkpoint.get('quota_used', 0)
                
                logger.info(f"Initialized scraper with {len(self._processed_videos)} previously processed videos")
                logger.info(f"Current quota usage: {self.config._quota_used}/{self.config.get_quota_limit()}")
            
            def get_newest_video_date(self):
                """Get the published date of the newest video in the database"""
                try:
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    
                    cursor.execute("""
                        SELECT published_at 
                        FROM videos 
                        ORDER BY published_at DESC 
                        LIMIT 1
                    """)
                    
                    result = cursor.fetchone()
                    conn.close()
                    
                    if result:
                        # Parse the datetime string
                        return datetime.fromisoformat(result[0].replace('Z', '+00:00'))
                    return None
                    
                except Exception as e:
                    print(f"Error getting newest video date: {e}")
                    return None
            
            def smart_video_check(self, channel_id):
                """Only fetch videos newer than our most recent video"""
                newest_date = self.get_newest_video_date()
                
                if newest_date is None:
                    logger.info("No existing videos - performing full channel fetch")
                    return list(self.video_repo.get_videos_from_channel(channel_id))
                
                logger.info(f"Checking for videos newer than {newest_date}")
                scraping_status['current_task'] = f'Checking for new videos since {newest_date.strftime("%Y-%m-%d")}...'
                
                new_videos = []
                videos_checked = 0
                
                # Get videos from channel and stop when we reach our newest video
                for video in self.video_repo.get_videos_from_channel(channel_id):
                    videos_checked += 1
                    video_date = video.published_at
                    
                    # If video is newer than our newest, add it
                    if video_date > newest_date:
                        new_videos.append(video)
                        logger.info(f"Found new video: {video.title} ({video_date})")
                    else:
                        # We've reached videos we already have - stop checking
                        logger.info(f"Reached existing videos at {video_date} - stopping check")
                        break
                    
                    # Update progress
                    scraping_status['current_task'] = f'Checked {videos_checked} videos, found {len(new_videos)} new ones...'
                
                logger.info(f"Smart check complete: {len(new_videos)} new videos found after checking {videos_checked} videos")
                return new_videos
            
            def scrape_channel_smart(self, channel_id):
                """Smart channel scraping - only new content"""
                logger.info(f"Starting smart scrape of channel: {channel_id}")
                
                # Step 1: Get only new videos
                new_videos = self.smart_video_check(channel_id)
                videos_with_updates = []
                
                # Save new videos first
                if new_videos:
                    logger.info(f"Saving {len(new_videos)} new videos")
                    self.video_repo.save_videos(new_videos)
                    for video in new_videos:
                        self._processed_videos.add(video.video_id)
                    videos_with_updates.extend(new_videos)
                
                # Step 2: Check existing videos for new comments
                logger.info("Checking existing videos for new comments...")
                scraping_status['current_task'] = 'Checking existing videos for new comments...'
                
                existing_videos_with_new_comments = self.check_existing_videos_for_new_comments()
                if existing_videos_with_new_comments:
                    videos_with_updates.extend(existing_videos_with_new_comments)
                
                # Step 3: Process all videos that need comment updates
                if not videos_with_updates:
                    logger.info("No new videos or comment updates found")
                    scraping_status.update({
                        'active': False,
                        'current_task': 'No new content found. Channel is up to date!',
                        'progress': 100
                    })
                    return
                
                # Get comments for all videos that need updates
                logger.info(f"Processing {len(videos_with_updates)} videos with new/updated content")
                self._get_comments_for_videos_with_progress(videos_with_updates)
                
                # Save checkpoint
                self._save_checkpoint()
                
                logger.info(f"Smart scrape complete: {len(new_videos)} new videos + {len(existing_videos_with_new_comments)} existing videos with new comments processed")
            
            def check_existing_videos_for_new_comments(self):
                """Check existing videos in database for new comments by comparing comment counts"""
                videos_needing_updates = []
                
                try:
                    import sqlite3
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    
                    # Get all existing videos and their current comment counts
                    cursor.execute("""
                        SELECT video_id, title, comment_count 
                        FROM videos 
                        ORDER BY published_at DESC
                    """)
                    existing_videos = cursor.fetchall()
                    conn.close()
                    
                    logger.info(f"Checking {len(existing_videos)} existing videos for comment updates...")
                    
                    for idx, (video_id, title, stored_comment_count) in enumerate(existing_videos):
                        try:
                            # Update progress periodically
                            if idx % 10 == 0:
                                progress = int((idx / len(existing_videos)) * 100)
                                scraping_status.update({
                                    'current_task': f'Checking video {idx + 1}/{len(existing_videos)} for new comments...',
                                    'progress': progress
                                })
                            
                            # Get current video info from YouTube API to check comment count
                            video_data = self.api.get_video_details([video_id])
                            if not video_data:
                                continue
                                
                            # Handle both dictionary and object access patterns
                            video_info = video_data[0]
                            if hasattr(video_info, 'comment_count'):
                                current_comment_count = video_info.comment_count
                            elif isinstance(video_info, dict):
                                current_comment_count = video_info.get('comment_count', 0)
                            else:
                                logger.warning(f"Unexpected video data format for {video_id}")
                                continue
                                
                            stored_comment_count = stored_comment_count or 0
                            
                            # If YouTube has more comments than we have stored, this video needs updating
                            if current_comment_count > stored_comment_count:
                                logger.info(f"Video '{title[:50]}' has new comments: {stored_comment_count} -> {current_comment_count}")
                                videos_needing_updates.append(video_info)
                            
                            # Small delay to avoid hitting API limits
                            time.sleep(0.1)
                            
                        except Exception as e:
                            logger.error(f"Error checking video {video_id}: {e}")
                            continue
                    
                    logger.info(f"Found {len(videos_needing_updates)} existing videos with new comments")
                    return videos_needing_updates
                    
                except Exception as e:
                    logger.error(f"Error checking existing videos: {e}")
                    return []
            
            def _get_comments_for_videos_with_progress(self, videos):
                """Get comments with proper progress tracking"""
                if not videos:
                    return
                
                total_videos = len(videos)
                processed_videos = 0
                
                logger.info(f"Processing comments for {total_videos} videos")
                
                for video_index, video in enumerate(videos):
                    try:
                        # Handle both dictionary and object access patterns
                        if hasattr(video, 'title'):
                            video_title = video.title
                            video_id = video.video_id
                        elif isinstance(video, dict):
                            video_title = video.get('title', 'Unknown Title')
                            video_id = video.get('video_id', '')
                        else:
                            logger.warning(f"Unexpected video format at index {video_index}")
                            continue
                        
                        scraping_status['current_task'] = f'Processing video {video_index + 1}/{total_videos}: {video_title[:50]}...'
                        
                        # Update overall progress
                        overall_progress = int((video_index / total_videos) * 100)
                        scraping_status.update({
                            'progress': overall_progress,
                            'total': total_videos,
                            'current_video': video_index + 1
                        })
                        
                        comment_count = 0
                        for comment in self.comment_repo.get_comments_for_video(video_id, self.config.get_include_replies()):
                            comment_count += 1
                            
                            # Update comment progress periodically
                            if comment_count % 50 == 0:
                                scraping_status['current_task'] = f'Video {video_index + 1}/{total_videos}: {video_title[:30]}... ({comment_count} comments)'
                        
                        processed_videos += 1
                        logger.info(f"Processed {comment_count} comments for video: {video_title}")
                        
                        # Update final progress for this video
                        final_progress = int((processed_videos / total_videos) * 100)
                        scraping_status.update({
                            'progress': final_progress,
                            'current_task': f'Completed {processed_videos}/{total_videos} videos ({final_progress}%)'
                        })
                        
                    except Exception as e:
                        logger.error(f"Error processing video {getattr(video, 'title', 'unknown')}: {e}")
                        continue
                
                scraping_status.update({
                    'progress': 100,
                    'current_task': f'Completed! Processed {processed_videos} videos with new comments.'
                })
        
        scraper = ThreadSafeScraper(config)
        
        scraping_status['current_task'] = 'Checking for new videos and comments...'
        
        # Add informative logging about the smart scraping process
        logger.info("Smart update process:")
        logger.info("• Checking YouTube API for new videos since last update")
        logger.info("• Comparing comment counts to detect new comments")
        logger.info("• Only downloading new content (not re-scraping existing)")
        logger.info(f"• Resume from checkpoint: {len(scraper._processed_videos)} videos already processed")
        
        scraping_status['current_task'] = 'Fetching only new videos and comments...'
        
        # Run the smart scraper (only new content)
        scraper.scrape_channel_smart(MEDICAL_MEDIUM_CHANNEL_ID)
        
        scraping_status.update({
            'active': False,
            'current_task': 'Comment update completed successfully!',
            'progress': 100
        })
        
    except Exception as e:
        scraping_status.update({
            'active': False,
            'error': str(e),
            'current_task': f'Update failed: {str(e)}'
        })
        logger.error(f"Scraping error: {e}", exc_info=True)

@app.route('/api/scraper/start', methods=['POST'])
def start_scraper():
    """Start a new scraping task"""
    global scraping_status
    
    if scraping_status['active']:
        return jsonify({'error': 'Comment update is already in progress'}), 400
    
    # Start scraper in background thread
    thread = threading.Thread(target=run_scraper, daemon=True)
    thread.start()
    
    return jsonify({'message': 'Comment update started', 'status': scraping_status})

@app.route('/api/scraper/status')
def get_scraper_status():
    """Get current scraping status and logs"""
    global scraping_status
    return jsonify(scraping_status)

@app.route('/api/scraper/stop', methods=['POST'])
def stop_scraper():
    """Stop the current scraping task"""
    global scraping_status
    
    if not scraping_status['active']:
        return jsonify({'error': 'No update in progress'}), 400
    
    scraping_status.update({
        'active': False,
        'current_task': 'Comment update stopped by user',
        'error': 'Stopped by user'
    })
    
    return jsonify({'message': 'Comment update stopped', 'status': scraping_status})

# Ensure directories exist for proper app operation
try:
    # Create templates directory if it doesn't exist
    templates_dir = BASE_DIR / "templates"
    if not templates_dir.exists():
        logger.warning(f"Templates directory not found at: {templates_dir}")
        # Try to find templates in the bundle
        if getattr(sys, 'frozen', False):
            # In bundle, templates might be in Resources
            bundle_templates = BASE_DIR / ".." / "Resources" / "templates"
            if bundle_templates.exists():
                logger.info(f"Found templates in bundle at: {bundle_templates}")
            else:
                logger.warning("Templates not found in expected bundle locations")
    
    # Create temp exports directory if possible
    temp_dir = BASE_DIR / "temp_exports"
    temp_dir.mkdir(exist_ok=True, parents=True)
    logger.info("✅ Directory initialization complete")
    
except Exception as e:
    logger.warning(f"⚠️  Directory creation warning: {e}")
    logger.warning("🔄 App will continue anyway")

if __name__ == '__main__':
    # Get port from environment variable (Heroku sets this)
    port = int(os.environ.get('PORT', 9191))
    
    # Check if database exists - but don't exit if it doesn't (for web deployment)
    if not os.path.exists(DB_PATH):
        print(f"Warning: Database not found at {DB_PATH}")
        print("Database will be created when scraper runs or can be uploaded separately.")
    
    # Start the Flask server
    app.run(debug=False, host='0.0.0.0', port=port) 
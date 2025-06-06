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

# PostgreSQL support for Heroku
try:
    import psycopg2
    from urllib.parse import urlparse
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database configuration - Support both SQLite and PostgreSQL
DATABASE_URL = os.environ.get('DATABASE_URL')
USE_POSTGRES = DATABASE_URL and DATABASE_URL.startswith('postgresql://')

if USE_POSTGRES:
    # PostgreSQL configuration for production (Render)
    try:
        url = urlparse(DATABASE_URL)
        DB_CONFIG = {
            'host': url.hostname,
            'database': url.path[1:],
            'user': url.username,
            'password': url.password,
            'port': url.port
        }
        logger.info(f"🐘 Using PostgreSQL database: {url.hostname}:{url.port}/{url.path[1:]}")
        print(f"🐘 PostgreSQL configured for production deployment")
    except ImportError:
        logger.error("❌ psycopg2 not available for PostgreSQL connection")
        raise ImportError("psycopg2-binary required for PostgreSQL support")
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

# Skinni Societie target video IDs
TARGET_VIDEO_IDS = [
    "vxBMePfysQk",  # TikTok's Skinny-Obsessed Community
    "2JkkwEzHIcQ"   # Skinny Influencer Liv Schmidt
]

def init_postgres_tables():
    """Initialize PostgreSQL tables if they don't exist"""
    if not USE_POSTGRES:
        return
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Create videos table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                video_id VARCHAR(255) PRIMARY KEY,
                title TEXT,
                description TEXT,
                published_at TIMESTAMP,
                duration VARCHAR(50),
                view_count BIGINT,
                like_count BIGINT,
                comment_count BIGINT,
                tags TEXT,
                category_id VARCHAR(50),
                channel_title VARCHAR(255),
                thumbnail_url TEXT,
                language VARCHAR(10)
            )
        """)
        
        # Create comments table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS comments (
                comment_id VARCHAR(255) PRIMARY KEY,
                video_id VARCHAR(255),
                parent_comment_id VARCHAR(255),
                author VARCHAR(255),
                text TEXT,
                published_at TIMESTAMP,
                updated_at TIMESTAMP,
                like_count INTEGER,
                is_reply BOOLEAN DEFAULT FALSE,
                channel_owner_liked BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (video_id) REFERENCES videos (video_id)
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_video_id ON comments (video_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON comments (parent_comment_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_published_at ON videos (published_at)")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        logger.info("✅ PostgreSQL tables initialized successfully")
        
    except Exception as e:
        logger.error(f"❌ Error initializing PostgreSQL tables: {e}")
        raise

# Initialize database tables
if USE_POSTGRES:
    init_postgres_tables()

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
    """Close database connection"""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/videos')
def get_videos():
    """Get all videos with pagination and filtering"""
    try:
        db = get_db()
        if db is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = db.cursor()
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort', 'published_at')
        order = request.args.get('order', 'desc')
        
        # Validate sort parameters
        valid_sorts = ['published_at', 'title', 'view_count', 'like_count', 'comment_count']
        if sort_by not in valid_sorts:
            sort_by = 'published_at'
        
        if order not in ['asc', 'desc']:
            order = 'desc'
        
        # Build base query
        base_query = """
            SELECT video_id, title, description, published_at, duration, 
                   view_count, like_count, comment_count, tags, category_id,
                   channel_title, thumbnail_url, language
            FROM videos
        """
        
        # Add search filter if provided
        params = []
        if search:
            base_query += " WHERE title LIKE ?"
            params.append(f'%{search}%')
        
        # Add ordering
        base_query += f" ORDER BY {sort_by} {order.upper()}"
        
        # Adapt query for database type
        base_query = adapt_query(base_query)
        
        # Get total count for pagination
        count_query = "SELECT COUNT(*) FROM videos"
        if search:
            count_query += " WHERE title LIKE ?"
            count_query = adapt_query(count_query)
            cursor.execute(count_query, params[:1])  # Only search param for count
        else:
            cursor.execute(count_query)
        
        total_count = cursor.fetchone()[0]
        
        # Calculate pagination
        offset = (page - 1) * per_page
        total_pages = (total_count + per_page - 1) // per_page
        
        # Add pagination to main query
        paginated_query = base_query + f" LIMIT ? OFFSET ?"
        paginated_query = adapt_query(paginated_query)
        params.extend([per_page, offset])
        
        # Execute main query
        cursor.execute(paginated_query, params)
        
        # Fetch results and convert to dictionaries
        videos = []
        for row in cursor.fetchall():
            video = dict_from_row(row, cursor)
            
            # Format dates and numbers
            if video.get('published_at'):
                try:
                    # Handle different date formats
                    date_str = video['published_at']
                    if isinstance(date_str, str):
                        # Remove timezone info if present for consistent parsing
                        if 'T' in date_str:
                            date_str = date_str.replace('Z', '').split('T')[0]
                        video['published_at'] = date_str
                except Exception as e:
                    logger.warning(f"Date parsing error for video {video.get('video_id')}: {e}")
            
            # Format numbers
            for field in ['view_count', 'like_count', 'comment_count']:
                if video.get(field) is not None:
                    video[field] = int(video[field]) if video[field] else 0
            
            videos.append(video)
        
        return jsonify({
            'videos': videos,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages
            },
            'search': search,
            'sort': sort_by,
            'order': order
        })
        
    except Exception as e:
        logger.error(f"❌ Error fetching videos: {e}")
        return jsonify({'error': 'Failed to fetch videos'}), 500

@app.route('/api/videos/<video_id>/comments')
def get_comments(video_id):
    """Get comments for a specific video with pagination and filtering"""
    try:
        db = get_db()
        if db is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = db.cursor()
        
        # Get pagination and filter parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        search = request.args.get('search', '').strip()
        sort_by = request.args.get('sort', 'published_at')
        order = request.args.get('order', 'desc')
        min_likes = request.args.get('min_likes', 0, type=int)
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        
        # Validate sort parameters
        valid_sorts = ['published_at', 'like_count', 'author']
        if sort_by not in valid_sorts:
            sort_by = 'published_at'
            
        if order not in ['asc', 'desc']:
            order = 'desc'
        
        # Build query for main comments (not replies)
        base_query = """
            SELECT comment_id, video_id, parent_comment_id, author, text, 
                   published_at, updated_at, like_count, is_reply, channel_owner_liked
            FROM comments 
            WHERE video_id = ? AND (parent_comment_id IS NULL OR parent_comment_id = '')
        """
        
        # Build parameters list
        params = [video_id]
        
        # Add filters
        if search:
            base_query += " AND (text LIKE ? OR author LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])
        
        if min_likes > 0:
            base_query += " AND like_count >= ?"
            params.append(min_likes)
        
        if start_date:
            base_query += " AND published_at >= ?"
            params.append(start_date)
        
        if end_date:
            base_query += " AND published_at <= ?"
            params.append(end_date)
        
        # Add ordering
        base_query += f" ORDER BY {sort_by} {order.upper()}"
        
        # Adapt query for database type
        base_query = adapt_query(base_query)
        
        # Get total count for pagination
        count_query = """
            SELECT COUNT(*) FROM comments 
            WHERE video_id = ? AND (parent_comment_id IS NULL OR parent_comment_id = '')
        """
        count_params = [video_id]
        
        if search:
            count_query += " AND (text LIKE ? OR author LIKE ?)"
            count_params.extend([f'%{search}%', f'%{search}%'])
        
        if min_likes > 0:
            count_query += " AND like_count >= ?"
            count_params.append(min_likes)
        
        if start_date:
            count_query += " AND published_at >= ?"
            count_params.append(start_date)
        
        if end_date:
            count_query += " AND published_at <= ?"
            count_params.append(end_date)
        
        count_query = adapt_query(count_query)
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]
        
        # Calculate pagination
        offset = (page - 1) * per_page
        total_pages = (total_count + per_page - 1) // per_page
        
        # Add pagination to main query
        paginated_query = base_query + " LIMIT ? OFFSET ?"
        paginated_query = adapt_query(paginated_query)
        params.extend([per_page, offset])
        
        # Execute main query
        cursor.execute(paginated_query, params)
        
        # Fetch main comments
        comments = []
        for row in cursor.fetchall():
            comment = dict_from_row(row, cursor)
            
            # Format like count
            comment['like_count'] = int(comment['like_count']) if comment['like_count'] else 0
            
            # Get replies for this comment
            replies_query = """
                SELECT comment_id, video_id, parent_comment_id, author, text, 
                       published_at, updated_at, like_count, is_reply, channel_owner_liked
                FROM comments 
                WHERE video_id = ? AND parent_comment_id = ?
                ORDER BY published_at ASC
            """
            replies_query = adapt_query(replies_query)
            cursor.execute(replies_query, [video_id, comment['comment_id']])
            
            replies = []
            for reply_row in cursor.fetchall():
                reply = dict_from_row(reply_row, cursor)
                reply['like_count'] = int(reply['like_count']) if reply['like_count'] else 0
                replies.append(reply)
            
            comment['replies'] = replies
            comments.append(comment)
        
        # Get video info
        video_query = "SELECT title FROM videos WHERE video_id = ?"
        video_query = adapt_query(video_query)
        cursor.execute(video_query, [video_id])
        video_row = cursor.fetchone()
        video_title = video_row[0] if video_row else "Unknown Video"
        
        return jsonify({
            'comments': comments,
            'video_title': video_title,
            'video_id': video_id,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total_count,
                'pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages
            },
            'filters': {
                'search': search,
                'sort': sort_by,
                'order': order,
                'min_likes': min_likes,
                'start_date': start_date,
                'end_date': end_date
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error fetching comments for video {video_id}: {e}")
        return jsonify({'error': 'Failed to fetch comments'}), 500

@app.route('/api/videos/<video_id>')
def get_video(video_id):
    """Get details for a specific video"""
    try:
        db = get_db()
        if db is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = db.cursor()
        
        query = """
            SELECT video_id, title, description, published_at, duration, 
                   view_count, like_count, comment_count, tags, category_id,
                   channel_title, thumbnail_url, language
            FROM videos 
            WHERE video_id = ?
        """
        query = adapt_query(query)
        cursor.execute(query, [video_id])
        
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Video not found'}), 404
        
        video = dict_from_row(row, cursor)
        
        # Format numbers
        for field in ['view_count', 'like_count', 'comment_count']:
            if video.get(field) is not None:
                video[field] = int(video[field]) if video[field] else 0
        
        return jsonify(video)
        
    except Exception as e:
        logger.error(f"❌ Error fetching video {video_id}: {e}")
        return jsonify({'error': 'Failed to fetch video'}), 500

@app.route('/api/videos/comment-data/<comment_id>')
def get_comment_data(comment_id):
    """Get comment data for export (including video info)"""
    try:
        db = get_db()
        if db is None:
            return jsonify({'error': 'Database connection failed'}), 500
        
        cursor = db.cursor()
        
        # Get comment with video info
        query = """
            SELECT c.comment_id, c.video_id, c.parent_comment_id, c.author, c.text,
                   c.published_at, c.updated_at, c.like_count, c.is_reply, c.channel_owner_liked,
                   v.title as video_title, v.channel_title
            FROM comments c
            JOIN videos v ON c.video_id = v.video_id
            WHERE c.comment_id = ?
        """
        query = adapt_query(query)
        cursor.execute(query, [comment_id])
        
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': 'Comment not found'}), 404
        
        comment = dict_from_row(row, cursor)
        comment['like_count'] = int(comment['like_count']) if comment['like_count'] else 0
        
        return jsonify(comment)
        
    except Exception as e:
        logger.error(f"❌ Error fetching comment {comment_id}: {e}")
        return jsonify({'error': 'Failed to fetch comment'}), 500

# Utility functions
def format_number(num):
    """Format numbers with K/M suffixes"""
    if num is None:
        return "0"
    
    try:
        num = int(num)
        if num >= 1000000:
            return f"{num / 1000000:.1f}M"
        elif num >= 1000:
            return f"{num / 1000:.1f}K"
        else:
            return str(num)
    except (ValueError, TypeError):
        return "0"

@app.template_filter('format_number')
def format_number_filter(num):
    """Template filter for formatting numbers"""
    return format_number(num)

# Ensure directories exist for proper app operation
try:
    # Create templates directory if it doesn't exist
    templates_dir = BASE_DIR / "templates" if not USE_POSTGRES else Path("templates")
    if not templates_dir.exists() and not USE_POSTGRES:
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
    if not USE_POSTGRES:
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
    if not USE_POSTGRES and not os.path.exists(DB_PATH):
        print(f"Warning: Database not found at {DB_PATH}")
        print("Database should be populated using simple_video_scraper.py")
    
    # Start the Flask server
    app.run(debug=False, host='0.0.0.0', port=port) 
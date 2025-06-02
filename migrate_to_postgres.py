#!/usr/bin/env python3
"""
Database Migration Script: SQLite to PostgreSQL
Converts your local SQLite database to PostgreSQL for Heroku deployment.
"""

import os
import json
import sqlite3
import psycopg2
from urllib.parse import urlparse
import sys
from datetime import datetime

def export_sqlite_data(sqlite_path):
    """Export data from SQLite database to JSON files"""
    print(f"📂 Connecting to SQLite database: {sqlite_path}")
    
    if not os.path.exists(sqlite_path):
        print(f"❌ SQLite database not found at: {sqlite_path}")
        return False
    
    try:
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Export videos
        print("📹 Exporting videos...")
        cursor.execute('SELECT * FROM videos')
        videos = [dict(row) for row in cursor.fetchall()]
        
        # Export comments
        print("💬 Exporting comments...")
        cursor.execute('SELECT * FROM comments')
        comments = [dict(row) for row in cursor.fetchall()]
        
        # Save to JSON files
        with open('videos_export.json', 'w') as f:
            json.dump(videos, f, indent=2, default=str)
        
        with open('comments_export.json', 'w') as f:
            json.dump(comments, f, indent=2, default=str)
        
        print(f"✅ Exported {len(videos)} videos and {len(comments)} comments")
        print(f"📁 Files created: videos_export.json, comments_export.json")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error exporting SQLite data: {e}")
        return False

def create_postgres_tables(pg_conn):
    """Create PostgreSQL tables matching SQLite schema"""
    print("🏗️  Creating PostgreSQL tables...")
    
    cursor = pg_conn.cursor()
    
    # Create videos table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            video_id VARCHAR(255) PRIMARY KEY,
            title TEXT,
            description TEXT,
            published_at TIMESTAMP,
            view_count INTEGER,
            like_count INTEGER,
            comment_count INTEGER,
            channel_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            like_count INTEGER,
            is_reply BOOLEAN DEFAULT FALSE,
            channel_owner_liked BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (video_id) REFERENCES videos(video_id)
        )
    """)
    
    # Create indexes for better performance
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_video_id ON comments(video_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_parent_id ON comments(parent_comment_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_comments_published_at ON comments(published_at)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_videos_published_at ON videos(published_at)")
    
    pg_conn.commit()
    print("✅ PostgreSQL tables created successfully")

def import_to_postgres(pg_conn):
    """Import data from JSON files to PostgreSQL"""
    print("📥 Importing data to PostgreSQL...")
    
    cursor = pg_conn.cursor()
    
    # Import videos
    if os.path.exists('videos_export.json'):
        with open('videos_export.json', 'r') as f:
            videos = json.load(f)
        
        print(f"📹 Importing {len(videos)} videos...")
        for video in videos:
            cursor.execute("""
                INSERT INTO videos (video_id, title, description, published_at, 
                                  view_count, like_count, comment_count, channel_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (video_id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    view_count = EXCLUDED.view_count,
                    like_count = EXCLUDED.like_count,
                    comment_count = EXCLUDED.comment_count
            """, (
                video['video_id'], video['title'], video['description'],
                video['published_at'], video['view_count'], video['like_count'],
                video['comment_count'], video['channel_id']
            ))
        
        print(f"✅ Imported {len(videos)} videos")
    
    # Import comments
    if os.path.exists('comments_export.json'):
        with open('comments_export.json', 'r') as f:
            comments = json.load(f)
        
        print(f"💬 Importing {len(comments)} comments...")
        batch_size = 1000
        
        for i in range(0, len(comments), batch_size):
            batch = comments[i:i + batch_size]
            
            for comment in batch:
                cursor.execute("""
                    INSERT INTO comments (comment_id, video_id, parent_comment_id, 
                                        author, text, published_at, like_count, 
                                        is_reply, channel_owner_liked)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (comment_id) DO UPDATE SET
                        text = EXCLUDED.text,
                        like_count = EXCLUDED.like_count,
                        channel_owner_liked = EXCLUDED.channel_owner_liked
                """, (
                    comment['comment_id'], comment['video_id'], 
                    comment.get('parent_comment_id'), comment['author'],
                    comment['text'], comment['published_at'], 
                    comment['like_count'], comment.get('is_reply', False),
                    comment.get('channel_owner_liked', False)
                ))
            
            pg_conn.commit()
            print(f"📦 Imported batch {i//batch_size + 1}/{(len(comments) + batch_size - 1)//batch_size}")
        
        print(f"✅ Imported {len(comments)} comments")
    
    pg_conn.commit()

def main():
    """Main migration function"""
    print("🚀 Medical Medium Comment Explorer - Database Migration")
    print("=" * 60)
    
    # Check if we're running on Heroku
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        print("🌐 Running on Heroku - importing to PostgreSQL")
        
        # Parse DATABASE_URL
        url = urlparse(database_url)
        
        try:
            # Connect to PostgreSQL
            pg_conn = psycopg2.connect(
                host=url.hostname,
                port=url.port,
                user=url.username,
                password=url.password,
                database=url.path[1:]  # Remove leading slash
            )
            
            print("✅ Connected to PostgreSQL")
            
            # Create tables
            create_postgres_tables(pg_conn)
            
            # Import data
            import_to_postgres(pg_conn)
            
            print("🎉 Migration completed successfully!")
            
            pg_conn.close()
            
        except Exception as e:
            print(f"❌ Error connecting to PostgreSQL: {e}")
            sys.exit(1)
    
    else:
        print("💻 Running locally - exporting SQLite data")
        
        # Export from SQLite
        sqlite_path = 'data/youtube_comments.db'
        if export_sqlite_data(sqlite_path):
            print("\n📋 Next steps:")
            print("1. Upload videos_export.json and comments_export.json to your Heroku app")
            print("2. Run this script on Heroku to import the data")
            print("3. Command: heroku run python migrate_to_postgres.py")
        else:
            sys.exit(1)

if __name__ == '__main__':
    main() 
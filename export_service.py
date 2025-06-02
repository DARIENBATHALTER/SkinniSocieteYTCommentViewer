import os
import json
import sqlite3
import zipfile
import tempfile
import threading
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import uuid

class ExportService:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.temp_dir = Path("temp_exports")
        self.temp_dir.mkdir(exist_ok=True)
        self.export_tasks = {}  # In-memory task tracking
        
        # For now, we'll create HTML files that can be manually converted to PNG
        # using browser screenshot tools (right-click -> "Save as image" or screenshot)
        print("Export service initialized - generating HTML files for manual PNG conversion")
        
    def get_db_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def generate_avatar_color(self, username: str) -> str:
        """Generate consistent color for username"""
        colors = [
            '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', 
            '#FFEAA7', '#DDA0DD', '#98D8C8', '#F39C12',
            '#E74C3C', '#9B59B6', '#3498DB', '#2ECC71'
        ]
        return colors[hash(username) % len(colors)]
    
    def generate_comment_html(self, comment: Dict, video_title: str = "") -> str:
        """Generate HTML for a single comment in YouTube style"""
        avatar_color = self.generate_avatar_color(comment['author'])
        first_letter = comment['author'][0].upper() if comment['author'] else 'U'
        
        # Format date - handle various timestamp formats from database
        try:
            if isinstance(comment['published_at'], str):
                # Try different date formats
                if 'T' in comment['published_at']:
                    # ISO format
                    published_date = datetime.fromisoformat(comment['published_at'].replace('Z', '+00:00'))
                else:
                    # Try parsing as datetime string
                    published_date = datetime.strptime(comment['published_at'], '%Y-%m-%d %H:%M:%S')
            else:
                # Assume it's already a datetime object
                published_date = comment['published_at']
        except Exception as e:
            print(f"Date parsing error for comment {comment.get('comment_id', 'unknown')}: {e}")
            # Fallback to current date
            published_date = datetime.now()
            
        formatted_date = published_date.strftime('%b %d, %Y')
        
        # Format like count
        like_count = comment.get('like_count', 0)
        if like_count >= 1000:
            like_display = f"{like_count/1000:.1f}K".replace('.0K', 'K')
        else:
            like_display = str(like_count)
            
        # Channel owner liked indicator
        channel_owner_liked = comment.get('channel_owner_liked', False)
        heart_icon = '❤️' if channel_owner_liked else ''
        
        # Escape HTML in text content
        comment_text = comment.get('text', '').replace('<', '&lt;').replace('>', '&gt;').replace('&', '&amp;')
        author_name = comment.get('author', 'Unknown').replace('<', '&lt;').replace('>', '&gt;')
        video_title_escaped = video_title.replace('<', '&lt;').replace('>', '&gt;') if video_title else ''
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: 'Roboto', Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #ffffff;
                    width: 600px;
                }}
                .comment-container {{
                    display: flex;
                    align-items: flex-start;
                    gap: 12px;
                    padding: 16px;
                    background-color: #ffffff;
                }}
                .avatar {{
                    width: 40px;
                    height: 40px;
                    border-radius: 50%;
                    background-color: {avatar_color};
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    font-size: 18px;
                    font-weight: 500;
                    flex-shrink: 0;
                }}
                .comment-content {{
                    flex: 1;
                    min-width: 0;
                }}
                .comment-header {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    margin-bottom: 4px;
                }}
                .author-name {{
                    font-size: 13px;
                    font-weight: 500;
                    color: #030303;
                }}
                .comment-date {{
                    font-size: 12px;
                    color: #606060;
                }}
                .comment-text {{
                    font-size: 14px;
                    line-height: 1.4;
                    color: #030303;
                    margin-bottom: 8px;
                    white-space: pre-wrap;
                    word-wrap: break-word;
                }}
                .comment-actions {{
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }}
                .like-button {{
                    display: flex;
                    align-items: center;
                    gap: 6px;
                    padding: 8px 12px;
                    border-radius: 18px;
                    background-color: #f2f2f2;
                    color: #030303;
                    font-size: 12px;
                    font-weight: 500;
                }}
                .like-icon {{
                    width: 16px;
                    height: 16px;
                }}
                .heart-icon {{
                    margin-left: 8px;
                    font-size: 14px;
                }}
                .video-title {{
                    font-size: 11px;
                    color: #606060;
                    margin-bottom: 8px;
                    font-style: italic;
                }}
            </style>
        </head>
        <body>
            <div class="comment-container">
                <div class="avatar">{first_letter}</div>
                <div class="comment-content">
                    {f'<div class="video-title">From: {video_title_escaped}</div>' if video_title else ''}
                    <div class="comment-header">
                        <span class="author-name">{author_name}</span>
                        <span class="comment-date">{formatted_date}</span>
                    </div>
                    <div class="comment-text">{comment_text}</div>
                    <div class="comment-actions">
                        <div class="like-button">
                            <svg class="like-icon" viewBox="0 0 24 24" fill="currentColor">
                                <path d="M18.77,11h-4.23l1.52-4.94C16.38,5.03,15.54,4,14.38,4c-0.58,0-1.14,0.24-1.52,0.65L7,11H3v10h4h1h9.43 c1.06,0,1.97-0.67,2.3-1.64l1.26-3.75C21.25,14.42,20.16,13,18.77,11z M7,20H4v-8h3V20z M19.98,15.17l-1.26,3.75 C18.43,19.49,18.16,19.75,17.43,19.75H8v-6.85l5.38-5.38C13.51,7.39,13.76,7.25,14.38,7.25c0.28,0,0.5,0.11,0.63,0.3 c0.07,0.1,0.15,0.26,0.09,0.47l-1.52,4.94L13.18,14h1.35h4.23c0.41,0,0.8,0.17,1.03,0.46C19.92,14.61,20.05,14.86,19.98,15.17z"/>
                            </svg>
                            {like_display}
                        </div>
                        {f'<span class="heart-icon">{heart_icon}</span>' if heart_icon else ''}
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        return html_template
    
    def html_to_png(self, html_content: str, output_path: str) -> bool:
        """Save HTML files that can be manually converted to PNG using browser tools"""
        try:
            # Make sure the directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            print(f"Creating file: {output_path}")
            
            # Save HTML content with PNG extension for download
            # Users can open these in a browser and take screenshots or use "Save as image"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Verify the file was created
            if output_file.exists():
                print(f"Successfully created: {output_path}")
            else:
                print(f"Failed to create: {output_path}")
                return False
            
            # Also save a .html version for reference
            html_path = output_path.replace('.png', '.html')
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"Also created HTML version: {html_path}")
            
            return True
        except Exception as e:
            print(f"Error in html_to_png: {e}")
            return False
    
    def sanitize_filename(self, text: str, max_length: int = 50) -> str:
        """Sanitize text for use in filename"""
        # Remove or replace invalid characters (keep @ since it's part of our naming scheme)
        sanitized = re.sub(r'[<>:"/\\|?*]', '', text)
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
        return sanitized[:max_length]
    
    def generate_export_filename(self, video_title: str, username: str, comment_text: str) -> str:
        """Generate filename according to specification"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H-%M')  # Use - instead of : to avoid filename issues
        
        # Sanitize and truncate components
        video_part = self.sanitize_filename(video_title, 15)
        user_part = self.sanitize_filename(username, 10)
        comment_part = self.sanitize_filename(comment_text, 10)
        
        # Remove @ from username if it already exists (since usernames already include @)
        if user_part.startswith('@'):
            user_part = user_part[1:]
        
        return f"{video_part}_{user_part}_{comment_part}_{timestamp}.png"  # Use .png extension
    
    def export_single_comment(self, comment_id: str) -> Optional[str]:
        """Export a single comment as PNG"""
        try:
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get comment with video info
            cursor.execute("""
                SELECT c.*, v.title as video_title 
                FROM comments c 
                JOIN videos v ON c.video_id = v.video_id 
                WHERE c.comment_id = ?
            """, (comment_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            comment = dict(row)
            conn.close()
            
            # Generate HTML and convert to PNG
            html_content = self.generate_comment_html(comment, comment['video_title'])
            filename = self.generate_export_filename(
                comment['video_title'], 
                comment['author'], 
                comment['text']
            )
            
            output_path = self.temp_dir / filename
            if self.html_to_png(html_content, str(output_path)):
                return str(output_path)
            return None
            
        except Exception as e:
            print(f"Error exporting single comment: {e}")
            return None
    
    def export_video_comments(self, video_id: str, task_id: str = None) -> Optional[str]:
        """Export all comments from a video as ZIP file"""
        try:
            if not task_id:
                task_id = str(uuid.uuid4())
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get video info
            cursor.execute("SELECT title FROM videos WHERE video_id = ?", (video_id,))
            video_row = cursor.fetchone()
            if not video_row:
                return None
                
            video_title = video_row['title']
            
            # Get all comments for video
            cursor.execute("""
                SELECT * FROM comments 
                WHERE video_id = ? 
                ORDER BY published_at DESC
            """, (video_id,))
            
            comments = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            if not comments:
                return None
            
            # Initialize progress tracking
            if task_id:
                self.export_tasks[task_id] = {
                    'status': 'processing',
                    'progress': 0,
                    'total': len(comments),
                    'current_item': f"Processing {len(comments)} comments"
                }
            
            # Create temporary directory for this export
            export_dir = self.temp_dir / f"export_{task_id}"
            export_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate PNGs for each comment
            png_files = []
            for i, comment in enumerate(comments):
                html_content = self.generate_comment_html(comment, video_title)
                filename = self.generate_export_filename(
                    video_title,
                    comment['author'],
                    comment['text']
                )
                
                png_path = export_dir / filename
                if self.html_to_png(html_content, str(png_path)):
                    # The html_to_png function creates the file with the given path
                    # so we add the file that was actually created
                    if png_path.exists():
                        png_files.append(png_path)
                    else:
                        print(f"Warning: Expected file not found: {png_path}")
                
                # Update progress
                if task_id:
                    self.export_tasks[task_id]['progress'] = i + 1
                    self.export_tasks[task_id]['current_item'] = f"Creating PNG {i+1}/{len(comments)}"
            
            # Create ZIP file
            timestamp = datetime.now().strftime('%Y-%m-%d %H-%M')
            safe_video_title = self.sanitize_filename(video_title, 30)
            zip_filename = f"{safe_video_title}_CommentExport_{timestamp}.zip"
            zip_path = self.temp_dir / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for png_file in png_files:
                    zipf.write(png_file, png_file.name)
            
            # Cleanup temporary PNG files
            for png_file in png_files:
                png_file.unlink()
            export_dir.rmdir()
            
            # Mark task as completed
            if task_id:
                self.export_tasks[task_id]['status'] = 'completed'
                self.export_tasks[task_id]['file_path'] = str(zip_path)
            
            return str(zip_path)
            
        except Exception as e:
            if task_id:
                self.export_tasks[task_id]['status'] = 'failed'
                self.export_tasks[task_id]['error'] = str(e)
            print(f"Error exporting video comments: {e}")
            return None
    
    def export_channel_comments(self, task_id: str = None) -> Optional[List[str]]:
        """Export all comments from all videos in the channel"""
        try:
            if not task_id:
                task_id = str(uuid.uuid4())
            
            conn = self.get_db_connection()
            cursor = conn.cursor()
            
            # Get all videos
            cursor.execute("SELECT video_id, title FROM videos ORDER BY published_at DESC")
            videos = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            if not videos:
                return None
            
            # Initialize progress tracking
            if task_id:
                self.export_tasks[task_id] = {
                    'status': 'processing',
                    'video_progress': 0,
                    'video_total': len(videos),
                    'comment_progress': 0,
                    'comment_total': 0,
                    'current_video': '',
                    'zip_files': []
                }
            
            zip_files = []
            
            for video_index, video in enumerate(videos):
                # Update video progress
                if task_id:
                    self.export_tasks[task_id]['video_progress'] = video_index
                    self.export_tasks[task_id]['current_video'] = video['title']
                
                # Create video-specific task for comment tracking
                video_task_id = f"{task_id}_video_{video_index}"
                zip_path = self.export_video_comments(video['video_id'], video_task_id)
                
                if zip_path:
                    zip_files.append(zip_path)
                    if task_id:
                        self.export_tasks[task_id]['zip_files'].append(zip_path)
                
                # Update video progress
                if task_id:
                    self.export_tasks[task_id]['video_progress'] = video_index + 1
            
            # Mark task as completed
            if task_id:
                self.export_tasks[task_id]['status'] = 'completed'
            
            return zip_files
            
        except Exception as e:
            if task_id:
                self.export_tasks[task_id]['status'] = 'failed'
                self.export_tasks[task_id]['error'] = str(e)
            print(f"Error exporting channel comments: {e}")
            return None
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get the status of an export task"""
        return self.export_tasks.get(task_id)
    
    def cleanup_old_files(self, hours_old: int = 24):
        """Clean up temporary files older than specified hours"""
        try:
            cutoff_time = datetime.now().timestamp() - (hours_old * 3600)
            for file_path in self.temp_dir.glob("*"):
                if file_path.stat().st_mtime < cutoff_time:
                    if file_path.is_file():
                        file_path.unlink()
                    elif file_path.is_dir():
                        import shutil
                        shutil.rmtree(file_path)
        except Exception as e:
            print(f"Error during cleanup: {e}") 
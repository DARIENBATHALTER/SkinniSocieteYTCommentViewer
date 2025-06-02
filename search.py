#!/usr/bin/env python3
"""
YouTube Comment Search Utility

A tool to search comments in the SQLite database.
"""

import argparse
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Search YouTube comments in the database"
    )
    parser.add_argument(
        "query",
        help="Text to search for in comments"
    )
    parser.add_argument(
        "-d", "--database",
        default="data/youtube_comments.db",
        help="Path to SQLite database file (default: data/youtube_comments.db)"
    )
    parser.add_argument(
        "-l", "--limit",
        type=int,
        default=50,
        help="Maximum number of results to return (default: 50)"
    )
    parser.add_argument(
        "-a", "--author",
        help="Filter by comment author"
    )
    parser.add_argument(
        "-v", "--video",
        help="Filter by video ID"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output results to JSON file"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)"
    )
    
    return parser.parse_args()

def search_comments(args):
    """Search for comments in the database.
    
    Args:
        args: Command line arguments
        
    Returns:
        List of comment dictionaries
    """
    db_path = Path(args.database)
    
    if not db_path.exists():
        print(f"Error: Database file not found at {db_path}")
        return []
    
    query = args.query.strip()
    limit = max(1, args.limit)
    
    # Build SQL query
    sql = """
    SELECT 
        c.comment_id, c.video_id, c.parent_comment_id, c.author, 
        c.text, c.published_at, c.like_count, c.is_reply,
        v.title as video_title, v.published_at as video_published_at
    FROM 
        comments c
    JOIN 
        videos v ON c.video_id = v.video_id
    WHERE 
        c.text LIKE ?
    """
    
    params = [f"%{query}%"]
    
    # Add author filter if provided
    if args.author:
        sql += " AND c.author LIKE ?"
        params.append(f"%{args.author}%")
    
    # Add video filter if provided
    if args.video:
        sql += " AND c.video_id = ?"
        params.append(args.video)
    
    # Add order and limit
    sql += " ORDER BY c.published_at DESC LIMIT ?"
    params.append(limit)
    
    # Execute query
    try:
        conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute(sql, params)
        
        # Convert to list of dictionaries
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            
            # Convert datetime objects to strings for JSON serialization
            if isinstance(result['published_at'], datetime):
                result['published_at'] = result['published_at'].isoformat()
            if isinstance(result['video_published_at'], datetime):
                result['video_published_at'] = result['video_published_at'].isoformat()
                
            results.append(result)
        
        conn.close()
        return results
        
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []

def display_results(results, output_format="text"):
    """Display search results.
    
    Args:
        results: List of comment dictionaries
        output_format: Output format (text or json)
    """
    if not results:
        print("No matching comments found.")
        return
    
    if output_format == "json":
        print(json.dumps(results, indent=2))
        return
    
    # Text format
    print(f"Found {len(results)} matching comments:\n")
    
    for i, comment in enumerate(results, 1):
        video_date = datetime.fromisoformat(comment['video_published_at']) if isinstance(comment['video_published_at'], str) else comment['video_published_at']
        comment_date = datetime.fromisoformat(comment['published_at']) if isinstance(comment['published_at'], str) else comment['published_at']
        
        print(f"--- Result {i} ---")
        print(f"Video: {comment['video_title']}")
        print(f"Video ID: {comment['video_id']}")
        print(f"Video Date: {video_date.strftime('%Y-%m-%d')}")
        print(f"Author: {comment['author']}")
        print(f"Comment Date: {comment_date.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Likes: {comment['like_count']}")
        print(f"Comment ID: {comment['comment_id']}")
        if comment['is_reply']:
            print(f"Reply to: {comment['parent_comment_id']}")
        print("\nComment:")
        print(comment['text'])
        print("\n")

def save_to_file(results, filename):
    """Save results to a JSON file.
    
    Args:
        results: List of comment dictionaries
        filename: Output filename
    """
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Results saved to {filename}")
    except Exception as e:
        print(f"Error saving results: {e}")

def main():
    """Main entry point."""
    args = parse_args()
    
    # Search for comments
    results = search_comments(args)
    
    # Display results
    display_results(results, args.format)
    
    # Save to file if requested
    if args.output and results:
        save_to_file(results, args.output)

if __name__ == "__main__":
    main() 
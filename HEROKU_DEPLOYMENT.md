# Medical Medium Comment Explorer - Heroku Deployment Guide

## Overview
This guide will help you deploy your Medical Medium YouTube Comment Explorer as a web application on Heroku. Once deployed, anyone can access it via a URL without needing to download or install anything.

## Prerequisites
- Heroku account (free tier works fine)
- Git installed on your computer
- Your YouTube API key

## Step 1: Install Heroku CLI

### macOS (using Homebrew):
```bash
brew tap heroku/brew && brew install heroku
```

### Alternative (download installer):
Visit https://devcenter.heroku.com/articles/heroku-cli and download the installer.

## Step 2: Login to Heroku
```bash
heroku login
```
This will open your browser to complete the login.

## Step 3: Prepare Your Database

### Option A: Upload Existing Database (Recommended)
If you have your existing `youtube_comments.db` file:

1. **Install Heroku Postgres addon** (free tier):
```bash
heroku addons:create heroku-postgresql:mini --app your-app-name
```

2. **Convert SQLite to PostgreSQL** (we'll help you with this)

### Option B: Start Fresh
The app will create an empty database and you can scrape content directly on Heroku.

## Step 4: Create Heroku App
```bash
# Create a new Heroku app (replace 'your-app-name' with something unique)
heroku create your-app-name

# Or let Heroku generate a random name
heroku create
```

## Step 5: Set Environment Variables
```bash
# Set your YouTube API key
heroku config:set YOUTUBE_API_KEY=your_actual_api_key_here

# Set Flask environment
heroku config:set FLASK_ENV=production
heroku config:set FLASK_DEBUG=False
```

## Step 6: Deploy to Heroku
```bash
# Initialize git repository (if not already done)
git init

# Add all files
git add .

# Commit changes
git commit -m "Initial deployment to Heroku"

# Add Heroku remote
heroku git:remote -a your-app-name

# Deploy!
git push heroku main
```

## Step 7: Open Your Web App
```bash
heroku open
```

## Database Migration (SQLite to PostgreSQL)

If you have existing data, we'll need to convert it:

### 1. Export your SQLite data:
```bash
# Run this in your local project directory
python -c "
import sqlite3
import json

# Connect to your SQLite database
conn = sqlite3.connect('data/youtube_comments.db')
conn.row_factory = sqlite3.Row

# Export videos
cursor = conn.cursor()
cursor.execute('SELECT * FROM videos')
videos = [dict(row) for row in cursor.fetchall()]

# Export comments
cursor.execute('SELECT * FROM comments')
comments = [dict(row) for row in cursor.fetchall()]

# Save to JSON files
with open('videos_export.json', 'w') as f:
    json.dump(videos, f, indent=2)

with open('comments_export.json', 'w') as f:
    json.dump(comments, f, indent=2)

print(f'Exported {len(videos)} videos and {len(comments)} comments')
conn.close()
"
```

### 2. Create import script for Heroku:
We'll create a script that imports this data into PostgreSQL on Heroku.

## Monitoring Your App

### View logs:
```bash
heroku logs --tail
```

### Check app status:
```bash
heroku ps
```

### Access database console:
```bash
heroku pg:psql
```

## Scaling (if needed)

### Upgrade to hobby dyno for better performance:
```bash
heroku ps:scale web=1:hobby
```

## Cost Breakdown

### Free Tier:
- **App hosting**: Free (550-1000 dyno hours/month)
- **Database**: Free PostgreSQL (10,000 rows limit)
- **Total**: $0/month

### Hobby Tier (if you need more):
- **App hosting**: $7/month (always-on, custom domain)
- **Database**: $9/month (10M rows, better performance)
- **Total**: $16/month

## Advantages of Web App vs Desktop App

✅ **Instant access** - Just share a URL  
✅ **No downloads** - Works on any device with a browser  
✅ **Always updated** - Everyone sees the latest data  
✅ **Mobile friendly** - Works on phones and tablets  
✅ **No installation issues** - No more "app won't open" problems  
✅ **Collaborative** - Multiple people can use it simultaneously  

## Next Steps

1. **Custom Domain** (optional): You can add a custom domain like `mmcomments.yourname.com`
2. **SSL Certificate**: Heroku provides free SSL certificates
3. **Monitoring**: Set up monitoring and alerts
4. **Backups**: Configure automatic database backups

## Troubleshooting

### App won't start:
```bash
heroku logs --tail
```
Look for error messages in the logs.

### Database connection issues:
Make sure your `DATABASE_URL` environment variable is set (Heroku does this automatically).

### Out of memory:
Upgrade to hobby dyno or optimize your queries.

## Support

If you run into issues during deployment, the logs will usually tell you what's wrong:
```bash
heroku logs --tail
```

Common issues and solutions will be added here as we encounter them. 
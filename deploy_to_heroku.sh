#!/bin/bash

# Medical Medium Comment Explorer - Heroku Deployment Script
# This script automates the deployment process to Heroku

set -e  # Exit on any error

echo "🚀 Medical Medium Comment Explorer - Heroku Deployment"
echo "======================================================"

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI not found. Please install it first:"
    echo "   brew tap heroku/brew && brew install heroku"
    exit 1
fi

# Check if user is logged in to Heroku
if ! heroku auth:whoami &> /dev/null; then
    echo "🔐 Please log in to Heroku first:"
    heroku login
fi

# Get app name from user
read -p "📝 Enter your Heroku app name (or press Enter for auto-generated): " APP_NAME

# Create Heroku app
if [ -z "$APP_NAME" ]; then
    echo "🏗️  Creating Heroku app with auto-generated name..."
    heroku create
    APP_NAME=$(heroku apps:info --json | python3 -c "import sys, json; print(json.load(sys.stdin)['name'])")
else
    echo "🏗️  Creating Heroku app: $APP_NAME"
    heroku create "$APP_NAME"
fi

echo "✅ Created app: $APP_NAME"

# Add PostgreSQL addon
echo "🐘 Adding PostgreSQL database..."
heroku addons:create heroku-postgresql:mini --app "$APP_NAME"

# Get YouTube API key
read -p "🔑 Enter your YouTube API key: " API_KEY

# Set environment variables
echo "⚙️  Setting environment variables..."
heroku config:set YOUTUBE_API_KEY="$API_KEY" --app "$APP_NAME"
heroku config:set FLASK_ENV=production --app "$APP_NAME"
heroku config:set FLASK_DEBUG=False --app "$APP_NAME"

# Initialize git if needed
if [ ! -d ".git" ]; then
    echo "📦 Initializing git repository..."
    git init
fi

# Add Heroku remote
echo "🔗 Adding Heroku remote..."
heroku git:remote -a "$APP_NAME"

# Add and commit files
echo "📁 Adding files to git..."
git add .
git commit -m "Deploy Medical Medium Comment Explorer to Heroku" || echo "No changes to commit"

# Deploy to Heroku
echo "🚀 Deploying to Heroku..."
git push heroku main

# Check if we have existing data to migrate
if [ -f "data/youtube_comments.db" ]; then
    echo "📊 Found existing database. Would you like to migrate the data?"
    read -p "   Migrate data? (y/n): " MIGRATE_DATA
    
    if [ "$MIGRATE_DATA" = "y" ] || [ "$MIGRATE_DATA" = "Y" ]; then
        echo "📤 Exporting local database..."
        python3 migrate_to_postgres.py
        
        if [ -f "videos_export.json" ] && [ -f "comments_export.json" ]; then
            echo "📥 Uploading data files to Heroku..."
            # Note: This is a simplified approach. In practice, you'd upload these files
            # and then run the migration script on Heroku
            echo "⚠️  Manual step required:"
            echo "   1. Upload videos_export.json and comments_export.json to your app"
            echo "   2. Run: heroku run python migrate_to_postgres.py --app $APP_NAME"
        fi
    fi
fi

# Open the app
echo "🌐 Opening your web app..."
heroku open --app "$APP_NAME"

echo ""
echo "🎉 Deployment completed successfully!"
echo "📱 Your app is now live at: https://$APP_NAME.herokuapp.com"
echo ""
echo "📋 Next steps:"
echo "   • Share the URL with friends and family"
echo "   • Monitor your app: heroku logs --tail --app $APP_NAME"
echo "   • Update content: Use the scraper interface in your web app"
echo ""
echo "💡 Pro tip: Bookmark your app URL for easy access!" 
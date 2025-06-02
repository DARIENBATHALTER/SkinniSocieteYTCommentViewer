#!/bin/bash

# Medical Medium Comment Explorer - Railway Deployment Script
# Railway is a modern alternative to Heroku with better free tier

set -e  # Exit on any error

echo "🚀 Medical Medium Comment Explorer - Railway Deployment"
echo "======================================================"
echo "Railway offers $5/month credit (usually covers small apps completely)"
echo ""

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    echo "📦 Installing Railway CLI..."
    npm install -g @railway/cli
fi

# Login to Railway
echo "🔐 Logging in to Railway..."
railway login

# Create new project
echo "🏗️  Creating Railway project..."
railway init

# Get YouTube API key
read -p "🔑 Enter your YouTube API key: " API_KEY

# Set environment variables
echo "⚙️  Setting environment variables..."
railway variables set YOUTUBE_API_KEY="$API_KEY"
railway variables set FLASK_ENV=production
railway variables set FLASK_DEBUG=False

# Add PostgreSQL database
echo "🐘 Adding PostgreSQL database..."
railway add postgresql

# Deploy
echo "🚀 Deploying to Railway..."
railway up

echo ""
echo "🎉 Deployment completed successfully!"
echo "📱 Your app will be available at your Railway project URL"
echo ""
echo "📋 Next steps:"
echo "   • Check your Railway dashboard for the live URL"
echo "   • Share the URL with friends and family"
echo "   • Monitor your app in the Railway dashboard"
echo ""
echo "💡 Pro tip: Railway gives you $5/month credit - perfect for small apps!" 
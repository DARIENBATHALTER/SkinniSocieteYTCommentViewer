# 🗄️ Render PostgreSQL Setup Guide

## Why PostgreSQL on Render?
- ✅ **Persistent storage** - data survives deployments and restarts
- ✅ **Free PostgreSQL** available on Render (limited storage)
- ✅ **Automatic backups** and management
- ✅ **Better for production** web apps

## Setup Steps

### 1. Create PostgreSQL Database
1. **Go to Render Dashboard**: https://dashboard.render.com/
2. **Click "New +"** → **"PostgreSQL"**
3. **Database Settings**:
   - **Name**: `mmcomment-db` (or your preference)
   - **Database**: `mmcomments`
   - **User**: `mmuser` (will be created)
   - **Region**: Same as your web service
   - **Plan**: **Free** (good for development/testing)

### 2. Get Database Connection Details
After creation, Render provides:
- **Internal Database URL**: `postgresql://user:pass@hostname:port/dbname`
- **External Database URL**: For external connections
- Use the **Internal URL** for your web service

### 3. Update Your Web Service Environment Variables
In your Render web service:
1. **Go to Environment tab**
2. **Add/Update variables**:
   ```
   DATABASE_URL=postgresql://user:pass@hostname:port/dbname
   YOUTUBE_API_KEY=your_new_api_key_here
   FLASK_ENV=production
   FLASK_DEBUG=False
   ```

### 4. Webapp Changes Needed
Your webapp currently uses SQLite. For PostgreSQL, you need:

#### A. Update Database Connection (Minor Code Changes)
- Detect if `DATABASE_URL` contains `postgresql://`
- Use `psycopg2` for PostgreSQL connections
- Keep SQLite for local development

#### B. Database Schema Migration
- Create tables in PostgreSQL
- Import existing SQLite data (if any)

## Migration Code Changes
See `webapp_postgres.py` for the updated version that supports both SQLite and PostgreSQL.

## Alternative: External Database Storage
If you prefer to keep SQLite:
- Use **external storage** (AWS S3, Google Cloud Storage)
- Upload/download database file
- More complex but keeps current architecture 
# Medical Medium YouTube Comment Explorer

A powerful web application for browsing, filtering, and exporting YouTube comments from the Medical Medium channel. Export individual comments or entire video collections as professional-looking PNG images that mimic YouTube's comment design.

## ✨ Features

### 🔍 **Comment Browsing**
- Browse 82K+ comments across 598+ videos from the Medical Medium channel
- Advanced filtering by date, keywords, and like count
- Sort by most liked, least liked, or most recent
- Nested reply viewing with parent-child relationships
- Real-time search with highlighting

### 📤 **Export Capabilities**
- **Single Comment Export**: Individual PNG files with authentic YouTube styling
- **Video Export**: ZIP files containing all comments from a video (chunked for large videos)
- **Channel Export**: Complete channel export with separate ZIP files per video
- **Bulk Processing**: Handles 1,600+ comments per video efficiently

### 🎨 **Authentic YouTube Styling**
- Colored circular avatars with user initials
- Proper spacing and typography matching YouTube
- Like counts with K/M formatting
- Channel owner heart indicators
- Date formatting and relative positioning

### 🚀 **Technical Features**
- Client-side PNG generation using html2canvas
- Chunked processing to avoid browser memory limits
- Real-time progress tracking with dual progress bars
- Error handling with skip-and-continue logic
- Responsive web interface built with Bootstrap

## 📁 Project Structure

```
YTScraper copy/
├── webapp.py                 # Flask web server
├── templates/
│   └── index.html            # Main web interface
├── data/
│   └── youtube_comments.db   # SQLite database with comments
├── requirements.txt          # Python dependencies
├── build_standalone.py       # Build script for executable
└── README.md                # This file
```

## 🔧 Development Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation
1. Clone or download the project
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the development server:
   ```bash
   python webapp.py
   ```
4. Open your browser to `http://localhost:9191`

## 📦 Building Standalone Executable

To create a distributable application that doesn't require Python installation:

### Build Process
```bash
python build_standalone.py
```

This will:
1. Install PyInstaller if needed
2. Create a launcher script
3. Bundle Python + Flask + SQLite + your data into a single executable
4. Output: `dist/YouTubeCommentExplorer.exe` (Windows) or equivalent for Mac/Linux

### What Gets Included
- ✅ Python runtime
- ✅ Flask web server
- ✅ SQLite database with all comments
- ✅ HTML templates and assets
- ✅ All dependencies
- ✅ Auto-launching browser

### Distribution
The resulting executable:
- **Single file** - no installation required
- **Self-contained** - includes all data and dependencies
- **Cross-platform** - works on Windows, Mac, and Linux
- **User-friendly** - double-click to run, browser opens automatically

## 💻 Usage

### Starting the Application
**Development:**
```bash
python webapp.py
```

**Standalone Executable:**
- Double-click `YouTubeCommentExplorer.exe`
- Browser opens automatically to the application

### Exporting Comments

#### Single Comment Export
1. Navigate to any video's comments
2. Click the "Export" button next to any comment
3. PNG file downloads immediately

#### Video Export (All Comments)
1. Open a video's comment page
2. Click "Export All Video Comments"
3. ZIP file(s) download with all comments as PNGs
4. Large videos split into multiple ZIP files (500 comments each)

#### Channel Export (All Videos)
1. From the main video list page
2. Click "Export All Channel Comments"
3. Individual ZIP files download for each video
4. Progress tracking shows overall and per-video progress

### Export File Naming
```
[VideoTitle]_[Username]_[CommentText]_[YYYY-MM-DD HH-MM].png
```

Example:
```
Celery_Juice_Can_Save_Your_Life_sinisterking6009_Exactly_my_thoughts_2025-01-15_14-30.png
```

## 🎯 Technical Implementation

### Client-Side PNG Generation
- Uses `html2canvas` library for browser-based image generation
- No server-side image processing required
- High-quality 2x scale factor for crisp images
- Handles fonts, colors, and complex layouts

### Chunked Processing
- Breaks large exports into 500-comment chunks
- Prevents browser memory issues
- Maintains file naming consistency
- Real-time progress tracking

### Database Schema
```sql
videos (video_id, title, published_at, view_count, like_count, comment_count)
comments (comment_id, video_id, parent_comment_id, author, text, published_at, like_count, is_reply)
```

## 🚀 Performance

### Benchmarks
- **Single comment export**: ~2-3 seconds
- **Video export (1,600 comments)**: ~45-60 minutes
- **Channel export (82K comments)**: ~24-48 hours
- **Memory usage**: <500MB for largest exports

### Optimizations
- Chunked processing prevents memory overflow
- Client-side generation reduces server load
- Progress tracking provides user feedback
- Error handling ensures completion despite individual failures

## 🛠️ Troubleshooting

### Common Issues

**Port 9191 already in use:**
```bash
# Kill existing process
pkill -f "python webapp.py"
# Or change port in webapp.py
```

**Build fails on PyInstaller:**
```bash
# Install/update PyInstaller
pip install --upgrade pyinstaller
# Ensure all dependencies installed
pip install -r requirements.txt
```

**Large exports fail:**
- Browser may limit long-running scripts
- Use smaller chunk sizes (edit `maxCommentsPerZip`)
- Close other browser tabs to free memory

## 📊 Data Statistics

Current database contains:
- **Videos**: 598 (Medical Medium channel)
- **Comments**: 82,000+ total
- **Date Range**: Multiple years of content
- **Size**: ~50MB SQLite database

## 🔒 Privacy & Data

- All data is locally stored (SQLite database)
- No external API calls during export
- Comments were previously scraped using YouTube API
- User data never transmitted outside local application

## 🤝 Contributing

This is a specialized tool for Medical Medium comment analysis. For modifications:

1. Fork the repository
2. Make changes to `webapp.py` or `templates/index.html`
3. Test with development setup
4. Build new executable with `build_standalone.py`

## 📋 Dependencies

Core requirements:
```
flask>=2.0.0
sqlite3 (built-in)
html2canvas (CDN)
bootstrap (CDN)
jszip (CDN)
```

Build requirements:
```
pyinstaller>=5.0
```

## 📝 License

This project is for educational and research purposes. YouTube content remains property of respective creators.

---

**Built with ❤️ for the Medical Medium community** # MMYouTubeCommentExplorer

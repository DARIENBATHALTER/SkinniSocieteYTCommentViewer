# Skinni Societie Comment Viewer

A specialized web application for browsing, filtering, and exporting YouTube comments from two specific videos related to Skinni Societie content. Export individual comments or entire collections as professional-looking PNG images that mimic YouTube's comment design.

## ✨ Features

### 🔍 **Comment Browsing**
- Browse 2,000+ comments across 2 targeted videos about skinny culture and influencers
- Advanced filtering by date, keywords, and like count
- Sort by most liked, least liked, or most recent
- Nested reply viewing with parent-child relationships
- Real-time search with highlighting

### 📤 **Export Capabilities**
- **Single Comment Export**: Individual PNG files with authentic YouTube styling
- **Video Export**: ZIP files containing all comments from a video (chunked for large videos)
- **Collection Export**: Complete export with separate ZIP files per video
- **Bulk Processing**: Handles 1,000+ comments per video efficiently

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
SkinnieSocieteScraper/
├── webapp.py                      # Flask web server
├── templates/
│   └── index.html                 # Main web interface
├── data/
│   └── youtube_comments.db        # SQLite database with comments
├── simple_video_scraper.py        # Initial data collection script
├── requirements.txt               # Python dependencies
└── README.md                     # This file
```

## 🔧 Setup and Usage

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- YouTube API key (for initial data collection only)

### Installation
1. Clone or download the project
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Initial Data Collection (One-time)
If starting fresh, run the scraper to collect comments:
```bash
# Set your YouTube API key
export YOUTUBE_API_KEY="your_api_key_here"

# Run the scraper (one-time only)
python simple_video_scraper.py
```

### Running the Viewer
```bash
python webapp.py
```
Open your browser to `http://localhost:9191`

## 🎯 Target Videos

This application focuses on comments from two specific videos:

1. **"TikTok's Skinny-Obsessed Community, "SkinnyTok," Isn't Making You Healthier - It's a Cult..."**
   - Video ID: vxBMePfysQk
   - Comments analyzed: ~1,471

2. **"Skinny Influencer" Liv Schmidt's Culty Membership Exposed...**
   - Video ID: 2JkkwEzHIcQ  
   - Comments analyzed: ~539

## 💻 Using the Application

### Browsing Comments
1. **Video Selection**: Choose from the two available videos on the main page
2. **Filtering**: Use the filter panel to search by keywords, date ranges, or minimum likes
3. **Sorting**: Sort comments by date, popularity, or author
4. **Navigation**: Browse through paginated results

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

#### Collection Export (All Videos)
1. From the main video list page
2. Click "Export All Comments"
3. Individual ZIP files download for each video
4. Progress tracking shows overall and per-video progress

### Export File Naming
```
[VideoTitle]_[Username]_[CommentText]_[YYYY-MM-DD HH-MM].png
```

Example:
```
TikToks_Skinny_Obsessed_Community_user123_Great_analysis_2025-01-15_14-30.png
```

## 🎨 Red Theme

The application features a red color scheme to match the Skinni Societie branding:
- Primary accent color: #DC3545 (Bootstrap red)
- Icon color: Red play button symbol
- Maintains clean, professional appearance

## 🚀 Performance

### Current Dataset
- **Videos**: 2 (targeted content)
- **Comments**: 2,000+ total
- **Export speed**: ~2-3 seconds per comment
- **Memory usage**: <200MB for typical operations

### Optimizations
- Chunked processing prevents memory overflow
- Client-side generation reduces server load
- Progress tracking provides user feedback
- Error handling ensures completion despite individual failures

## 🛠️ Technical Implementation

### Client-Side PNG Generation
- Uses `html2canvas` library for browser-based image generation
- No server-side image processing required
- High-quality 2x scale factor for crisp images
- Handles fonts, colors, and complex layouts

### Database Schema
```sql
videos (video_id, title, published_at, view_count, like_count, comment_count)
comments (comment_id, video_id, parent_comment_id, author, text, published_at, like_count, is_reply)
```

## 🔧 Troubleshooting

### Common Issues

**Port 9191 already in use:**
```bash
# Kill existing process
pkill -f "python webapp.py"
# Or change port in webapp.py
```

**Missing database:**
```bash
# Run the scraper to collect data
python simple_video_scraper.py
```

**Large exports fail:**
- Browser may limit long-running scripts
- Use smaller chunk sizes (edit `maxCommentsPerZip`)
- Close other browser tabs to free memory

## 📊 Data Statistics

Current database contains:
- **Videos**: 2 (Skinni Societie related content)
- **Comments**: 2,000+ total
- **Focus**: Analysis of skinny culture discussions and community responses

## 🎯 Purpose

This tool is designed for researchers, content creators, and analysts interested in understanding online discussions about:
- Skinny culture and "SkinnyTok" communities
- Influencer accountability and cult-like behaviors
- Body image discussions in social media
- Community responses to health/wellness content

**Built for focused analysis of skinny culture discourse** 🔍✨

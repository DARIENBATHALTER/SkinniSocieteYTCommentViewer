# YouTube Comment Explorer

A web application to browse and search YouTube comments scraped with the YouTube Comment Scraper.

## Features

- Browse all scraped videos with thumbnails and metadata
- View all comments for a specific video
- Search comments by keyword
- Filter comments by date range
- Responsive design that works on mobile and desktop

## Requirements

- Python 3.9+
- Flask
- SQLite database created by the YouTube Comment Scraper

## Installation

1. Make sure you have already run the YouTube Comment Scraper and have a populated database in the `data` folder.

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Start the web server:
   ```bash
   python webapp.py
   ```

2. Open your browser and go to:
   ```
   http://localhost:5000
   ```

3. Browse the videos and click on any video to see its comments.

4. Use the filter button to search for specific keywords or filter by date range.

## Screenshots

### Video List
![Video List](https://example.com/video-list.png)

### Comments View
![Comments View](https://example.com/comments-view.png)

## License

MIT 
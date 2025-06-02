from googleapiclient.discovery import build
from tqdm import tqdm
import json
import time

# Replace with your YouTube API key
API_KEY = 'AIzaSyBbiT0ncEnaYbIOkIBUJPdSsvRQ3ux3lEE'

youtube = build('youtube', 'v3', developerKey=API_KEY)

def get_uploads_playlist_id(channel_id):
    res = youtube.channels().list(part='contentDetails', id=channel_id).execute()
    return res['items'][0]['contentDetails']['relatedPlaylists']['uploads']

def get_video_ids(playlist_id):
    video_ids = []
    next_page = None
    while True:
        res = youtube.playlistItems().list(
            part='contentDetails',
            playlistId=playlist_id,
            maxResults=50,
            pageToken=next_page
        ).execute()
        video_ids += [item['contentDetails']['videoId'] for item in res['items']]
        next_page = res.get('nextPageToken')
        if not next_page:
            break
    return video_ids

def get_comments(video_id):
    comments = []
    next_page = None
    while True:
        try:
            res = youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=100,
                pageToken=next_page,
                textFormat='plainText'
            ).execute()

            for item in res['items']:
                snippet = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'videoId': video_id,
                    'author': snippet.get('authorDisplayName'),
                    'text': snippet.get('textDisplay'),
                    'publishedAt': snippet.get('publishedAt'),
                    'likeCount': snippet.get('likeCount'),
                })

            next_page = res.get('nextPageToken')
            if not next_page:
                break

        except Exception as e:
            print(f"[!] Error fetching comments for {video_id}: {e}")
            break

    return comments

def scrape_channel_comments(channel_id):
    playlist_id = get_uploads_playlist_id(channel_id)
    print(f"[+] Uploads playlist ID: {playlist_id}")

    video_ids = get_video_ids(playlist_id)
    print(f"[+] Found {len(video_ids)} videos.")

    all_comments = []
    for vid in tqdm(video_ids):
        comments = get_comments(vid)
        all_comments.extend(comments)
        time.sleep(0.5)  # To avoid rate limits

    with open('all_comments.json', 'w', encoding='utf-8') as f:
        json.dump(all_comments, f, ensure_ascii=False, indent=2)

    print(f"[✓] Saved {len(all_comments)} comments to all_comments.json")

# Example usage
scrape_channel_comments('UCUORv_qpgmg8N5plVqlYjXg')  # Replace with actual channel ID

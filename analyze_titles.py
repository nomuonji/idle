from googleapiclient.discovery import build
import json
import isodate # for parsing duration duration ISO 8601

api_key = "AIzaSyAfIovLQzP0mpxsz5db7VjLulFdY5ZrIXY"
channel_id = "UCuFPaemAaMR8R5cHzjy23dQ" # Found via API search

youtube = build('youtube', 'v3', developerKey=api_key)

def get_all_videos_snippet(channel_id, max_results=200):
    # 1. Get Uploads ID
    res = youtube.channels().list(id=channel_id, part='contentDetails').execute()
    uploads_id = res['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    videos = []
    next_page_token = None
    
    print(f"Fetching videos from playlist {uploads_id}...")
    
    while True:
        req = youtube.playlistItems().list(
            playlistId=uploads_id,
            part='snippet',
            maxResults=50,
            pageToken=next_page_token
        )
        resp = req.execute()
        
        for item in resp['items']:
            title = item['snippet']['title']
            vid = item['snippet']['resourceId']['videoId']
            videos.append({'id': vid, 'title': title})
            
        next_page_token = resp.get('nextPageToken')
        if not next_page_token or len(videos) >= max_results:
            break
            
    return videos

def check_details(video_ids):
    # Get duration and tags
    details_map = {}
    
    # Process in chunks of 50
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        req = youtube.videos().list(
            id=','.join(chunk),
            part='contentDetails,snippet'
        )
        resp = req.execute()
        
        for item in resp['items']:
            vid = item['id']
            duration_iso = item['contentDetails']['duration']
            duration_sec = isodate.parse_duration(duration_iso).total_seconds()
            tags = item['snippet'].get('tags', [])
            details_map[vid] = {'duration': duration_sec, 'tags': tags}
            
    return details_map

videos = get_all_videos_snippet(channel_id, max_results=100) # Check recent 100
vids = [v['id'] for v in videos]
details = check_details(vids)

print(f"\nAnalyzing {len(videos)} videos...\n")

for v in videos:
    vid = v['id']
    title = v['title']
    detail = details.get(vid, {})
    duration = detail.get('duration', 0)
    tags = detail.get('tags', [])
    
    is_short = duration <= 60
    has_mv_keyword = "Music Video" in title or "MV" in title
    
    type_label = "OTHER"
    if is_short:
        type_label = "SHORT"
    elif has_mv_keyword:
        type_label = "MV (Likely)"
    
    print(f"[{type_label}] {title[:60]}... (Duration: {duration}s)")

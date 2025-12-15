from googleapiclient.discovery import build
import json

api_key = "AIzaSyAfIovLQzP0mpxsz5db7VjLulFdY5ZrIXY"
youtube = build('youtube', 'v3', developerKey=api_key)

print("--- Test 1: Get Video Info directly ---")
try:
    # Snow Man "Dangerholic"
    request = youtube.videos().list(
        part="snippet,statistics",
        id="i5586Z2y2h0" 
    )
    response = request.execute()
    print(json.dumps(response, indent=2))
except Exception as e:
    print(e)
    
print("\n--- Test 2: Search Channel by Handle ---")
try:
    # Using 'q' to search
    request = youtube.search().list(
        part="snippet",
        q="Snow Man",
        type="channel",
        maxResults=1
    )
    response = request.execute()
    if 'items' in response and response['items']:
        found_id = response['items'][0]['id']['channelId']
        print(f"FOUND CHANNEL ID: {found_id}")
        
        # Check details
        request2 = youtube.channels().list(
            part='contentDetails',
            id=found_id
        )
        resp2 = request2.execute()
        print("--- Channel Details ---")
        print(json.dumps(resp2, indent=2))
        
        uploads_id = resp2['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        print(f"UPLOADS ID: {uploads_id}")
        
        request3 = youtube.playlistItems().list(
            part='snippet',
            playlistId=uploads_id,
            maxResults=5
        )
        resp3 = request3.execute()
        print("--- Playlist Items ---")
        print(json.dumps(resp3, indent=2))
        
        if resp3['items']:
            test_vid_id = resp3['items'][0]['snippet']['resourceId']['videoId']
            print(f"Testing statistics for video ID: {test_vid_id}")
            
            stats_req = youtube.videos().list(
                part='statistics',
                id=test_vid_id
            )
            stats_resp = stats_req.execute()
            print("--- Stats Response ---")
            print(json.dumps(stats_resp, indent=2))

    else:
        print("No channel found in search.")
except Exception as e:
    print(e)

import isodate
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

class YouTubeClient:
    def __init__(self, api_key):
        self.youtube = build('youtube', 'v3', developerKey=api_key)

    def get_channel_videos(self, channel_id, limit=50, full_scan=False):
        """
        Get latest videos from a channel.
        Note: Searching by channel ID is the easiest way to get uploads.
        """
        videos = []
        try:
            # 1. Get Uploads Playlist ID
            request = self.youtube.channels().list(
                part='contentDetails',
                id=channel_id
            )
            response = request.execute()
            
            if not response.get('items'):
                print(f"Channel {channel_id} not found.")
                return []

            uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

            # 2. Get Videos from Playlist with Pagination
            next_page_token = None
            total_fetched = 0
            
            print(f"Fetching videos from playlist: {uploads_playlist_id} (Full Scan: {full_scan})")

            while True:
                # Decide max results for this batch
                batch_limit = 50
                
                request = self.youtube.playlistItems().list(
                    part='snippet',
                    playlistId=uploads_playlist_id,
                    maxResults=batch_limit,
                    pageToken=next_page_token
                )
                response = request.execute()

                items = response.get('items', [])
                if not items:
                    break

                # Temporary list to hold basic info before fetching details
                batch_videos = []
                video_ids = []
                
                for item in items:
                    vid = item['snippet']['resourceId']['videoId']
                    video_ids.append(vid)
                    batch_videos.append({
                        'id': vid,
                        'title': item['snippet']['title'],
                        'published_at': item['snippet']['publishedAt']
                    })
                
                # 3. Get Statistics and ContentDetails (Duration)
                if video_ids:
                    stats_request = self.youtube.videos().list(
                        part='statistics,contentDetails',
                        id=','.join(video_ids)
                    )
                    stats_response = stats_request.execute()
                    
                    # Create a map for easy lookup
                    details_map = {item['id']: item for item in stats_response['items']}
                    
                    for video in batch_videos:
                        sid = video['id']
                        if sid in details_map:
                            stats = details_map[sid].get('statistics', {})
                            content = details_map[sid].get('contentDetails', {})
                            
                            video['view_count'] = int(stats.get('viewCount', 0))
                            
                            # Parse duration
                            duration_iso = content.get('duration', 'PT0S')
                            try:
                                video['duration_seconds'] = isodate.parse_duration(duration_iso).total_seconds()
                            except:
                                video['duration_seconds'] = 0
                        else:
                            video['view_count'] = 0
                            video['duration_seconds'] = 0
                        
                        videos.append(video)

                total_fetched += len(items)
                next_page_token = response.get('nextPageToken')

                if not full_scan and total_fetched >= limit:
                    break
                
                if not next_page_token:
                    break
                    
                # Creating a break point for safety if full scan is too large (e.g. > 2000)
                if full_scan and total_fetched > 2000:
                    print("Safety limit reached (2000 videos). Stopping scan.")
                    break

            return videos

        except Exception as e:
            print(f"An error occurred: {e}")
            return []

if __name__ == "__main__":
    # Test stub - requires valid API Key
    # api_key = "YOUR_KEY"
    # client = YouTubeClient(api_key)
    # vids = client.get_channel_videos("UCuFPaemAaMR8RJIUZBn7drA", limit=5)
    # print(vids)
    pass

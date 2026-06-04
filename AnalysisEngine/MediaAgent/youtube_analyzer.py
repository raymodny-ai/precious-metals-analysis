import os
from googleapiclient.discovery import build

class YouTubeAnalyzer:
    def __init__(self):
        self.api_key = os.getenv('YOUTUBE_API_KEY')
        self.youtube = None
        if self.api_key:
            self.youtube = build('youtube', 'v3', developerKey=self.api_key)
    
    def search_videos(self, query, max_results=5):
        if not self.youtube:
            print("YouTube API key not found")
            return []
        
        try:
            request = self.youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                maxResults=max_results,
                order="date"
            )
            response = request.execute()
            videos = []
            for item in response.get('items', []):
                videos.append({
                    'title': item['snippet']['title'],
                    'description': item['snippet']['description'],
                    'videoId': item['id']['videoId'],
                    'channelTitle': item['snippet']['channelTitle']
                })
            return videos
        except Exception as e:
            print(f"YouTube search error: {e}")
            return []

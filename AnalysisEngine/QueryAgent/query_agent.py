import requests
import os

class QueryAgent:
    def __init__(self):
        self.google_api_key = os.getenv('GOOGLE_API_KEY')
        self.google_cse_id = os.getenv('GOOGLE_CSE_ID')
        self.bing_api_key = os.getenv('BING_API_KEY')
    
    def search_google(self, query, num=10):
        if not self.google_api_key or not self.google_cse_id:
            print("Google API key or CSE ID not found")
            return []
        
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            'key': self.google_api_key,
            'cx': self.google_cse_id,
            'q': query + " USA", # Force US context
            'num': num,
            'gl': 'us' # Geolocation US
        }
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json().get('items', [])
        except Exception as e:
            print(f"Google search error: {e}")
            return []

    def search_bing(self, query, count=10):
        # Placeholder for Bing
        return []

    def search(self, query):
        # Primary: Google, Secondary: Bing
        results = self.search_google(query)
        if not results:
            results = self.search_bing(query)
        return results

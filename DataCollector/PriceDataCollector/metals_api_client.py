import requests
import os

class MetalsAPIClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv('METALS_API_KEY')
        self.base_url = "https://metals-api.com/api"
    
    def get_latest_rates(self, base='USD', symbols=['XAU', 'XAG', 'XPT', 'XPD']):
        """
        Get latest rates for precious metals.
        Default symbols: Gold (XAU), Silver (XAG), Platinum (XPT), Palladium (XPD)
        """
        endpoint = f"{self.base_url}/latest"
        params = {
            'access_key': self.api_key,
            'base': base,
            'symbols': ','.join(symbols)
        }
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching data from Metals-API: {e}")
            return None

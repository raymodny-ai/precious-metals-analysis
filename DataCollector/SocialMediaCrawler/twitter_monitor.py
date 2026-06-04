import tweepy
import os

class TwitterMonitor:
    def __init__(self):
        self.bearer_token = os.getenv('TWITTER_BEARER_TOKEN')
        self.client = None
        if self.bearer_token:
            self.client = tweepy.Client(bearer_token=self.bearer_token)
    
    def search_tweets(self, query, max_results=10):
        if not self.client:
            print("Twitter client not initialized")
            return []
        
        try:
            tweets = self.client.search_recent_tweets(query=query, max_results=max_results, tweet_fields=['created_at', 'public_metrics'])
            if not tweets.data:
                return []
            return tweets.data
        except Exception as e:
            print(f"Error searching tweets: {e}")
            return []

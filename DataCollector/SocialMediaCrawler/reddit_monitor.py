import praw
import os

class RedditMonitor:
    def __init__(self):
        self.client_id = os.getenv('REDDIT_CLIENT_ID')
        self.client_secret = os.getenv('REDDIT_CLIENT_SECRET')
        self.user_agent = os.getenv('REDDIT_USER_AGENT', 'PreciousInsight/1.0')
        
        if self.client_id and self.client_secret:
            self.reddit = praw.Reddit(
                client_id=self.client_id,
                client_secret=self.client_secret,
                user_agent=self.user_agent
            )
        else:
            self.reddit = None

    def get_hot_posts(self, subreddit_name='Gold', limit=10):
        if not self.reddit:
            print("Reddit client not initialized")
            return []
        
        try:
            subreddit = self.reddit.subreddit(subreddit_name)
            posts = []
            for post in subreddit.hot(limit=limit):
                posts.append({
                    'title': post.title,
                    'score': post.score,
                    'url': post.url,
                    'created_utc': post.created_utc,
                    'num_comments': post.num_comments
                })
            return posts
        except Exception as e:
            print(f"Error fetching Reddit posts: {e}")
            return []

import tweepy

class XClient:
    def __init__(self, consumer_key, consumer_secret, access_token, access_token_secret):
        self.auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        self.auth.set_access_token(access_token, access_token_secret)
        self.api = tweepy.API(self.auth)
        self.client = tweepy.Client(
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )

    def post_tweet(self, text):
        """
        Post a tweet using Tweepy Client (API v2).
        """
        try:
            response = self.client.create_tweet(text=text)
            print(f"Tweet posted successfully: {response}")
            return True
        except Exception as e:
            print(f"Error posting tweet: {e}")
            return False

if __name__ == "__main__":
    # Test stub
    pass

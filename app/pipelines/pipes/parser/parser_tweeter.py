import tweepy


api_key = '645ixiaHqw0XEC7l1YQ3612I0'
api_key_secret = 'ECuRQ6GnnbpCxV5Qp6Dhbdn2NTk8L5vtTb1VZDfqveErXXm7Vi'
access_token = '1760367164987494401-nXHx8AUpoN3w6J5EFmzIzIqkg9n8BL'
access_token_secret = 'McwFv9xBCoygcSlRIHkhZls5irmd1gJ6YjwARctX4RUq6'

auth = tweepy.OAuthHandler(api_key, api_key_secret)
auth.set_access_token(access_token, access_token_secret)

api = tweepy.API(auth)

def get_new_tweets(user_name):
    number_of_tweets = 1
    try:
        tweets = api.user_timeline(screen_name=user_name, count=number_of_tweets, tweet_mode='extended')
        for tweet in tweets:
            print(f"{tweet.user.name} сказал: {tweet.full_text}\n")
    except tweepy.TweepyException as e:
        print("Ошибка в получении твитов: " + str(e))

get_new_tweets('elonmusk')
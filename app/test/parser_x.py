import tweepy
import config_x
import os
import json
import requests
from requests_oauthlib import OAuth1, OAuth1Session
from ntscraper import Nitter
from pprint import pprint


# Authenticate with Twitter API
api_key = config_x.API_KEY
api_key_secret = config_x.API_SECRET
access_token = config_x.ACCESS_TOKEN
access_token_secret = config_x.ACCESS_TOKEN_SECRET
bearer_token = os.environ.get(config_x.BEARER_TOKEN)


def test1():
    auth = tweepy.OAuth1UserHandler(api_key, api_key_secret, access_token, access_token_secret)
    api = tweepy.API(auth)

    # Specify the screen name of the user whose pinned tweet you want to access
    screen_name = 'elonmusk'

    # Fetch the user's timeline
    user_timeline = api.user_timeline(screen_name=screen_name, count=1, include_rts=False, exclude_replies=True)

    # Iterate through the user's timeline to find the pinned tweet
    for tweet in user_timeline:
        if tweet.pinned:
            pinned_tweet = tweet
            break

    # Access the pinned tweet's text
    if pinned_tweet:
        print("Pinned Tweet:")
        print(pinned_tweet.text)
    else:
        print("This user does not have a pinned tweet.")


def test2():
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


def test3():
    auth = tweepy.OAuth1UserHandler(api_key, api_key_secret, access_token, access_token_secret)
    api = tweepy.API(auth)

    # Define the list of users you're interested in
    users = ['elonmusk']

    # Iterate through each user and fetch their tweets
    for user in users:
        print(f"Tweets from {user}:")
        tweets = api.user_timeline(screen_name=user, count=10)  # You can adjust the count as needed
        for tweet in tweets:
            print(tweet.text)
        print()


def test4(query, max_results=10): # query - username; max_results - max tweet count
    # Twitter API v2 endpoint for searching tweets
    url = "https://api.twitter.com/2/tweets/search/recent"

    # Request headers
    headers = {
        "Authorization": f"Bearer {bearer_token}"
    }

    # Request parameters
    params = {
        "query": query,
        "max_results": max_results
    }

    # Make the API request
    response = requests.get(url, headers=headers, params=params)
    data = response.json()

    # Print basic information about the tweets
    if "data" in data:
        print(f"Found {len(data['data'])} tweets matching the query '{query}':\n")
        for tweet in data["data"]:
            print(f"Tweet ID: {tweet['id']}")
            print(f"Author: {tweet['author_id']}")
            print(f"Text: {tweet['text']}")
            print("------------------------------")
    else:
        print("No tweets found.")


def test5():
    client = tweepy.Client(bearer_token=bearer_token)

    query = 'covid -is:retweet'
    response = ''

    try:
        response = client.search_recent_tweets(query=query, max_results=100)
        print("Tweets successfully reed!")
    except tweepy.TweepyException as e:
        print(f"An error occurred:\n{e}")

    print(response)


def test6():
    url = "https://api.twitter.com/2/tweets"

    # The data to send in the body of the request
    payload = {
        "text": "Hello, world! This is my first tweet via API."
    }

    # Creating OAuth 1 authentication object with your credentials
    auth = OAuth1(api_key, api_key_secret, access_token, access_token_secret)

    # Making a POST request to the Twitter API
    response = requests.post(url, json=payload, auth=auth)

    # Checking if the request was successful
    if response.status_code == 201:
        print("Successfully posted tweet.")
        tweet_id = response.json()['data']['id']
        print(f"Tweet ID: {tweet_id}")
    else:
        print("Failed to post tweet.")
        print(f"Status code: {response.status_code}, Response body: {response.text}")


def test7():
    auth = tweepy.OAuth1UserHandler(
        api_key,
        api_key_secret,
        access_token,
        access_token_secret
    )

    # Create an API object
    api = tweepy.API(auth)

    # Create a tweet
    tweet_text = 'Hello, world - this is my first tweet using Tweepy and Twitter API v2!'
    try:
        # Publish the tweet
        api.update_status(tweet_text)
        print("Tweet successfully sent!")
    except tweepy.TweepyException as e:
        print(f"An error occurred: {e}")


def test8():
    def create_url():
        # Specify the usernames that you want to lookup below
        # You can enter up to 100 comma-separated values.
        usernames = "usernames=TwitterDev,TwitterAPI"
        user_fields = "user.fields=description,created_at"
        # User fields are adjustable, options include:
        # created_at, description, entities, id, location, name,
        # pinned_tweet_id, profile_image_url, protected,
        # public_metrics, url, username, verified, and withheld
        url = "https://api.twitter.com/2/users/by?{}&{}".format(usernames, user_fields)
        return url

    def bearer_oauth(r):
        """
        Method required by bearer token authentication.
        """

        r.headers["Authorization"] = f"Bearer {bearer_token}"
        r.headers["User-Agent"] = "v2UserLookupPython"
        return r

    def connect_to_endpoint(url):
        response = requests.request("GET", url, auth=bearer_oauth, )
        print(response.status_code)
        if response.status_code != 200:
            raise Exception(
                "Request returned an error: {} {}".format(
                    response.status_code, response.text
                )
            )
        return response.json()

    url = create_url()
    json_response = connect_to_endpoint(url)
    print(json.dumps(json_response, indent=4, sort_keys=True))


def test9():
    # User fields are adjustable, options include:
    # created_at, description, entities, id, location, name,
    # pinned_tweet_id, profile_image_url, protected,
    # public_metrics, url, username, verified, and withheld
    fields = "created_at,description"
    params = {"usernames": "TwitterDev,TwitterAPI", "user.fields": fields}

    # Get request token
    request_token_url = "https://api.twitter.com/oauth/request_token"
    oauth = OAuth1Session(api_key, client_secret=api_key_secret)

    fetch_response = {}
    try:
        fetch_response = oauth.fetch_request_token(request_token_url)
    except ValueError:
        print(
            "There may have been an issue with the consumer_key or consumer_secret you entered."
        )

    resource_owner_key = fetch_response.get("oauth_token")
    resource_owner_secret = fetch_response.get("oauth_token_secret")
    print("Got OAuth token: %s" % resource_owner_key)

    # # Get authorization
    base_authorization_url = "https://api.twitter.com/oauth/authorize"
    authorization_url = oauth.authorization_url(base_authorization_url)
    print("Please go here and authorize: %s" % authorization_url)
    verifier = input("Paste the PIN here: ")

    # Get the access token
    access_token_url = "https://api.twitter.com/oauth/access_token"
    oauth = OAuth1Session(
        api_key,
        client_secret=api_key_secret,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier,
    )
    oauth_tokens = oauth.fetch_access_token(access_token_url)

    access_token = oauth_tokens["oauth_token"]
    access_token_secret = oauth_tokens["oauth_token_secret"]

    # Make the request
    oauth = OAuth1Session(
        api_key,
        client_secret=api_key_secret,
        resource_owner_key=access_token,
        resource_owner_secret=access_token_secret,
    )

    response = oauth.get(
        "https://api.twitter.com/2/users/by", params=params
    )

    if response.status_code != 200:
        raise Exception(
            "Request returned an error: {} {}".format(response.status_code, response.text)
        )

    print("Response code: {}".format(response.status_code))

    json_response = response.json()

    print(json.dumps(json_response, indent=4, sort_keys=True))


def test10():
    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'User-Agent': 'tweepy/0.8.0'
    }

    # Define the query parameter
    query = 'from:twitterdev'

    # Make the API call to the recent search endpoint
    response = requests.get(
        'https://api.twitter.com/2/tweets/search/recent',
        headers=headers,
        params={'query': query}
    )

    # Check the response status code
    if response.status_code == 200:
        # Parse the JSON response
        data = json.loads(response.text)

        # Print the first tweet's ID
        print(data['data'][0]['id'])
    else:
        print(f'Error: {response.status_code}\n{response.text}')


def test11():
    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'Content-Type': 'application/json'
    }

    # Define the tweet content
    tweet_text = "Hello, this is a test tweet from the Twitter API v2!"

    # Create the tweet data
    tweet_data = {
        'text': tweet_text
    }

    # Make the API call to post a tweet
    response = requests.post(
        'https://api.twitter.com/2/tweets',
        headers=headers,
        data=json.dumps(tweet_data)
    )

    # Check the response status code
    if response.status_code == 201:
        print("Tweet posted successfully!")
    else:
        print(f'Error: {response.status_code}\n{response.text}')


def test12():
    search_url = "https://api.twitter.com/2/users/2244994945/tweets"

    # Optional params: start_time,end_time,since_id,until_id,max_results,next_token,
    # expansions,tweet.fields,media.fields,poll.fields,user.fields
    query_params = {'tweet.fields': 'created_at,text'}

    def bearer_oauth(r):
        """
        Method required by bearer token authentication.
        """
        r.headers["Authorization"] = f"Bearer {bearer_token}"
        return r

    def connect_to_endpoint(url, params):
        response = requests.get(url, auth=bearer_oauth, params=params)
        print(response.status_code)
        if response.status_code != 200:
            raise Exception(response.status_code, response.text)
        return response.json()

    json_response = connect_to_endpoint(search_url, query_params)
    print(json.dumps(json_response, indent=4, sort_keys=True))


def test13():
    user_id = "28481667"

    create_tweet_url = f"https://api.twitter.com/2/users/{user_id}/tweets"

    def bearer_oauth(r):
        """
        Method required by bearer token authentication.
        """
        r.headers["Authorization"] = f"Bearer {bearer_token}"
        return r

    def connect_to_endpoint(url, data):
        response = requests.post(url, auth=bearer_oauth, json=data)
        print(response.status_code)
        if response.status_code != 201:
            raise Exception(response.status_code, response.text)
        return response.json()

    tweet_text = "This is a sample tweet posted using the Twitter API v2!"
    payload = {"text": tweet_text}
    json_response = connect_to_endpoint(create_tweet_url, payload)
    print(json.dumps(json_response, indent=4, sort_keys=True))


def test14():
    scraper = Nitter(log_level=1, skip_instance_check=False)
    tweets = scraper.get_tweets("elonmusk", mode="user", number=10)
    pprint(tweets)


def test15():
    auth = tweepy.OAuthHandler(api_key, api_key_secret)
    auth.set_access_token(access_token, access_token_secret)

    # Create API object
    api = tweepy.API(auth)

    def create_tweet(text: str):
        try:
            # Create a tweet
            response = api.update_status(status=text)
            print(f"Successfully tweeted: {text} (ID: {response.id})")
        except tweepy.TweepyException as e:
            print(f"An error occurred: {e}")

    # Text you want to tweet
    tweet_text = "Hello Twitter World!"

    # Call the function to make a tweet
    create_tweet(tweet_text)


def test16():
    auth = tweepy.OAuth1UserHandler(
        api_key, api_key_secret,
        access_token, access_token_secret
    )

    api = tweepy.API(auth)

    # Define the tweet parser function
    def parse_tweets(search_query, max_tweets=100):
        """
        Fetches tweets by a search query and parses their text.
        :param search_query: The query to search for tweets.
        :param max_tweets: The maximum number of tweets to fetch.
        :return: A list of tweet texts.
        """
        tweets = tweepy.Cursor(api.search_tweets, q=search_query, tweet_mode='extended').items(max_tweets)

        tweet_texts = []
        #    for tweet in tweets:
        # In the full-text mode, the text of the tweet is in `full_text`.
        #        tweet_texts.append(tweet.full_text)

        return tweet_texts

    # Use the parser to fetch and display tweets
    search_query = "#python"  # Example hashtag to search for
    parsed_tweets = parse_tweets(search_query, max_tweets=10)

    for tweet_text in parsed_tweets:
        print(tweet_text)

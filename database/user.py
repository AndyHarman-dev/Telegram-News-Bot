import json


# User preferences class realises a user preferences object to save it in database
class UserPreferences:
    def __init__(self, user_id=0, topics=[], avoid_topics=[], frequency=""):
        self.user_id = user_id
        self.topics = topics
        self.avoid_topics = avoid_topics
        self.frequency = frequency

    def to_json(self):
        return json.dumps({
            'user_id': self.user_id,
            'data': {
                'topics': self.topics,
                'avoid_topics': self.avoid_topics,
                'frequency': self.frequency
            }
        })


# User class realises a user object to save it in database
class User:
    def __init__(self, user_id=0, user_name="", has_pro=False, preferences: UserPreferences = UserPreferences()):
        self.user_id = user_id
        self.user_name = user_name
        self.has_pro = has_pro
        self.preferences = preferences
        self.accounts = []

    def to_json(self):
        return json.dumps({
            'user_id': self.user_id,
            'user_name': self.user_name,
            'has_pro': self.has_pro,
            'preferences': self.preferences.to_json()
        })

import json
import entity


# User preferences class realises a user preferences object to save it in database
class Preferences:
    """
    Initializes an instance of the class.

    Args:
        entity_id (int): The ID of the entity. Defaults to 0. (entity is either a group or an account)
        topics (list): A list of topics. Defaults to an empty list.
        avoid_topics (list): A list of topics to avoid. Defaults to an empty list.
        frequency (str): The frequency of something. Defaults to an empty string.
    """

    def __init__(self, entity_id=0, topics=[], avoid_topics=[], frequency=""):
        self.entity_id = entity_id
        self.topics = topics
        self.avoid_topics = avoid_topics
        self.frequency = frequency

    def to_json(self):
        return json.dumps({
            'entity_id': self.entity_id,
            'data': {
                'topics': self.topics,
                'avoid_topics': self.avoid_topics,
                'frequency': self.frequency
            }
        })


# User class realises a user object to save it in database
class User:
    def __init__(self, user_id=0, user_name="", has_pro=False, preferences: Preferences = Preferences()):
        self.user_id = user_id
        self.user_name = user_name
        self.has_pro = has_pro

        self.platform_entities = {}

    def to_json(self):
        return json.dumps({
            'user_id': self.user_id,
            'user_name': self.user_name,
            'has_pro': self.has_pro,
            'groups': self.groups,
            'accounts': self.accounts
        })

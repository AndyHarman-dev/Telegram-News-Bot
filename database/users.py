import json
import re


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

    @staticmethod
    def validate_preferences(input_string):
        # Split the input string into lines
        lines = input_string.split("\n")

        # Check if there are exactly three lines
        if len(lines) != 3:
            return False

        # Validate the topics line
        topics_line = lines[0]
        if not topics_line.startswith("topics:"):
            return False
        topics = topics_line[len("topics:"):].split(",")
        if not all(re.match(r"^\s*\w+\s*$", topic) for topic in topics):
            return False

        # Validate the avoid_topics line
        avoid_topics_line = lines[1]
        if not avoid_topics_line.startswith("avoid_topics:"):
            return False
        avoid_topics = avoid_topics_line[len("avoid_topics:"):].split(",")
        if not all(re.match(r"^\s*\w+\s*$", avoid_topic) for avoid_topic in avoid_topics):
            return False

        # Validate the frequency line
        frequency_line = lines[2]
        if not frequency_line.startswith("frequency:"):
            return False
        frequency = frequency_line[len("frequency:"):].strip()
        if frequency not in ["daily", "weekly", "monthly"]:
            return False

        # If all checks passed, the input is valid
        return True

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

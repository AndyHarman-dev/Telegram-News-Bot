import users


# Entity is a base class for a group or account
class Entity:
    """
    Initializes a new instance of the class.

    Args:
        entity_id (int): The unique identifier of the entity.
        entity_name (str): The name of the entity.
    """

    def __init__(self, entity_id, entity_name, preferences: users.Preferences, platform):
        self.entity_id = entity_id
        self.entity_name = entity_name
        self.preferences = preferences
        self.platform = platform


# Group is an entity that represents a group of a social media platform
class Group(Entity):
    """
    Initializes a new instance of the Group class.

    Args:
        entity_id (int): The ID of the entity.
        entity_name (str): The name of the entity.
    """

    def __init__(self, entity_id, entity_name, platform):
        super().__init__(entity_id, entity_name, platform)


class Account(Entity):
    """
    Initializes a new instance of the Account class.
    """

    def __init__(self, entity_id, entity_name, platform):
        super().__init__(entity_id, entity_name, platform)

from app.interfaces.prototype import IPrototype
from app.misc.log_helper import LogHelper

LOG_REGISTRY = LogHelper(__name__, "PrototypeRegistry")


class PrototypeRegistry:
    _instance = None
    _registry = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PrototypeRegistry, cls).__new__(cls)
        return cls._instance

    @classmethod
    def register_object(cls, key, obj, category=None):
        if not isinstance(obj, IPrototype):
            LOG_REGISTRY.raise_exception_with_log(ValueError("Object must implement the IPrototype interface"))
        if category not in cls._registry:
            cls._registry[category] = {}
        cls._registry[category][key] = obj

    @classmethod
    def get_object(cls, key, category=None):
        if category is None:
            if key in cls._registry:
                return cls._registry[key].clone()
            else:
                LOG_REGISTRY.raise_exception_with_log(ValueError("Prototype not found"))
        elif category and category in cls._registry:
            return cls._registry[category][key].clone()

    @classmethod
    def get_category_as_list(cls, category) -> list:
        if category in cls._registry:
            return list(cls._registry[category].values())
        else:
            LOG_REGISTRY.raise_exception_with_log(ValueError(f"Category {category} does not exist!"))

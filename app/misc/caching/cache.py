class Node:
    """
    Wrapper for a key,value pair of LRUCache
    """

    def __init__(self, key, value):
        self.key = key
        self.value = value
        self.prev = None
        self.next = None


class LRUCache:
    """The cache has a fixed capacity, and when the capacity is exceeded, the least recently used item is evicted.

    Attributes:
        capacity: The maximum capacity of the cache.
        cache: A dictionary mapping keys to nodes in the cache.
        head: A dummy node at the head of the cache.
        tail: A dummy node at the tail of the cache.
    """
    _instance = None  # Singleton instance

    def __new__(cls, capacity):
        """
            Creates a new instance of the LRUCache class.

            Args:
                capacity: The maximum capacity of the cache.

            Returns:
                 An instance of the LRUCache class.
        """
        if cls._instance is None:
            cls._instance = super(LRUCache, cls).__new__(cls)
            cls._instance.capacity = capacity
            cls._instance.cache = {}
            cls._instance.head = Node(0, 0)  # dummy node
            cls._instance.tail = Node(0, 0)  # dummy node
            cls._instance.head.next = cls._instance.tail
            cls._instance.tail.prev = cls._instance.head
        return cls._instance

    def get(self, key):
        """
            Retrieves an item from the cache.

            Args:
                key: The key of the item to retrieve.

            Returns:
                The value of the item, or -1 if the item is not in the cache.
            """
        if key in self.cache:
            node = self.cache[key]
            self._remove(node)
            self._add(node)
            return node.value
        return -1

    def put(self, key, value):
        """
            Adds an item to the cache.

            Args:
                key: The key of the item to add.
                value: The value of the item to add.
            """
        if key in self.cache:
            self._remove(self.cache[key])
        node = Node(key, value)
        self._add(node)
        self.cache[key] = node
        if len(self.cache) > self.capacity:
            node = self.head.next
            self._remove(node)
            del self.cache[node.key]

    def _remove(self, node):
        """
          Removes a node from the cache.

          Args:
              node: The node to remove.
          """
        prev = node.prev
        next = node.next
        prev.next = next
        next.prev = prev

    def _add(self, node):
        """
            Adds a node to the cache.

            Args:
                node: The node to add.
            """
        prev = self.tail.prev
        prev.next = node
        self.tail.prev = node
        node.prev = prev
        node.next = self.tail


COMMON_CACHE = LRUCache(1000)

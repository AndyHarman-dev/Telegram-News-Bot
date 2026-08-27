from app.database.db_helper import DatabaseModel, DatabaseHelper


class ChannelManager:
    # Custom methods ======================================
    @staticmethod
    def get_channels_by_type(channel_resource_type):
        """
        Retrieves a list of channels of a specified type with their IDs and URLs.

        Args:
            channel_resource_type (int): The type of channel to filter by.

        Returns:
            list: A list of tuples with channel ID and URL of the specified type.
        """

        query = """
            SELECT channel_id, channel_url FROM channels WHERE channel_resource_type = ?
        """
        return DatabaseHelper.safe_execute_query(query, (channel_resource_type,))

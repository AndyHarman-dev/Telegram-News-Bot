from app.database.db_helper import DatabaseModel, DatabaseHelper, Post

class PostManager():

    @staticmethod
    def is_content_exists_for_post(post_id):
        """
        Checks if content exists for a given post ID in the posts_content table.

        Args:
            post_id (int): The ID of the post to check.

        Returns:
            bool: True if content exists, False otherwise.
        """
        query = """
            SELECT 1 FROM posts_content 
            WHERE post_id = ?
        """
        result = DatabaseHelper.safe_execute_query(query, (post_id,))
        return bool(result)


    @staticmethod
    def get_post_content(post_id):
        """
        Retrieves the content for a given post. If the content does not exist in the database,
        it fetches the content using the URL, stores it, and then returns it.

        Args:
            post_id (int): The ID of the post.

        Returns:
            str: The content of the post.
        """
        query = """
            SELECT content FROM posts_content
            WHERE post_id = ?
        """
        result = DatabaseHelper.safe_execute_query(query, (post_id,))
        return result[0][0] if result else None

    @staticmethod
    def get_post_by_id(post_id):
        """
        Retrieve post by its ID.

        Args:
            post_id (int): The ID of the post.

        Returns:
            Post: The post entity.
        """
        query = """
            SELECT * FROM posts
            WHERE post_id = ?
        """
        result = DatabaseHelper.safe_execute_query(query, (post_id,))
        if result:
            post_id, channel_id, title, content, link, rating, popularity, date = result[0]
            return Post(post_id, channel_id, title, content, link, rating, popularity, date)
        else:
            return None



    @staticmethod
    def delete_old_posts(days_old):
        """
        Delete old posts from the database based on the specified number of days old.
        :param days_old: int - Number of days old for posts to be deleted
        :return: None
        """
        query = """
            DELETE FROM posts
            WHERE julianday(CURRENT_DATE) - julianday(date) > ?
        """
        DatabaseHelper.safe_execute_query(query, (days_old,))


if __name__ == '__main__':

    Post = PostManager.get_post_by_id(54)
    print(Post.link)
    print(Post.channel_id)
    #pass
    #post_content = PostManager.get_post_content(54)
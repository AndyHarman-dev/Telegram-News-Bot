from app.database.db_helper import DatabaseHelper
from app.database.db_llm import DatabaseLlmManager


class MessageManager:
    @staticmethod
    async def create_message(user_id, chat_id, role, content, summary=None):
        """
        Creates a new message in the database.

        Args:
            user_id (int): The ID of the user who sent the message.
            chat_id (int): The ID of the chat where the message was sent.
            role (int): The role of the user (1 - user, 2 - bot, 3 - etc).
            content (str): The content of the message.
            summary (str, optional): A summary or processed version of the message content.
        """
        query = """
            INSERT INTO messages (user_id, chat_id, role, content, summary)
            VALUES (?, ?, ?, ?, ?)
        """

        #summarize only long messages
        if summary is None and (len(content) > 512) :
            summary = await DatabaseLlmManager.llm_summarize_text(content)
        else:
            summary = content

        DatabaseHelper.safe_execute_query(query, (user_id, chat_id, role, content, summary) )
        return



    @staticmethod
    def get_chat_context(chat_id, full_count, summary_count):
        """
        Retrieves the latest messages from a chat, with a specified number of full messages and summary messages.

        Args:
            chat_id (int): The ID of the chat.
            full_count (int): The number of full messages to retrieve.
            summary_count (int): The number of summary messages to retrieve.

        Returns:
            list: A list of dictionaries, each representing a message.
        """
        query = """
            SELECT * FROM (
                SELECT message_id, user_id, chat_id, role, content, summary, date
                FROM messages
                WHERE chat_id = ?
                ORDER BY date DESC
                LIMIT ?
            ) sub
            ORDER BY date ASC
        """
        total_count = full_count + summary_count
        messages = DatabaseHelper.safe_execute_query(query, (chat_id, total_count))

        # Process messages to return full content for the latest 'full_count' messages
        # and summary for the earlier 'summary_count' messages
        processed_messages = []
        for i, message in enumerate(messages):
            if i < summary_count:
                # Use summary for older messages
                processed_message = {
                    'message_id': message[0],
                    'user_id': message[1],
                    'chat_id': message[2],
                    'role': message[3],
                    'content': message[5],  # summary
                    'date': message[6]
                }
            else:
                # Use full content for newer messages
                processed_message = {
                    'message_id': message[0],
                    'user_id': message[1],
                    'chat_id': message[2],
                    'role': message[3],
                    'content': message[4],  # full content
                    'date': message[6]
                }
            processed_messages.append(processed_message)

        return processed_messages

    @staticmethod
    def messages_to_string(messages):
        """
        Converts a list of message dictionaries into a single string.
        Each message summary is prefixed with the role ('User' or 'ChatGPT').

        Args:
            messages (list): A list of dictionaries, each representing a message.

        Returns:
            str: A single string containing all messages, each on a new line.
        """
        combined_message = ""
        for message in messages:
            role_prefix = "User:" if message['role'] == 1 else "Assistant:"
            combined_message += f"{role_prefix} {message['content']}\n"

        return combined_message


if __name__ == '__main__':
    print("Testing DB Message")
    context = MessageManager.get_chat_context(466001259, 10, 10)
    print(context)

    processed_messages = MessageManager.get_chat_context(466001259, 10, 10)
    combined_message = MessageManager.messages_to_string(processed_messages)
    print(combined_message)
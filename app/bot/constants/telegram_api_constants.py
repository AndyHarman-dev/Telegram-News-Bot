import os

telegram_api_config = {
    'max_messages_per_second': int(os.environ.get('MAX_MESSAGES_PER_SECOND', 30)),
    'max_messages_per_group_per_minute': int(os.environ.get('MAX_MESSAGES_PER_GROUP_PER_MINUTE', 20)),
    'max_bulk_notifications_per_second': int(os.environ.get('MAX_BULK_NOTIFICATIONS_PER_SECOND', 30)),
    'max_message_length': int(os.environ.get('MAX_MESSAGE_LENGTH', 4096)),
    'max_message_size': int(os.environ.get('MAX_MESSAGE_SIZE', 512)),
    'max_photo_file_size': int(os.environ.get('MAX_PHOTO_FILE_SIZE', 10 * 1024 * 1024)),  # 10 MB
    'max_photo_thumbnail_dimensions': int(os.environ.get('MAX_PHOTO_THUMBNAIL_DIMENSIONS', 320)),
    'max_photo_dimensions': int(os.environ.get('MAX_PHOTO_DIMENSIONS', 1280)),  # can be increased to 2560 in some clients
    'max_document_file_size': int(os.environ.get('MAX_DOCUMENT_FILE_SIZE', 50 * 1024 * 1024)),  # 50 MB
    'max_sticker_file_size': int(os.environ.get('MAX_STICKER_FILE_SIZE', 512 * 1024)),  # 512 KB
    'max_video_note_duration': int(os.environ.get('MAX_VIDEO_NOTE_DURATION', 60)),
    'max_video_note_file_size': int(os.environ.get('MAX_VIDEO_NOTE_FILE_SIZE', 16 * 1024 * 1024)),  # 16 MB
}


# Maximum number of messages that can be sent per second
MAX_MESSAGES_PER_SECOND = 30

# Maximum number of messages that can be sent to the same group or channel per minute
MAX_MESSAGES_PER_GROUP_PER_MINUTE = 20

# Maximum number of messages that can be sent for bulk notifications per second
# before getting 429 errors
MAX_BULK_NOTIFICATIONS_PER_SECOND = 30

# Maximum number of characters in a text message
MAX_MESSAGE_LENGTH = 4096

MAX_MESSAGE_SIZE = 512

# Maximum file size for photos
MAX_PHOTO_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

# Maximum width and height for photo thumbnails
MAX_PHOTO_THUMBNAIL_DIMENSIONS = 320

# Maximum width and height for sent photos
MAX_PHOTO_DIMENSIONS = 1280  # Can be increased to 2560 in some clients

# Maximum file size for documents/files
MAX_DOCUMENT_FILE_SIZE = 50 * 1024 * 1024  # 50 MB

# Maximum file size for stickers
MAX_STICKER_FILE_SIZE = 512 * 1024  # 512 KB

# Maximum seconds of video in a round message
MAX_VIDEO_NOTE_DURATION = 60

# Maximum file size for video notes
MAX_VIDEO_NOTE_FILE_SIZE = 16 * 1024 * 1024  # 16 MB
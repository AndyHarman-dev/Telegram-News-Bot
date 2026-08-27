import feedparser
import os
import openai
import logging
from dotenv import load_dotenv
import sqlite3
from hashlib import md5
import requests
from bs4 import BeautifulSoup #for HTML to text convert
from PIL import Image #images work
from io import BytesIO
import json
from base64 import b64decode #for openai image convert
from pathlib import Path
import asyncio


import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from telegram import Bot






def main():

    init_data()    


    TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    CHANNEL_ID = '@ModEraTest'  # or '-100xxxxxxxxxx' if using numerical ID
#    CHANNEL_ID = 1001807035279
    
    application = ApplicationBuilder().token(TOKEN).build()
    
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)
    
    application.run_polling()

 #   with open('path_to_image.jpg', 'rb') as photo:
 #       bot.send_photo(chat_id=CHANNEL_ID, photo=photo, caption="Caption for the photo")


def init_data():
    # Setup logging
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)

        # Read .env file
    load_dotenv()

    # Check if the required environment variables are set
    required_values = ['TELEGRAM_BOT_TOKEN', 'OPENAI_API_KEY']
    missing_values = [value for value in required_values if os.environ.get(value) is None]
    if len(missing_values) > 0:
        logging.error(f'The following environment values are missing in your .env: {", ".join(missing_values)}')
        exit(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = Bot(token=TOKEN)
    await bot.send_message(chat_id=CHANNEL_ID, 
                     text="HELLO WORLD, Hello from my bot! ")

if __name__ == '__main__':
    main()
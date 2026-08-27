import asyncio
from telegram import Bot, InputFile
from telegram.ext import Application, CommandHandler, filters, ContextTypes
import os  # <- Import the os module
import os
import sys


async def delayed_send(bot: Bot, chat_id: int, delay_seconds: int, text: str):
    await asyncio.sleep(delay_seconds)
    await bot.send_message(chat_id=chat_id, text=text)

    # This will give you the directory of the current script: "D:\Developer\Python\Projects\PythonBot\PythonBot\App"
    script_directory = os.path.dirname(os.path.abspath(sys.argv[0]))

# Now, construct the absolute path to the image
    photo_path = os.path.join(script_directory, "../../images/beaut-1692905124-0_watermarked.jpg")

    # Check if the path exists
    if not os.path.exists(photo_path):
        print(f"File {photo_path} does not exist.")
        return

    with open(photo_path, 'rb') as photo_file:
        await bot.send_photo(chat_id=chat_id, photo=photo_file, caption="Это моя котенок. Ее зовут Луна.")



async def start_sending_delayed_messages():
    bot = Bot(token=TOKEN)
    chat_id = -1001807035279
    await delayed_send(bot, chat_id, 5, "Отложенное сообщение отправлено через 10 секунд!")
    await delayed_send(bot, chat_id, 10, "Отложенное сообщение отправлено через 20 секунд!")

if __name__ == "__main__":
    TOKEN = "6472581335:AAF8Wa-WE2gX9Ozf17ji1eX25GsCp3UzTvg"
    asyncio.run(start_sending_delayed_messages())



"""

import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, filters, ContextTypes

TOKEN = "6472581335:AAF8Wa-WE2gX9Ozf17ji1eX25GsCp3UzTvg"

async def delayed_send(bot: Bot, chat_id: int, delay_seconds: int, text: str):
    await asyncio.sleep(delay_seconds)
    await bot.send_message(chat_id=chat_id, text=text)

async def command_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    chat_id = update.message.chat_id
    
    # Запланировать отправку сообщения через 10 секунд
    asyncio.create_task(delayed_send(bot, chat_id, 10, "Отложенное сообщение!"))
    await update.message.reply_text("Сообщение будет отправлено через 10 секунд!")

def main():
    app = Application.builder().token(TOKEN).build()

    # Добавление обработчика команды
    app.add_handler(CommandHandler('start', command_start))

    # Запуск бота
    print("Bot started...")
    app.run_polling(poll_interval=3)

if __name__ == "__main__":
    main()

    """
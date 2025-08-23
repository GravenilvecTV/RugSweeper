from telegram import Bot
import asyncio
import dotenv
import os
dotenv.load_dotenv()

async def main():
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    updates = await bot.get_updates()
    print(updates[0].message.chat.id)

asyncio.run(main())
from telegram_utils import Bot
import asyncio
import dotenv
import os
dotenv.load_dotenv()

async def main():
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    updates = await bot.get_updates()
    if not updates:
        print("No updates found.")
    else:
        print(updates) 

asyncio.run(main())
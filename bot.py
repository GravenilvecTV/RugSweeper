import logging
import os
import asyncio
import threading
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler

from handlers import (
    start, choice_handler, add_rug, add_pumpfun, verify_token_handler,
    CHOOSING, ADD_RUG, ADD_PUMPFUN, VERIFY_TOKEN, markup
)
from wallet import wallet, wallet_choice_handler, WALLET_MENU
from pumpportal import fetch_new_tokens, sweep_callback_handler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

def start_pumpportal_thread():
    def runner():
        asyncio.run(fetch_new_tokens())
    thread = threading.Thread(target=runner, daemon=True)
    thread.start()

def main():
    application = ApplicationBuilder().token(TOKEN).build()
 
    # ConversationHandler pour la gestion des étapes
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start, filters=filters.ChatType.PRIVATE),
            CommandHandler("wallet", wallet, filters=filters.ChatType.PRIVATE)
        ],
        states={
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, choice_handler)],
            ADD_RUG: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_rug)],
            ADD_PUMPFUN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_pumpfun)],
            VERIFY_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_token_handler)],
            WALLET_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, wallet_choice_handler)],
        },
        fallbacks=[CommandHandler("start", start, filters=filters.ChatType.PRIVATE)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(sweep_callback_handler, pattern=r"^sweep:"))

    start_pumpportal_thread()
    application.run_polling()

if __name__ == '__main__':
    main()
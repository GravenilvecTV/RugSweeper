import logging
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler

from handlers import (
    start, choice_handler, add_rug, add_pumpfun, verify_token_handler,
    CHOOSING, ADD_RUG, ADD_PUMPFUN, VERIFY_TOKEN, markup
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

def main():
    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [MessageHandler(filters.TEXT & ~filters.COMMAND, choice_handler)],
            ADD_RUG: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_rug)],
            ADD_PUMPFUN: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_pumpfun)],
            VERIFY_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_token_handler)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    application.add_handler(conv_handler)
    application.run_polling()

if __name__ == '__main__':
    main()
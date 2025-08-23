import logging
import os
import re
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

CHOOSING, ADD_RUG, ADD_PUMPFUN, VERIFY_TOKEN = range(4)

reply_keyboard = [
    ["Add a rug address", "Show address list", "Verify token", "Cancel"]
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)

ADRESSES_FILE = "adresses.txt"

def load_addresses():
    if not os.path.exists(ADRESSES_FILE):
        return []
    with open(ADRESSES_FILE, "r") as f:
        return [line.strip() for line in f if line.strip()]

def load_address_counts():
    addresses = load_addresses()
    counts = {}
    for line in addresses:
        parts = line.split("|")
        rug_address = parts[0].strip()
        pumpfun_link = parts[1].strip() if len(parts) > 1 else ""
        key = (rug_address, pumpfun_link)
        counts[key] = counts.get(key, 0) + 1
    return counts

def save_address(address, pumpfun_link):
    with open(ADRESSES_FILE, "a") as f:
        f.write(f"{address} | {pumpfun_link}\n")

def is_valid_solana_address(address):
    pattern = r"^[1-9A-HJ-NP-Za-km-z]{32,44}$"
    return re.match(pattern, address) is not None

def address_exists(address, pumpfun_link):
    counts = load_address_counts()
    return (address, pumpfun_link) in counts

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    addresses = load_addresses()
    count = len(addresses)
    await update.message.reply_photo(
        photo="https://pbs.twimg.com/media/GzCWA2sWMAALOeZ?format=jpg&name=medium"
    )
    await update.message.reply_text(
        f"Welcome! What would you like to do?\n\nRegistered ruggers: {count}",
        reply_markup=markup
    )
    return CHOOSING

async def choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Add a rug address":
        await update.message.reply_text("Please send the rug address to add:")
        return ADD_RUG
    elif text == "Show address list":
        counts = load_address_counts()
        if counts:
            msg = "*🧹 Ruggers list*\n\n"
            for idx, ((rug_address, pumpfun_link), count) in enumerate(counts.items(), 1):
                msg += f"{idx}. [{rug_address}]({pumpfun_link}) — ({count} report{'s' if count > 1 else ''})\n"
            await update.message.reply_text(msg, parse_mode="Markdown")
        else:
            await update.message.reply_text("No rug address registered.")
        return CHOOSING
    elif text == "Verify token":
        await update.message.reply_text("Please send the token address to verify:")
        return VERIFY_TOKEN
    elif text == "Cancel":
        await update.message.reply_text("Operation cancelled.")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Invalid choice.", reply_markup=markup)
        return CHOOSING

async def add_rug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text
    if not is_valid_solana_address(address):
        await update.message.reply_text(
            "Invalid Solana address format.\nPlease send a valid Solana address (32-44 base58 characters)."
        )
        return ADD_RUG
    context.user_data["rug_address"] = address
    await update.message.reply_text("Now, please send the Pump.fun page link for this rugger:")
    return ADD_PUMPFUN

async def add_pumpfun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pumpfun_link = update.message.text
    pattern = r"^https://pump\.fun/profile/[A-Za-z0-9]+\?tab=(balances|followers|coins)$"
    if not re.match(pattern, pumpfun_link):
        await update.message.reply_text(
            "Invalid Pump.fun link format.\nPlease send a link like: https://pump.fun/profile/GuZLJe?tab=balances, tab=followers or tab=coins"
        )
        return ADD_PUMPFUN

    address = context.user_data.get("rug_address", "")
    save_address(address, pumpfun_link)
    counts = load_address_counts()
    count = counts.get((address, pumpfun_link), 1)
    await update.message.reply_text(
        f"Rug address added: {address}\nPump.fun link: {pumpfun_link}\nThis entry has been added {count} time{'s' if count > 1 else ''}."
    )
    await update.message.reply_text("Thank you! The address and link have been saved.")
    await update.message.reply_text("What would you like to do?", reply_markup=markup)
    return CHOOSING

async def verify_token_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    if not is_valid_solana_address(address):
        await update.message.reply_text(
            "Invalid Solana address format.\nPlease send a valid Solana address (32-44 base58 characters)."
        )
        return VERIFY_TOKEN
    addresses = load_addresses()
    found = any(line.split("|")[0].strip() == address for line in addresses)
    if found:
        await update.message.reply_text(f"✅ The address {address} is registered as a rugger.")
    else:
        await update.message.reply_text(f"❌ The address {address} is NOT registered.")
    await update.message.reply_text("What would you like to do?", reply_markup=markup)
    return CHOOSING

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
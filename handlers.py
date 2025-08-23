import re
from telegram import ReplyKeyboardMarkup
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from utils import (
    load_addresses, load_address_counts, save_address, is_valid_solana_address, address_exists
)

CHOOSING, ADD_RUG, ADD_PUMPFUN, VERIFY_TOKEN = range(4)

reply_keyboard = [
    ["Add a rug address", "Show address list", "Verify token", "Cancel"]
]
markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True)

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

async def add_rug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text
    if not is_valid_solana_address(address):
        await update.message.reply_text(
            "Invalid Solana address format.\nPlease send a valid Solana address (32-44 base58 characters)."
        )
        return ADD_RUG

    if address_exists(address):
        # Incrémente le compteur dans le JSON
        save_address(address)
        data = load_addresses()
        count = data[address]["count"]
        await update.message.reply_text(
            f"Rugger address already exists. Counter incremented.\nThis address has been reported {count} time{'s' if count > 1 else ''}."
        )
        await update.message.reply_text("What would you like to do?", reply_markup=markup)
        return CHOOSING
    else:
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
    data = load_addresses()
    count = data[address]["count"]
    await update.message.reply_text(
        f"Rug address added: {address}\nPump.fun link: {pumpfun_link}\nThis entry has been added {count} time{'s' if count > 1 else ''}."
    )
    await update.message.reply_text("Thank you! The address and link have been saved.")
    await update.message.reply_text("What would you like to do?", reply_markup=markup)
    return CHOOSING

async def choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "Add a rug address":
        await update.message.reply_text("Please send the rug address to add:")
        return ADD_RUG
    elif text == "Show address list":
        data = load_addresses()
        if data:
            msg = "*🧹 Ruggers list*\n\n"
            for idx, (rug_address, info) in enumerate(data.items(), 1):
                pumpfun_link = info.get("pumpfun_link", "")
                count = info.get("count", 1)
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

async def verify_token_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    if not is_valid_solana_address(address):
        await update.message.reply_text(
            "Invalid Solana address format.\nPlease send a valid Solana address (32-44 base58 characters)."
        )
        return VERIFY_TOKEN
    data = load_addresses()
    if address in data:
        pumpfun_link = data[address].get("pumpfun_link", "")
        msg = f"⚠️ Danger ! rugger is on list.\nPumpfun link: {pumpfun_link}" if pumpfun_link else "⚠️ Danger ! rugger is on list."
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text(f"❌ The address {address} is NOT registered.")
    await update.message.reply_text("What would you like to do?", reply_markup=markup)
    return CHOOSING

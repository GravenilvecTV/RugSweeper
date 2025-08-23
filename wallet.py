import base58
from solders.keypair import Keypair
from solana.rpc.api import Client
from telegram import ReplyKeyboardMarkup
from telegram import Update
from telegram.ext import ContextTypes
from cryptography.fernet import Fernet
import json
import os
import base64
import dotenv
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from pumpportal import create_wallet
import requests

WALLET_MENU = 10 
ENCRYPTED_KEYS_FILE = "encrypted_keys.json"

def get_balance(pubkey, rpc_url="https://api.mainnet-beta.solana.com"):
    client = Client(rpc_url)
    resp = client.get_balance(pubkey)
    # resp.value is in lamports, convert to SOL
    if hasattr(resp, "value"):
        return resp.value / 1e9  # SOL
    return None

wallet_keyboard = [
    ["Create wallet", "Deposit", "Withdraw", "Balance"]
]
wallet_markup = ReplyKeyboardMarkup(wallet_keyboard, one_time_keyboard=True, resize_keyboard=True)

async def wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_photo(
        photo="https://pbs.twimg.com/media/GzCWA2sWMAALOeZ?format=jpg&name=medium"
    )
    await update.message.reply_text(
        "Wallet options:\nPlease choose an action below.",
        reply_markup=wallet_markup
    )
    return WALLET_MENU

def save_encrypted_key_for_user(telegram_user_id: str, encrypted_privkey: str):
    """Sauvegarde la clé privée chiffrée dans un fichier JSON (format: {telegram_user_id: encrypted_privkey})."""
    if os.path.exists(ENCRYPTED_KEYS_FILE):
        with open(ENCRYPTED_KEYS_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}
    data[telegram_user_id] = encrypted_privkey
    with open(ENCRYPTED_KEYS_FILE, "w") as f:
        json.dump(data, f)

def get_sol_price():
    """Returns the current price of SOL in USD (float)."""
    try:
        resp = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd", timeout=5)
        data = resp.json()
        return float(data["solana"]["usd"])
    except Exception:
        return None

async def wallet_choice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = str(update.message.text)
    
    if text.startswith("Create wallet"):
        pubkey, privkey_base58 = create_wallet()
        print(pubkey, privkey_base58)
        salt = load_salt()
        key = derive_key("", salt)
        encrypted_privkey = encrypt_privkey(privkey_base58, key)
        telegram_user_id = str(update.effective_user.id)
        save_encrypted_key_for_user(telegram_user_id, encrypted_privkey)
        preview = privkey_base58[:4] + "..." + privkey_base58[-4:]
        await update.message.reply_text(
            f"✅ Wallet created\\!\n\n"
            f"Public address:\n`{pubkey.replace('.', '\\.')}`\n\n"
            f"Phantom private key \\(base58\\):\n||{privkey_base58.replace('.', '\\.')}||\nPreview: `{preview}`\n\n"
            f"⚠️ Save your private key\\! It gives access to your funds on Phantom\\. Never share it\\.",
            parse_mode="MarkdownV2"
        )
        await update.message.reply_text(
            "⚠️ Your private key is stored on the server, but it is encrypted and inaccessible without the system password.",
            parse_mode="Markdown"
        )
        await update.message.reply_text(
            "Wallet options:\nPlease choose an action below.",
            reply_markup=wallet_markup
        )
        return WALLET_MENU
    elif text == "Deposit":
        telegram_user_id = str(update.effective_user.id)
        # Load encrypted keys
        if os.path.exists(ENCRYPTED_KEYS_FILE):
            with open(ENCRYPTED_KEYS_FILE, "r") as f:
                encrypted_keys = json.load(f)
        else:
            encrypted_keys = {}
        salt = load_salt()
        key = derive_key("", salt)
        encrypted_privkey = encrypted_keys.get(telegram_user_id)
        if not encrypted_privkey:
            await update.message.reply_text("No key found for your Telegram account.")
        else:
            try:
                privkey_base58 = decrypt_privkey(encrypted_privkey, key)
                keypair = Keypair.from_base58_string(privkey_base58)
                pubkey = str(keypair.pubkey())
                sol_balance = get_balance(pubkey)
                sol_price = get_sol_price()
                msg = f"Deposit address:\n`{pubkey}`\n"
                if sol_balance is not None and sol_price is not None:
                    dollar_estimate = sol_balance * sol_price
                    msg += f"\nCurrent balance: {sol_balance} SOL (${dollar_estimate:.2f})"
                elif sol_balance is not None:
                    msg += f"\nCurrent balance: {sol_balance} SOL"
                else:
                    msg += "\nUnable to fetch balance."
                await update.message.reply_text(msg, parse_mode="Markdown")
            except Exception as e:
                await update.message.reply_text(f"Error decrypting your key: {e}")
        await update.message.reply_text(
            "Wallet options:\nPlease choose an action below.",
            reply_markup=wallet_markup
        )
        return WALLET_MENU
    elif text == "Withdraw":
        await update.message.reply_text("Withdraw function coming soon.")
    elif text == "Balance":
        telegram_user_id = str(update.effective_user.id)
        # Load encrypted keys
        if os.path.exists(ENCRYPTED_KEYS_FILE):
            with open(ENCRYPTED_KEYS_FILE, "r") as f:
                encrypted_keys = json.load(f)
        else:
            encrypted_keys = {}
        salt = load_salt()
        key = derive_key("", salt)
        encrypted_privkey = encrypted_keys.get(telegram_user_id)
        if not encrypted_privkey:
            await update.message.reply_text("No key found for your Telegram account.")
        else:
            try:
                privkey_base58 = decrypt_privkey(encrypted_privkey, key)
                keypair = Keypair.from_base58_string(privkey_base58)
                await update.message.reply_text(
                    f"Your public address: `{keypair.pubkey()}`",
                    parse_mode="Markdown"
                )
                sol_balance = get_balance(keypair.pubkey())
                sol_price = get_sol_price()
                if sol_balance is not None and sol_price is not None:
                    dollar_estimate = sol_balance * sol_price
                    await update.message.reply_text(
                        f"Sol balance: {sol_balance} SOL\nEstimated value: ${dollar_estimate:.2f}",
                        parse_mode="Markdown"
                    )
                elif sol_balance is not None:
                    await update.message.reply_text(
                        f"Sol balance: {sol_balance} SOL",
                        parse_mode="Markdown"
                    )
                else:
                    await update.message.reply_text("Unable to fetch balance.", parse_mode="Markdown")
            except Exception as e:
                await update.message.reply_text(f"Error decrypting your key: {e}")
        await update.message.reply_text(
            "Wallet options:\nPlease choose an action below.",
            reply_markup=wallet_markup
        )
        return WALLET_MENU
    else:
        await update.message.reply_text("Invalid option.")
    # Show wallet menu again (except if waiting for public key)
    if text != "Balance":
        await update.message.reply_text(
            "Wallet options:\nPlease choose an action below.",
            reply_markup=wallet_markup
        )
        return WALLET_MENU

 
def generate_encryption_key():
    """Génère une clé de chiffrement Fernet (à stocker de façon sécurisée)."""
    return Fernet.generate_key()

def load_salt():
    """Charge le salt depuis le fichier .env."""
    dotenv.load_dotenv()
    salt = os.getenv("FERNET_SALT")
    if not salt:
        raise ValueError("Le salt FERNET_SALT n'est pas défini dans le .env")
    return base64.b64decode(salt)

def derive_key(password: str, salt: bytes) -> bytes:
    """Dérive une clé Fernet à partir d'un mot de passe et d'un salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
    return key

def encrypt_privkey(privkey: str, encryption_key: bytes) -> str:
    """Chiffre la clé privée avec Fernet."""
    f = Fernet(encryption_key)
    token = f.encrypt(privkey.encode())
    return token.decode()

def decrypt_privkey(token: str, encryption_key: bytes) -> str:
    """Déchiffre la clé privée avec Fernet."""
    f = Fernet(encryption_key)
    privkey = f.decrypt(token.encode())
    return privkey.decode()

def save_encrypted_key(pubkey: str, encrypted_privkey: str):
    """Sauvegarde la clé privée chiffrée dans un fichier JSON (format: {pubkey: encrypted_privkey})."""
    if os.path.exists(ENCRYPTED_KEYS_FILE):
        with open(ENCRYPTED_KEYS_FILE, "r") as f:
            data = json.load(f)
    else:
        data = {}
    data[pubkey] = encrypted_privkey
    with open(ENCRYPTED_KEYS_FILE, "w") as f:
        json.dump(data, f)








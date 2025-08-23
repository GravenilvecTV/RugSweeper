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

WALLET_MENU = 10 
ENCRYPTED_KEYS_FILE = "encrypted_keys.json"

def get_balance(pubkey, rpc_url="https://api.mainnet-beta.solana.com"):
    client = Client(rpc_url)
    resp = client.get_balance(pubkey)
    if resp.get("result"):
        return resp["result"]["value"] / 1e9  # SOL
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
            f"Public address :\n`{pubkey.replace('.', '\\.')}`\n\n"
            f"Phantom private key \\(base58\\) :\n||{privkey_base58.replace('.', '\\.')}||\n\n"
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
        await update.message.reply_text("Deposit function coming soon.")
    elif text == "Withdraw":
        await update.message.reply_text("Withdraw function coming soon.")
    elif text == "Balance":
        telegram_user_id = str(update.effective_user.id)
        # Charger les clés chiffrées
        if os.path.exists(ENCRYPTED_KEYS_FILE):
            with open(ENCRYPTED_KEYS_FILE, "r") as f:
                encrypted_keys = json.load(f)
        else:
            encrypted_keys = {}
        salt = load_salt()
        key = derive_key("", salt)
        encrypted_privkey = encrypted_keys.get(telegram_user_id)
        if not encrypted_privkey:
            await update.message.reply_text("Aucune clé enregistrée pour votre compte Telegram.")
        else:
            try:
                privkey_base58 = decrypt_privkey(encrypted_privkey, key)
                seed_bytes = base58.b58decode(privkey_base58)
                kp = Keypair.from_seed(seed_bytes)
                pubkey = str(kp.pubkey())
                await update.message.reply_text(
                    f"Votre clé privée Phantom \\(base58\\) : `{privkey_base58}`\nLongueur : {len(privkey_base58)} caractères",
                    parse_mode="Markdown"
                )
                await update.message.reply_text(
                    f"Votre adresse publique : `{pubkey}`",
                    parse_mode="Markdown"
                )
            except Exception as e:
                await update.message.reply_text(f"Erreur lors du déchiffrement de votre clé : {e}")
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

async def wallet_balance_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pubkey = update.message.text.strip()
    balance = get_balance(pubkey)
    if balance is not None:
        await update.message.reply_text(f"Balance for `{pubkey}`: {balance} SOL", parse_mode="Markdown")
    else:
        await update.message.reply_text("Unable to fetch balance. Please check your public key.")
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








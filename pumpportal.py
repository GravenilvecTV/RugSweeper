import asyncio
import websockets
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def get_all_chat_ids():
    """Retourne la liste de tous les chat_id ayant discuté avec le bot, sauf le channel."""
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
    url = f"https://api.telegram.org/bot{telegram_token}/getUpdates"
    try:
        response = requests.get(url)
        data = response.json()
        chat_ids = set()
        if "result" in data:
            for update in data["result"]:
                message = update.get("message")
                if message and "chat" in message and "id" in message["chat"]:
                    chat_id = str(message["chat"]["id"])
                    # Exclure le channel
                    if chat_id != channel_id:
                        chat_ids.add(chat_id)
        return list(chat_ids)
    except Exception as e:
        print(f"Erreur lors de la récupération des chat_id : {e}")
        return []

def send_telegram_message(address: str, link: str):
    """
    Envoie un message stylisé sur Telegram à tous les chat_id connus sauf le channel.
    """
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_channel_id = os.getenv("TELEGRAM_CHANNEL_ID")
    # Ne rien envoyer si c'est le channel
    if telegram_channel_id == "-1002569761588":
        print("Message non envoyé : channel détecté.")
        return

    message = (
        "🚨 *New token from a rugger* 🚨\n\n"
        f"Address: `{address}`\n"
        f"[View on PumpPortal]({link})"
    )

    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload = {
        "chat_id": telegram_channel_id,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"Erreur lors de l'envoi Telegram à {telegram_channel_id}: {response.text}")
    except Exception as e:
        print(f"Exception lors de l'envoi Telegram à {telegram_channel_id}: {e}")

def load_addresses():
    path = os.path.join(os.path.dirname(__file__), "adresses.json")
    with open(path, "r") as f:
        return json.load(f)

addresses = load_addresses()

async def fetch_new_tokens():
    print("Start websocket for new tokens by specific creator...")
    uri = "wss://pumpportal.fun/api/data"
    try:
        async with websockets.connect(uri) as websocket:
            payload = {
                "method": "subscribeNewToken",
            }
            await websocket.send(json.dumps(payload))

            async for message in websocket:
                try:
                    data = json.loads(message)
                    if (
                        isinstance(data, dict)
                        and data.get("txType") == "create"
                        and data.get("traderPublicKey") in addresses
                    ):
                        msg = f"{data.get('traderPublicKey')}"
                        print(msg)
                        send_telegram_message(
                            data.get('traderPublicKey'),
                            f"https://pumpportal.fun/token/{data.get('tokenAddress')}"
                        )
                except Exception as e:
                    print(f"Erreur parsing event : {e}")
    except Exception as e:
        print(f"Erreur WebSocket pumpportal.fun : {e}")
        await asyncio.sleep(10)
        await fetch_new_tokens()

def create_wallet():
    """
    Crée un nouveau wallet via l'API PumpPortal et retourne (pubkey, privkey_base58).
    """
    try:
        response = requests.get(url="https://pumpportal.fun/api/create-wallet")
        data = response.json()
        pubkey = data.get("walletPublicKey")
        privkey_base58 = data.get("privateKey")
        return pubkey, privkey_base58
    except Exception as e:
        print(f"Erreur lors de la création du wallet PumpPortal : {e}")
        return None, None

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(fetch_new_tokens())
    except KeyboardInterrupt:
        print("Arrêt manuel du bot.")
    finally:
        loop.close()
    loop = asyncio.get_event_loop()
    try:
        tasks = [
            fetch_new_tokens(),
            watch_new_tokens_file()
        ]
        loop.run_until_complete(asyncio.gather(*tasks))
    except KeyboardInterrupt:
        print("Arrêt manuel du bot.")
    finally:
        loop.close()




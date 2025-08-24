import asyncio
import websockets
import json
import os
import requests
from dotenv import load_dotenv
from telegram import InlineKeyboardMarkup, InlineKeyboardButton 
from transactions import buy_token
import wallet
from solders.keypair import Keypair

load_dotenv()

def send_telegram_message(
    token_name: str,
    symbol: str,
    rugger_address: str,
    contract_address: str,
    market_cap_sol: float,
    initial_buy: float,
    sol_amount: float,
    signature: str
):
    """
    Sends a detailed message to Telegram with all important token info.
    """
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    telegram_channel_id = os.getenv("TELEGRAM_CHANNEL_ID")

    message = (
        "🚨 *Rug Alert!* 🚨\n\n"
        "🆕 *New Token Created by Registered Rugger*\n\n"
        f"🔹 *Name*: `{token_name}`\n"
        f"🔹 *Symbol*: `{symbol}`\n"
        f"🔹 *Rugger Address*: `{rugger_address}`\n"
        f"🔹 *Contract Address*: `{contract_address}`\n\n"
        "💰 *Token Details*\n"
        f"• Market Cap: `{market_cap_sol:.2f} SOL`\n"
        f"• Initial Buy: `{initial_buy:.2f}`\n"
        f"• SOL Amount: `{sol_amount:.6f}`\n"
        f"• Signature: `{signature}`\n\n"
        f"🔗 [View on Pump.fun](https://pump.fun/coin/{contract_address})"
    )

    # Add multiple buy buttons
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Buy 0.01 SOL", callback_data=f"sweep:{contract_address}:0.01"),
            InlineKeyboardButton("Buy 0.1 SOL", callback_data=f"sweep:{contract_address}:0.1"),
            InlineKeyboardButton("Buy 0.5 SOL", callback_data=f"sweep:{contract_address}:0.5"),
            InlineKeyboardButton("Buy 1 SOL", callback_data=f"sweep:{contract_address}:1"),
        ]
    ])

    url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
    payload = {
        "chat_id": telegram_channel_id,
        "text": message,
        "parse_mode": "Markdown",
        "reply_markup": keyboard.to_json()
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print(f"Erreur lors de l'envoi Telegram à {telegram_channel_id}: {response.text}")
    except Exception as e:
        print(f"Exception lors de l'envoi Telegram à {telegram_channel_id}: {e}")

def load_addresses():
    path = os.path.join(os.path.dirname(__file__), "data", "adresses.json")
    with open(path, "r") as f:
        return json.load(f)

addresses = load_addresses()

async def fetch_new_tokens():
    print("Start websocket for new tokens by specific creator...")
    # Test message with fake data
    send_telegram_message(
        "TestToken",
        "TEST",
        "FakeRuggerAddress1234567890",
        "rWqaZ3KaJaiKtVEQo4nuEsxKKr2tHtoeYMf1vVveDjS",
        42.0,
        1.23,
        0.012345,
        "FakeSignature1234567890"
    )
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
                        send_telegram_message(
                            data.get("name", ""),
                            data.get("symbol", ""),
                            data.get("traderPublicKey", ""),
                            data.get("mint", ""),
                            float(data.get("marketCapSol", 0)),
                            float(data.get("initialBuy", 0)),
                            float(data.get("solAmount", 0)),
                            data.get("signature", "")
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

async def sweep_callback_handler(update, context):
    query = update.callback_query
    await query.answer()
    try:
        _, contract_address, amount = query.data.split(":")
        user_id = str(update.effective_user.id)
        print(f"[DEBUG] Sweep request: user={user_id}, contract={contract_address}, amount={amount}")

        # Retrieve privkey_base58 and check validity before using Keypair
        pubkey, privkey_base58 = wallet.get_wallet_for_user(user_id)
        if not privkey_base58:
            await context.application.bot.send_message(
                chat_id=update.effective_user.id,
                text="No wallet found for your account.",
                parse_mode="Markdown"
            )
            return

        try:
            keypair = Keypair.from_base58_string(privkey_base58)
        except Exception as e:
            await context.application.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"Error loading your wallet: {e}",
                parse_mode="Markdown"
            )
            return

        # Validate contract_address (should be base58, no '-')
        try:
            # Only allow valid base58 addresses (no '-')
            if '-' in contract_address:
                raise ValueError("Invalid contract address format (contains '-').")
            pubkey = str(keypair.pubkey())
            success, result_msg = buy_token(pubkey, contract_address, keypair, float(amount))
            if success:
                msg = (
                    f"🧹 Sweep request received!\n"
                    f"User `{user_id}` will buy `{amount} SOL` of token:\n"
                    f"`{contract_address}`\n\n"
                    f"{result_msg}"
                )
            else:
                msg = (
                    f"❌ Sweep request failed for user `{user_id}` on token `{contract_address}`.\n"
                    f"Reason: {result_msg}"
                )
            await context.application.bot.send_message(
                chat_id=update.effective_user.id,
                text=msg,
                parse_mode="Markdown"
            )
        except Exception as e:
            await context.application.bot.send_message(
                chat_id=update.effective_user.id,
                text=f"Invalid contract address `{contract_address}`: {e}",
                parse_mode="Markdown"
            )
    except Exception as e:
        print(f"[DEBUG] Error in sweep_callback_handler: {e}")
        await context.application.bot.send_message(
            chat_id=update.effective_user.id,
            text=f"Error: {e}"
        )
 
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
        ]
        loop.run_until_complete(asyncio.gather(*tasks))
    except KeyboardInterrupt:
        print("Arrêt manuel du bot.")
    finally:
        loop.close()

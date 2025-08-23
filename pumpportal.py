import asyncio
import websockets
import json

async def fetch_new_tokens():
    print("Start websocket for new tokens by specific creator...")
    uri = "wss://pumpportal.fun/api/data"
    creator_key = "6pqcYg6r684jEyeNdsHr28RziuohNSzfkPDrVccpWU5H"
    try:
        async with websockets.connect(uri) as websocket:
            # S'abonne uniquement aux nouveaux tokens créés par ce créateur
            payload = {
                "method": "subscribeNewToken", 
            }
            await websocket.send(json.dumps(payload))

            async for message in websocket:
                try:
                    data = json.loads(message) 
                    # Affiche uniquement si le traderPublicKey correspond à creator_key
                    if (
                        isinstance(data, dict)
                        and data.get("txType") == "create" 
                    ):
                        print(f"Nouveau token créé par {creator_key} : {data}")
                except Exception as e:
                    print(f"Erreur parsing event : {e}")
    except Exception as e:
        print(f"Erreur WebSocket pumpportal.fun : {e}")
        await asyncio.sleep(10)
        await fetch_new_tokens()
        print(f"Erreur WebSocket pumpportal.fun : {e}")
        await asyncio.sleep(10)
        await fetch_new_tokens()

def start_token_subscription():
    """Démarre la souscription en tâche de fond sans bloquer l'event loop."""
    asyncio.create_task(fetch_new_tokens())

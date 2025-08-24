import requests
from dotenv import load_dotenv
load_dotenv()

from solders.transaction import VersionedTransaction
from solders.keypair import Keypair
from solders.commitment_config import CommitmentLevel
from solders.rpc.requests import SendVersionedTransaction
from solders.rpc.config import RpcSendTransactionConfig 
from solana.rpc.async_api import AsyncClient
import base64

rpc_url = "https://api.mainnet-beta.solana.com"

def buy_token(pubKey, mint, keypair, amount, slippage=10, priorityFee=0.001, pool="auto"):
    """
    Achète un token via PumpPortal
    
    Args:
        mint (str): L'adresse du contrat du token à acheter
        amount (int): Le montant à acheter (en SOL ou en tokens selon denominatedInSol)
        denominatedInSol (str): "true" si amount est en SOL, "false" si en nombre de tokens
        slippage (int): Le pourcentage de slippage autorisé
        priorityFee (float): Les frais de priorité à utiliser
        pool (str): L'exchange sur lequel trader ("pump", "raydium", "pump-amm", etc.)
    
    Returns:
        str: L'URL de la transaction sur Solscan si succès, None si échec
    """ 
 
    # Préparer les données pour l'API PumpPortal
    trade_data = {
        "publicKey": pubKey,
        "action": "buy",
        "mint": mint,
        "amount": str(amount),
        "denominatedInSol": True,
        "slippage": slippage,
        "priorityFee": priorityFee,
        "pool": pool
    }

    print(trade_data)
    
    # Effectuer la requête à PumpPortal
    response = requests.post(url="https://pumpportal.fun/api/trade-local", data=trade_data)
    
    # Vérifier si la réponse est valide avant de traiter
    if response.status_code != 200:
        print(f"Erreur HTTP: {response.status_code}")
        print(f"Contenu de l'erreur: {response.text}")
        return None

    # Vérifier si la réponse contient des données de transaction
    if len(response.content) == 0:
        print("Erreur: La réponse est vide")
        return None

    try:
        # Correction: détecte si la clé est hexadécimale (longueur 128, uniquement chiffres/lettres a-f)
        if len(keypair) == 128 and all(c in "0123456789abcdefABCDEF" for c in keypair):
            keypair = Keypair.from_bytes(bytes.fromhex(keypair))
        else:
            keypair = Keypair.from_base58_string(keypair)
        tx = VersionedTransaction(VersionedTransaction.from_bytes(response.content).message, [keypair])
    except Exception as e:
        print(f"Erreur lors de la création de la transaction: {e}")
        print(f"Taille du contenu: {len(response.content)} bytes")
        # Essayer de décoder comme JSON pour voir s'il y a un message d'erreur
        try:
            json_response = response.json()
            print(f"Réponse JSON: {json_response}")
        except:
            print("La réponse n'est pas un JSON valide")
        return None

    commitment = CommitmentLevel.Confirmed
    config = RpcSendTransactionConfig(preflight_commitment=commitment)
    txPayload = SendVersionedTransaction(tx, config)

    # Envoyer la transaction signée au réseau Solana
    response = requests.post(
        url=rpc_url,
        headers={"Content-Type": "application/json"},
        data=SendVersionedTransaction(tx, config).to_json()
    )
    
    try:
        txSignature = response.json()['result']
        transaction_url = f'https://solscan.io/tx/{txSignature}'
        print(f'Transaction: {transaction_url}')
        return transaction_url
    except Exception as e:
        # Gestion explicite de AccountNotFound
        try:
            error_json = response.json()
            if (
                "error" in error_json
                and error_json["error"].get("data", {}).get("err") == "AccountNotFound"
            ):
                msg = "Erreur : AccountNotFound. L'un des comptes nécessaires n'existe pas ou n'a jamais reçu de crédit."
                print(msg)
                return msg
        except Exception:
            pass
        print(f"Erreur lors de la récupération de la signature de transaction: {e} ")
        print(f"Réponse: {response.text}")
        return None

async def sell_token(pubKey, mint, keypair, slippage=20, priorityFee=0.001, pool="auto"):
    """
    Vend tout le solde du token via PumpPortal

    Args:
        pubKey (str): Adresse publique du wallet.
        mint (str): Adresse du token SPL à vendre.
        keypair (str): Clé privée du wallet (hex ou base58).
        slippage (int): Pourcentage de slippage autorisé.
        priorityFee (float): Frais de priorité à utiliser.
        pool (str): Exchange ("pump", "raydium", etc.)

    Returns:
        str: L'URL de la transaction sur Solscan si succès, None si échec
    """
    trade_data = {
        "publicKey": pubKey,
        "action": "sell",
        "mint": mint,
        "amount": "100%",  
        "denominatedInSol": False,
        "slippage": slippage,
        "priorityFee": priorityFee,
        "pool": pool
    }

    response = requests.post(url="https://pumpportal.fun/api/trade-local", data=trade_data)

    if response.status_code != 200:
        print(f"Erreur HTTP: {response.status_code}")
        print(f"Contenu de l'erreur: {response.text}")
        return None

    if len(response.content) == 0:
        print("Erreur: La réponse est vide")
        return None

    try:
        if len(keypair) == 128 and all(c in "0123456789abcdefABCDEF" for c in keypair):
            keypair = Keypair.from_bytes(bytes.fromhex(keypair))
        else:
            keypair = Keypair.from_base58_string(keypair)
        tx = VersionedTransaction(VersionedTransaction.from_bytes(response.content).message, [keypair])
    except Exception as e:
        print(f"Erreur lors de la création de la transaction: {e}")
        print(f"Taille du contenu: {len(response.content)} bytes")
        try:
            json_response = response.json()
            print(f"Réponse JSON: {json_response}")
        except:
            print("La réponse n'est pas un JSON valide")
        return None

    commitment = CommitmentLevel.Confirmed
    config = RpcSendTransactionConfig(preflight_commitment=commitment)
    txPayload = SendVersionedTransaction(tx, config)

    response = requests.post(
        url=rpc_url,
        headers={"Content-Type": "application/json"},
        data=SendVersionedTransaction(tx, config).to_json()
    )

    try:
        txSignature = response.json()['result']
        transaction_url = f'https://solscan.io/tx/{txSignature}'
        print(f'Transaction: {transaction_url}')
        return transaction_url
    except Exception as e:
        try:
            error_json = response.json()
            if (
                "error" in error_json
                and error_json["error"].get("data", {}).get("err") == "AccountNotFound"
            ):
                msg = "Erreur : AccountNotFound. L'un des comptes nécessaires n'existe pas ou n'a jamais reçu de crédit."
                print(msg)
                return msg
        except Exception:
            pass
        print(f"Erreur lors de la récupération de la signature de transaction: {e}")
        print(f"Réponse: {response.text}")
        return None
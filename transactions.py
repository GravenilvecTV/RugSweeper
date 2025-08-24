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
        pubKey (str): L'adresse publique du wallet
        mint (str): L'adresse du contrat du token à acheter
        keypair (Keypair or str): Clé privée du wallet (Keypair object ou base58 string)
        amount (float): Le montant à acheter (en SOL)
        slippage (int): Le pourcentage de slippage autorisé
        priorityFee (float): Les frais de priorité à utiliser
        pool (str): L'exchange sur lequel trader ("pump", "raydium", "pump-amm", etc.)
    
    Returns:
        tuple: (success: bool, message: str)
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

    response = requests.post(url="https://pumpportal.fun/api/trade-local", data=trade_data)

    if response.status_code != 200:
        print(f"Erreur HTTP: {response.status_code}")
        print(f"Contenu de l'erreur: {response.text}")
        return False, f"Erreur HTTP: {response.status_code}"

    if len(response.content) == 0:
        print("Erreur: La réponse est vide")
        return False, "Erreur: La réponse est vide"

    # keypair peut être un objet Keypair ou une string
    if isinstance(keypair, Keypair):
        kp = keypair
    else:
        kp = Keypair.from_base58_string(keypair)

    try:
        tx = VersionedTransaction(VersionedTransaction.from_bytes(response.content).message, [kp])
    except Exception as e:
        print(f"Erreur lors de la création de la transaction: {e}")
        return False, f"Erreur lors de la création de la transaction: {e}"

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
        return True, transaction_url
    except Exception as e:
        try:
            error_json = response.json()
            if (
                "error" in error_json
                and error_json["error"].get("data", {}).get("err") == "AccountNotFound"
            ):
                msg = "Erreur : AccountNotFound. L'un des comptes nécessaires n'existe pas ou n'a jamais reçu de crédit."
                print(msg)
                return False, msg
        except Exception:
            pass
        print(f"Erreur lors de la récupération de la signature de transaction: {e} ")
        print(f"Réponse: {response.text}")
        return False, f"Erreur lors de la récupération de la signature de transaction: {e}"
 
 
from solders.keypair import Keypair
from solana.rpc.api import Client

def create_wallet():
    kp = Keypair()
    pubkey = str(kp.pubkey())
    privkey = kp.secret().hex()
    return pubkey, privkey

def get_balance(pubkey, rpc_url="https://api.mainnet-beta.solana.com"):
    client = Client(rpc_url)
    resp = client.get_balance(pubkey)
    if resp.get("result"):
        return resp["result"]["value"] / 1e9  # SOL
    return None

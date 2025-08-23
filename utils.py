import os
import re
import json

ADRESSES_FILE = "adresses.json"

def load_addresses():
    if not os.path.exists(ADRESSES_FILE):
        return {}
    with open(ADRESSES_FILE, "r") as f:
        return json.load(f)

def load_address_counts():
    data = load_addresses()
    # Retourne un dict : (address, pumpfun_link) -> count
    return {(addr, info.get("pumpfun_link", "")): info.get("count", 1) for addr, info in data.items()}

def save_address(address, pumpfun_link=""):
    data = load_addresses()
    if address in data:
        # Incrémente le compteur si déjà présent
        data[address]["count"] = data[address].get("count", 1) + 1
        # Met à jour le lien pumpfun si fourni et non vide
        if pumpfun_link:
            data[address]["pumpfun_link"] = pumpfun_link
    else:
        data[address] = {"pumpfun_link": pumpfun_link, "count": 1}
    with open(ADRESSES_FILE, "w") as f:
        json.dump(data, f, indent=2)

def is_valid_solana_address(address):
    pattern = r"^[1-9A-HJ-NP-Za-km-z]{32,44}$"
    return re.match(pattern, address) is not None

def address_exists(address):
    data = load_addresses()
    return address in data

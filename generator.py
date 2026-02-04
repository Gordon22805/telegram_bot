import secrets
import string

def generate_accounts(region: str, quantity: int) -> str:
    """
    Generate 'quantity' of fake accounts for the given region.
    Returns single string with accounts separated by newlines.
    Format (per account, multi-line):
    Geo: REGION
    Shop: <word>_<word>_<digits>
    Password: <password>
    Status: Active (<n> orders)
    """
    adjectives = [
        "Sharp", "Prime", "Apex", "Nova", "Swift", "Urban", "Cloud",
        "Bright", "Stellar", "Vivid", "Elite", "Rapid", "Luxe", "Core",
        "Matrix", "Vector", "Nimbus", "Vertex", "Fusion", "Pulse"
    ]
    nouns = [
        "Pro", "Shop", "Mart", "Hub", "Store", "Market", "Plaza",
        "Point", "Depot", "Trade", "Lane", "Cart", "Outlet", "Supply",
        "Retail", "Bazaar", "Shelf", "Corner", "Space", "Zone"
    ]

    blocks = []
    for _ in range(quantity):
        shop = f"{secrets.choice(adjectives)}_{secrets.choice(nouns)}_{secrets.randbelow(900000) + 100000}"
        pwd = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        orders = secrets.randbelow(25) + 1

        blocks.append(
            f"Geo: {region}\n"
            f"Shop: {shop}\n"
            f"Password: {pwd}\n"
            f"Status: Active ({orders} orders)"
        )

    return "\n\n".join(blocks)

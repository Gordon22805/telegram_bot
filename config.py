import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# Prices per region
PRICES = {
    "USA": 9.99,
    "TURKEY": 11.99,
    "NETHERLANDS": 15.99,
}

# Limits
MAX_QUANTITY = 40
COOLDOWN_SECONDS = 10  # spamguard

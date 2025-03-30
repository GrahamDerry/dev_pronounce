import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if TELEGRAM_BOT_TOKEN:
    print("Bot token loaded successfully!")
else:
    print("Error: Bot token not found.")

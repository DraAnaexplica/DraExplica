import os
from dotenv import load_dotenv

load_dotenv()
print("TOKEN:", os.getenv("WHATSAPP_TOKEN"))

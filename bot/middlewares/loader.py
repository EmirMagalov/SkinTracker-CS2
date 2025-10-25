import os
from dotenv import load_dotenv
import json
from redis.asyncio import Redis
load_dotenv()
redis = Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))  # .../skinsprice/skinsapp
BASE_DIR = os.path.dirname(os.path.dirname(CURRENT_DIR))  # поднимаемся на 2 уровня → CSSkins
SAVE_PATH = os.path.join(BASE_DIR, os.getenv("SAVE_PATH"))  # CSSkins/bot
with open(f"{SAVE_PATH}/all_skins_ru.json", encoding="utf-8") as f:
    skins_ru = json.load(f)

with open(f"{SAVE_PATH}/all_skins_en.json", encoding="utf-8") as f:
    skins_en = json.load(f)
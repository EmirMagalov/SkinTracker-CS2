import os
from dotenv import load_dotenv
import json
from redis.asyncio import Redis
load_dotenv()
REDIS_URL = os.getenv("CELERY_BROKER_URL")  # должно быть типа redis://redis:6379/0
redis = Redis.from_url(REDIS_URL)


with open("all_skins_ru.json", encoding="utf-8") as f:
    skins_ru = json.load(f)

with open("all_skins_en.json", encoding="utf-8") as f:
    skins_en = json.load(f)
import os
from dotenv import load_dotenv
import json
from redis.asyncio import Redis
load_dotenv()
redis = Redis(host=os.getenv("REDIS_HOST"), port=6379, db=0)


with open("all_skins_ru.json", encoding="utf-8") as f:
    skins_ru = json.load(f)

with open("all_skins_en.json", encoding="utf-8") as f:
    skins_en = json.load(f)
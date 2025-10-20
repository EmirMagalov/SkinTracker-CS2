import json
from redis.asyncio import Redis
redis = Redis(host="localhost", port=6379, db=0)


with open("all_skins_ru.json", encoding="utf-8") as f:
    skins_ru = json.load(f)

with open("all_skins_en.json", encoding="utf-8") as f:
    skins_en = json.load(f)
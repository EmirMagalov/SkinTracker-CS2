import os
import json
import aiohttp
import urllib.parse
from middlewares.loader import redis
from dotenv import load_dotenv
load_dotenv()
API =os.getenv('URL')

CACHE_TTL = 180  # 3 минут

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://steamcommunity.com/market/",
    "X-Requested-With": "XMLHttpRequest",
}
async def get_skin_price(skin_name, condition=None):
    if condition:
        full_name = f"{skin_name} ({condition})"
    else:
        full_name = f"{skin_name}"

    encoded_name = urllib.parse.quote(full_name)
    print(encoded_name)

    key = f"steam_price:{encoded_name}"
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    url = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=1&market_hash_name={encoded_name}&format=json"
    async with aiohttp.ClientSession(headers=HEADERS) as session:
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()

                await redis.setex(key, CACHE_TTL, json.dumps(data))
                return data
            else:

                return None


async def create_user(user_id, user_first_name):
    async with aiohttp.ClientSession() as session:
        async with session.post(API + 'users/',
                                json={'user_id': user_id, 'user_first_name': user_first_name}) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None


async def add_user_skin(user_id, skin_id, skin_name, last_price, condition):
    async with aiohttp.ClientSession() as session:
        async with session.post(API + 'user-skins/add_user_skin/',
                                json={'user_id': user_id, 'skin_id': skin_id, 'skin_name': skin_name,
                                      'last_price': last_price,
                                      "condition": condition}) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None


async def get_user_skin(user_id, skin_id, condition):
    params = {'user_id': str(user_id), 'skin_id': skin_id}
    if condition is not None:
        params['condition'] = str(condition)

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API}user-skins/get_user_skin/", params=params) as response:
            if response.status == 200:
                return await response.json()
            return None


async def get_user_skins(user_id):
    async with aiohttp.ClientSession() as session:
        async with session.get(API + 'user-skins/get_user_skins/',
                               params={'user_id': user_id}
                               ) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None


async def delete_user_skin(user_id, skin_id, condition):
    async with aiohttp.ClientSession() as session:
        async with session.delete(API + 'user-skins/delete_user_skin/',
                                  params={'user_id': user_id, 'skin_id': skin_id, "condition": condition}
                                  ) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None


async def user_skin_trigger(user_id, skin_id, condition, threshold_value,last_price):
    async with aiohttp.ClientSession() as session:
        async with session.post(API + 'user-skins/user_skin_trigger/',
                                json={'user_id': user_id, 'skin_id': skin_id,
                                      'threshold_value': threshold_value,
                                      "condition": condition,'last_price':last_price}) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None


async def get_users():
    async with aiohttp.ClientSession() as session:
        async with session.get(API + 'users'
                               ) as response:
            if response.status == 200:
                return await response.json()
            else:
                return None

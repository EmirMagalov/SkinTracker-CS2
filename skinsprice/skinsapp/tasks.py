import os
import json
import urllib.parse
import asyncio
import aiohttp
from aiogram import Bot
from celery import shared_task
from dotenv import load_dotenv
from asgiref.sync import sync_to_async
from redis.asyncio import Redis
from .models import Skin, UserSkin

load_dotenv()

BOT_TOKEN = os.getenv("TOKEN")
CACHE_TTL = 300  # 5 минут
REDIS_HOST = os.getenv("REDIS_HOST")
REDIS_PORT = 6379
REDIS_DB = 0
MAX_CONCURRENT_REQUESTS = 5  # ограничение параллельных запросов


async def get_skin_price(skin_name, condition=None, session=None):
    """Получаем цену скина из Steam с кэшированием в Redis."""
    if condition:
        full_name = f"{skin_name} ({condition})"
    else:
        full_name = skin_name

    encoded_name = urllib.parse.quote(full_name)
    cache_key = f"steam_price:{encoded_name}"

    redis = Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    try:
        cached = await redis.get(cache_key)
        if cached:
            return json.loads(cached)

        url = f"https://steamcommunity.com/market/priceoverview/?appid=730&currency=1&market_hash_name={encoded_name}&format=json"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                await redis.setex(cache_key, CACHE_TTL, json.dumps(data))
                return data
            return None
    finally:
        await redis.close()


async def process_skins():
    """Асинхронная проверка цен и уведомление пользователей."""
    skins = await sync_to_async(list)(Skin.objects.all())
    if not skins:
        print("[INFO] Нет скинов в базе")
        return

    bot = Bot(token=BOT_TOKEN)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async with aiohttp.ClientSession() as session:

        async def fetch_and_notify(skin):
            async with semaphore:
                data = await get_skin_price(skin.skin_name, skin.condition, session=session)
                if not data:
                    print(f"[WARN] Нет данных для {skin.skin_name} ({skin.condition})")
                    return

                user_skins = await sync_to_async(list)(UserSkin.objects.filter(skin=skin))
                if not user_skins:
                    print(f"[INFO] Нет подписчиков на {skin.skin_name}")
                    return

                for us in user_skins:
                    try:
                        last_price = await sync_to_async(lambda: float(us.last_notified_price or 0))()
                        lowest_price_str = data.get("lowest_price") or "0"
                        parts = lowest_price_str.split(".")
                        if len(parts) > 2:
                            lowest_price_str = "".join(parts[:-1]) + "." + parts[-1]

                        try:
                            lowest_price = float(lowest_price_str)
                        except ValueError:
                            print(f"[ERROR] Некорректный формат цены: {lowest_price_str}")
                            return

                    except Exception as e:
                        print(f"[ERROR] Не удалось получить цену для {skin.skin_name}: {e}")
                        continue
                    if last_price == 0:
                        await sync_to_async(lambda: setattr(us, "last_notified_price", lowest_price) or us.save())()
                        continue  # не отправляем уведомление
                    if us.threshold_value != 0  and abs(lowest_price - last_price) >= us.threshold_value:

                        condition = f"({skin.condition})" if skin.condition else ''
                        text = f"💰 Цена на <b>{skin.skin_name} {condition}</b> изменилась!\n\nТекущая цена: {lowest_price}$"
                        try:
                            user_id = await sync_to_async(lambda: us.user.user_id)()
                            await bot.send_message(user_id, text, parse_mode="HTML")
                            print(f"[INFO] Отправлено пользователю {user_id}")
                        except Exception as e:
                            print(f"[ERROR] Не удалось отправить пользователю {user_id}: {e}")
                            continue
                        skin.last_price = lowest_price
                        await sync_to_async(skin.save)()

                        await sync_to_async(lambda: setattr(us, "last_notified_price", lowest_price) or us.save())()

        # Параллельно запускаем все задачи
        await asyncio.gather(*(fetch_and_notify(skin) for skin in skins))

    await bot.session.close()


@shared_task
def check_all_prices():
    """Celery задача для проверки всех цен с использованием отдельного event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(process_skins())
    finally:
        loop.close()

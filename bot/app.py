import os
import asyncio
from aiogram import Bot, Dispatcher, types
from dotenv import load_dotenv
from handlers.user_private import user_private_router
from aiogram.fsm.storage.redis import RedisStorage
from kbds.commands import private
from handlers.admin import admin_private
from middlewares.loader import redis
load_dotenv()
bot = Bot(token=os.getenv('TOKEN'))
storage = RedisStorage(redis=redis)
dp = Dispatcher(storage=storage)
dp.include_router(admin_private)
dp.include_router(user_private_router)



def start_bot():
    print("Bot_Online")

async def main():
    start_bot()
    await bot.set_my_commands(commands=private)
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped")
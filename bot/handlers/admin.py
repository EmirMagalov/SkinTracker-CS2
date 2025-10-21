from aiogram import Router, F, types
from aiogram.filters import Command
from middlewares.database_data import get_users

admin_private = Router()


@admin_private.message(Command('users'))
async def users(message: types.Message):
    user_id = message.from_user.id

    users = await get_users()
    await message.answer(f"Пользователей:{len(users)}")

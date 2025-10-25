import json
import re
import urllib.parse
from typing import Union
from decimal import Decimal

from aiogram import Router, F, types
from aiogram.filters import or_f
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from aiogram.types import InputMediaPhoto

from filters.search_skins import get_skin_id, get_skin, lang, get_exact_name
from middlewares.database_data import get_skin_price, create_user, add_user_skin, get_user_skin, get_user_skins, \
    delete_user_skin, user_skin_trigger
from kbds.inline import condition_kbds, create_inline_kb
from middlewares.loader import redis

user_private_router = Router()

ttl = 170

FALLBACK_IMAGE = "./public/ak-47-rifle-silhouette-png-05252024-c6e00iov49u7tpcf.png"  # твоя заглушка (можно заменить)


async def build_skin_message(skin, stattrak=False, condition=None):
    is_stattrakawait = await get_exact_name(f"StatTrak™ {skin['req_name']} (Field-Tested)")
    if condition == None:
        condition = "Collections"

    rarity = f'\n\n{skin["rarity"]}' if skin["rarity"].lower() != 'none' else ''

    min_float = f"\n\nМин. степень износа - {skin['min_float']}\n" if str(skin['min_float']).lower() != 'none' else ''
    max_float = f"Макс. степень износа - {skin['max_float']}\n" if str(skin['max_float']).lower() != 'none' else ''
    collection = f"\n\n🏷️{skin['collection']}" if str(skin['collection']).lower() != 'none' else ''
    if condition != "Collections":
        condition_show_name = lang["ru"].get(condition, condition)

        url_name = f'{skin["req_name"]} ({condition})'

        full_name = f'<b>{skin["show_name"]} ({condition_show_name})</b>{rarity}{collection}{min_float}{max_float}'
    else:
        full_name = f'<b>{skin["show_name"]}</b>{collection}\n'
        url_name = f'{skin["req_name"]}'
    skin_id = skin["skin_id"]

    if stattrak and is_stattrakawait:
        full_name = f'<b>StatTrak™</b> {full_name}'
        # Только теперь добавляем префикс и _st
        req_name = f"StatTrak™ {skin['req_name']}"
        url_name = f"StatTrak™ {skin['req_name']}"
        skin_id = skin["skin_id"] + "_st"
    else:
        req_name = skin["req_name"]

    encoded_name = urllib.parse.quote(url_name)  # кодируем пробелы, скобки и спецсимволы

    url = f"https://steamcommunity.com/market/listings/730/{encoded_name}"
    skins_price = await get_skin_price(req_name, condition if condition != "Collections" else '')

    lowest = skins_price.get('lowest_price')
    median = skins_price.get('median_price')
    mid_price = f"\nСредняя цена - {median} 📊\n" if median else "\n"
    min_price = f"Мин. предложение - {lowest} 📉\n\n" if lowest else "\n"

    caption = f"{full_name}{mid_price}{min_price}<a href='{url}'>Посмотреть в Steam</a>"

    if not lowest and not median:
        caption = f"{full_name}\nЭтот предмет никто не продает\n\n<a href='{url}'>Посмотреть в Steam</a>"

    # user_skin = await get_user_skin(user_id, skin_id, condition)

    kb = {}
    # if not user_skin:
    #     kb['Добавить в инвентарь ✚'] = f'add|{skin_id}|{skins_price.get("lowest_price")}|{condition}|{stattrak}'

    kb[f'Инвентарь 🗄️'] = 'inventory_0'
    if condition != "Collections":
        kb['Назад'] = f'back|{skin_id.split("_st")[0]}'
    return {'caption': caption, 'kb': kb,
            'skins_price': skins_price.get('lowest_price') if skins_price.get('lowest_price') else '0.00',
            'skin_id': skin_id}


@user_private_router.callback_query(F.data.startswith('back|'))
async def back(call: types.CallbackQuery):
    skin_id = call.data.split('|')[-1]
    skin = await get_skin(skin_id, 'ru')
    caption, kb = await search_text(skin)
    await call.message.edit_caption(caption=caption,
                                    reply_markup=kb, parse_mode='HTML')


async def search_text(skin):
    req_name = skin['req_name']

    # Если имя не начинается с "StatTrak™", добавляем
    if not req_name.strip().startswith("StatTrak™"):
        query = f"StatTrak™ {req_name} (Field-Tested)"
    else:
        query = f"{req_name} (Field-Tested)"
    is_stattrakawait = await get_exact_name(query)

    stattrak = f"StatTrak™ |{'✅' if is_stattrakawait else '❌'}|"
    collection = f"\n\n🏷️{skin['collection']}" if str(skin['collection']).lower() != 'none' else ''
    min_float = f"Мин. степень износа - {skin['min_float']}\n" if str(skin['min_float']).lower() != 'none' else ''
    max_float = f"Макс. степень износа - {skin['max_float']}\n\n" if str(skin['max_float']).lower() != 'none' else ''
    caption = f"<u><b>{skin['show_name']}</b></u>\n\n{skin['rarity']}\n\n{stattrak}{collection}\n\n{min_float}{max_float}{skin['descr']}"

    kb = condition_kbds(skin['skin_id'], is_stattrakawait)
    return caption, kb


async def start_message(message: types.Message):
    await message.answer("<b>SkinTracker CS2\n\n</b>Следи за ценами на скины в CS2! 💰"
                         "Узнавай текущую минимальную и среднюю стоимость скинов, получай мгновенные уведомления, когда цена изменяется, "
                         "и будь всегда в курсе выгодных предложений на рынке Steam.⚡\n\n"
                         "<i>🔍 Напиши название предмета, который хочешь найти!</i>"
                         , reply_markup=create_inline_kb({'Инвентарь 🗄️': 'inventory_0'})
                         , parse_mode="HTML")


@user_private_router.message(CommandStart())
async def start(message: types.Message):
    user_id = message.from_user.id
    user_first_name = message.from_user.first_name
    await start_message(message)
    await create_user(user_id, user_first_name)
    # await redis.set("key", "value")
    # value = await redis.get("key")


async def skin_show(user_id, skin_name, event: Union[types.Message, types.CallbackQuery]):
    skin_id = await get_skin_id(skin_name)
    if isinstance(event, types.Message):
        message = event
    elif isinstance(event, types.CallbackQuery):
        message = event.message
        await event.answer()
        # Для callback нужно ответить или редактировать сообщение
    else:
        # Неизвестный тип события
        return
    if skin_id:
        skin = await get_skin(skin_id, 'ru')

        if not skin:
            await message.answer("❌ Предмет не найден")
            return

        # type, image, req_name, show_name, descr = local_skins_list
        encoded_name = urllib.parse.quote(skin['req_name'])

        if skin['type'] == 'skin':
            caption, kb = await search_text(skin)
            url = f'<a href="https://steamcommunity.com/market/search?appid=730&q={encoded_name}">Посмотреть в Steam</a>'
            if isinstance(event, types.Message):
                await message.answer_photo(skin['image'], caption=f"{caption}\n\n{url}",
                                           reply_markup=kb, parse_mode='HTML')
                # await message.delete()
            elif isinstance(event, types.CallbackQuery):
                await message.edit_caption(skin['image'], caption=caption,
                                           reply_markup=kb, parse_mode='HTML')
            return
        else:
            skins_price = await get_skin_price(skin['req_name'])
            condition = 'Collections'
            user_skin = await get_user_skin(user_id, skin_id, condition)

            build = await build_skin_message(skin=skin,
                                             )
            kb = build['kb']
            if not user_skin:
                kb = {
                    f'Добавить в инвентарь ✚': f'add|{build["skin_id"]}|{skins_price.get("lowest_price")}|{condition}',
                    **build['kb']}

            if skins_price.get('lowest_price') or skins_price.get('median_price'):
                if isinstance(event, types.Message):

                    await message.answer_photo(skin['image'], caption=build['caption'],
                                               reply_markup=create_inline_kb(kb),

                                               parse_mode='HTML')
                elif isinstance(event, types.CallbackQuery):
                    await message.edit_caption(skin['image'], caption=build['caption'],
                                               reply_markup=create_inline_kb(kb),

                                               parse_mode='HTML')

            else:
                if isinstance(event, types.Message):
                    await message.answer_photo(skin['image'], caption=build['caption'],

                                               reply_markup=create_inline_kb(kb),
                                               parse_mode='HTML')
                    # await message.delete()
                elif isinstance(event, types.CallbackQuery):
                    await message.edit_caption(skin['image'], caption=build['caption'],

                                               reply_markup=create_inline_kb(kb),
                                               parse_mode='HTML')
            return

    await message.answer("❌ Предмет не найден")
    # await message.delete()


@user_private_router.message(F.text)
async def search(message: types.Message):
    user_id = message.from_user.id
    await skin_show(user_id, message.text, message)


@user_private_router.callback_query(F.data.startswith('skincalldata|'))
async def skincalldata(call: types.CallbackQuery):
    user_id = call.from_user.id
    skincalldata = call.data.split('|')
    skin_id = skincalldata[1].split('_st')[0]
    condition = skincalldata[2]

    try:

        _ = skincalldata[3]

        stattrak = True
    except:
        stattrak = False

    skin = await get_skin(skin_id, 'ru')

    # skins_price = await get_skin_price(skin["req_name"], condition)

    build = await build_skin_message(skin=skin,
                                     condition=condition, stattrak=stattrak)
    user_skin = await get_user_skin(user_id, build["skin_id"], condition)

    kb = build['kb']
    caption = build['caption']
    if not user_skin:
        kb = {f'Добавить в инвентарь ✚': f'add|{build["skin_id"]}|{build["skins_price"]}|{condition}|{stattrak}',
              **build['kb']}
    if stattrak:
        caption = f"{build['caption']}"
    try:
        await call.message.edit_caption(caption=
                                        caption,
                                        reply_markup=create_inline_kb(kb),
                                        parse_mode='HTML')
    except:
        await call.message.edit_media(media=InputMediaPhoto(
            media=skin['image'],
            caption=caption,
            parse_mode="HTML"
        ),
            reply_markup=create_inline_kb(kb),
        )


@user_private_router.callback_query(F.data.startswith('add'))
async def skins_add(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    skincalldata = call.data.split('|')
    skin_id = skincalldata[1]
    lowest_price = skincalldata[2]
    condition = skincalldata[3]
    # stattrak = skincalldata[4]
    # stattrak = stattrak.lower() == "true"
    skin = await get_skin(skin_id, 'ru')
    if not condition or condition.lower() == 'none':
        condition = 'Collections'
    # Очистка цены от символов валюты
    price_clean = "".join(c for c in lowest_price if c.isdigit() or c == ".")
    try:
        lowest_price_decimal = float(Decimal(price_clean))
    except Exception as e:
        print("Ошибка конвертации цены:", e)
        lowest_price_decimal = '0.00'

    # if stattrak:
    #     # skin_id = skin_id + '_st'
    #     req_name = f'StatTrak™ {skin["req_name"]}'
    # else:
    req_name = skin["req_name"]

    add = await add_user_skin(user_id, skin_id, req_name, lowest_price_decimal,
                              condition)
    user_skins_raw = await redis.get(f'user_skins_{user_id}')

    if user_skins_raw:
        user_skins = json.loads(user_skins_raw)  # превращаем JSON в список словарей
        user_skins.insert(0, add)  # вставляем элемент в начало списка
        await redis.set(f"user_skins_{user_id}", json.dumps(user_skins), ex=ttl)
    # else:
    #     user_skins = await get_user_skins(user_id)
    #     await redis.set(f'user_skins_{user_id}', json.dumps(user_skins), ex=300)

    await call.answer("Педмет добавлен в инвентарь!", show_alert=True)
    build = await build_skin_message(skin=skin, condition=condition
                                     )

    await call.message.edit_caption(caption=build['caption'],
                                    reply_markup=create_inline_kb(build['kb']),

                                    parse_mode='HTML')


async def inventory_show(user_id, index, call: types.CallbackQuery, delete=False):
    user_skins_raw = await redis.get(f'user_skins_{user_id}')

    if user_skins_raw:
        user_skins = json.loads(user_skins_raw)  # превращаем JSON в список словарей
    else:
        user_skins = await get_user_skins(user_id)
        await redis.set(f'user_skins_{user_id}', json.dumps(user_skins), ex=ttl)
    user_skins_len = len(user_skins)
    if not user_skins:
        if delete:
            await start_message(call.message)
            await call.message.delete()
        else:
            await call.answer("Инвентарь пустой!", show_alert=True)
            await call.answer()
        return
    try:
        user_skins = user_skins[index]
    except:
        user_skins = user_skins[0]
    skin_id = user_skins['skin_id']
    condition = user_skins['condition']
    skin = await get_skin(skin_id, 'ru')

    build = await build_skin_message(skin=skin,
                                     condition=condition)

    caption = f"<b>Инвентарь 🗄️</b>\n<i>Предмет {index + 1}/{user_skins_len}</i>\n\n{build['caption']}"
    kb = {}

    if index > 0:
        kb['⬅️ Назад'] = f'inventory_{index - 1}'
    if index < user_skins_len - 1:
        kb['Вперёд ➡️'] = f'inventory_{index + 1}'

    kb['Настройки 🛠️'] = f'settings|{skin_id}|{condition}|{index}'

    try:
        await call.message.edit_media(
            media=InputMediaPhoto(media=skin['image'], caption=caption, parse_mode='HTML'),
            reply_markup=create_inline_kb(kb, 2 if len(kb) >= 3 else 1)
        )
    except Exception as e:
        print("Ошибка при обновлении медиа:", e)
        # Если сообщение было без фото — просто отправим новое
        await call.answer()
        # await start_message(call.message)
        # await call.message.delete()


@user_private_router.callback_query(F.data.startswith('inventory_'))
async def inventory(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id

    index = call.data.split('_')[-1]
    index = int(index)
    await inventory_show(user_id, index, call)
    # await state.clear()


@user_private_router.callback_query(F.data.startswith('delete'))
async def delete_skin(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    skincalldata = call.data.split('|')
    skin_id = skincalldata[1]
    condition = skincalldata[2]

    await delete_user_skin(user_id, skin_id, condition)
    skin = await get_skin(skin_id, 'ru')
    await redis.delete(f"user_skins_{user_id}")
    await build_skin_message(skin=skin, condition=condition)
    index = 0
    await inventory_show(user_id, index, call, delete=True)


@user_private_router.callback_query(F.data.startswith('go_to'))
async def go_to(call: types.CallbackQuery):
    user_id = call.from_user.id
    skin_name = call.data.split(',')[-1]
    await skin_show(user_id, skin_name, call)


@user_private_router.callback_query(
    or_f(F.data.startswith('settings'), (F.data.startswith('increase_by')), (F.data.startswith('price'))))
async def settings(call: types.CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    skincalldata = call.data.split('|')
    skin_id = skincalldata[1]
    condition = skincalldata[2]
    index = skincalldata[3]
    data = await state.get_data()
    increase_by = [0.10, 1, 5, 10, 50, 100]
    user_skins_raw = await redis.get(f'user_skins_{user_id}')

    if user_skins_raw:
        user_skins = json.loads(user_skins_raw)  # превращаем JSON в список словарей
    else:
        user_skins = await get_user_skins(user_id)
        await redis.set(f'user_skins_{user_id}', json.dumps(user_skins), ex=ttl)
        # Теперь обновляем переменную data, чтобы дальше работать с актуальным значением
        # data = await state.get_data()
        # user_skins = data.get("user_skins")
    # print(user_skins)
    current_index = data.get("increase_by_index", 1)
    if call.data.startswith('increase_by'):
        calldata = call.data.split('|')
        value = calldata[4]

        if value == 'plus':
            current_index = (current_index + 1) % len(increase_by)
        elif value == 'minus':
            current_index = (current_index - 1) % len(increase_by)

    new_value = increase_by[current_index]

    await state.update_data(increase_by_index=current_index)
    skin = await get_skin(skin_id, 'ru')
    build = await build_skin_message(skin=skin,
                                     condition=condition)

    user_skin = next(
        (
            s for s in user_skins
            if s["skin_id"] == skin_id and (not condition or condition.lower() == 'none' or s["condition"] == condition)
        ),
        None
    )
    if not user_skin:
        await call.answer("Предмет не найден.", show_alert=True)
        return

    non_zero_threshold = [s for s in user_skins if Decimal(s["threshold_value"]) > Decimal('0.00')]
    count = len(non_zero_threshold)

    current = Decimal(user_skin['threshold_value'] or '0.00')

    if call.data.startswith('price'):
        calldata = call.data.split('|')

        action = calldata[4]

        if action == 'plus':
            # Если предмет новый и лимит достигнут — нельзя добавлять
            if current == 0 and count >= 5:
                await call.answer('Нельзя отслеживать больше 5 предметов!', show_alert=True)
            else:
                # Если предмет новый — увеличиваем счётчик
                if current == 0:
                    count += 1
                # Всегда увеличиваем current
                current += Decimal(new_value)

        elif action and action == 'minus':
            current = max(Decimal('0.00'), current - Decimal(str(new_value)))
            if current == 0:
                count -= 1
        await user_skin_trigger(user_id, skin_id, condition, str(current),
                                str(build['skins_price'].replace("$", "").replace(",", "")))
        user_skin['threshold_value'] = str(current)

        # !!! Обновляем список в state
        await redis.set(f"user_skins_{user_id}", json.dumps(user_skins), ex=ttl)
        print(user_skins)
    current = f"Отслеживать изменение цены на <b>{current:.2f}$</b>" if current else 'Для отслеживание цены нажмите на <b>"+"</b>'
    caption = f"<b>Настройки 🛠️</b>\n\n{build['caption']}\n\nОтслеживаемых предметов <b>({count})</b>\n\n{current}"
    kb = {}
    #

    kb['-'] = f'price|{skin_id}|{condition}|{index}|minus'
    kb['+'] = f'price|{skin_id}|{condition}|{index}|plus'
    kb['<'] = f'increase_by|{skin_id}|{condition}|{index}|minus'
    kb[f'Шаг {new_value:.2f}$'] = 'None'
    kb['>'] = f'increase_by|{skin_id}|{condition}|{index}|plus'

    if condition != 'Collections':
        kb['Подробнее↗️'] = f'go_to,{skin["req_name"]}'
    kb['Удалить 🗑️'] = f'delete|{skin_id}|{condition}'
    kb['Назад'] = f'inventory_{index}'
    try:
        await call.message.edit_caption(caption=caption, reply_markup=create_inline_kb(kb, 2, 3, 1), parse_mode="HTML")
    except:
        await call.answer()


@user_private_router.callback_query(F.data == 'None')
async def none(call: types.CallbackQuery):
    await call.answer()

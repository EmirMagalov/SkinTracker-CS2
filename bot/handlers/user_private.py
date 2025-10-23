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

user_private_router = Router()


async def build_skin_message(user_id, skin, stattrak=False, condition=None):
    is_stattrakawait = await get_exact_name(f"StatTrak™ {skin['req_name']} (Field-Tested)")
    if condition == None:
        condition = "Collections"

    rarity = f'\n\n{skin["rarity"]}' if skin["rarity"].lower() != 'none' else ''

    min_float = f"\n\nМин. степень износа - {skin['min_float']}\n" if str(skin['min_float']).lower() != 'none' else ''
    max_float = f"Макс. степень износа - {skin['max_float']}\n" if str(skin['max_float']).lower() != 'none' else ''
    if condition != "Collections":
        condition_show_name = lang["ru"].get(condition, condition)

        url_name = f'{skin["req_name"]} ({condition})'

        full_name = f'<b>{skin["show_name"]} ({condition_show_name})</b>{rarity}{min_float}{max_float}'
    else:
        full_name = f'<b>{skin["show_name"]}</b>\n'
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

    if skins_price.get('lowest_price') or skins_price.get('median_price'):
        mid_price = '\nСредняя цена - ' + str(skins_price.get('median_price')) + ' 📊'
        min_price = 'Мин. предложение - ' + skins_price.get('lowest_price') + ' 📉\n\n'

        caption = f"{full_name}{mid_price if skins_price.get('median_price') else ''}\n{min_price if skins_price.get('lowest_price') else ''}<a href='{url}'>Посмотреть в Steam</a>"
    else:
        caption = f"{full_name}\n\nЭтот предмет никто не продает\n\n<a href='{url}'>Посмотреть в Steam</a>"

    user_skin = await get_user_skin(user_id, skin_id, condition)

    kb = {}
    if not user_skin:
        kb['Добавить в инвентарь ✚'] = f'add|{skin_id}|{skins_price.get("lowest_price")}|{condition}|{stattrak}'

    kb[f'Инвентарь 🗄️'] = 'inventory_0'
    if condition != "Collections":
        kb['Назад'] = f'back|{skin_id.split("_st")[0]}'
    return caption, kb, skins_price.get('lowest_price') if skins_price.get('lowest_price') else '0.00'
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

    min_float = f"Мин. степень износа - {skin['min_float']}\n" if str(skin['min_float']).lower() != 'none' else ''
    max_float = f"Макс. степень износа - {skin['max_float']}\n\n" if str(skin['max_float']).lower() != 'none' else ''
    caption = f"<u><b>{skin['show_name']}</b></u>\n\n{skin['rarity']}\n\n{min_float}{max_float}{stattrak}\n\n{skin['descr']}"

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

            caption, kb, _ = await build_skin_message(user_id=user_id, skin=skin,
                                                      )
            if skins_price.get('lowest_price') or skins_price.get('median_price'):
                if isinstance(event, types.Message):
                    await message.answer_photo(skin['image'], caption=caption,
                                               reply_markup=create_inline_kb(kb),

                                               parse_mode='HTML')
                elif isinstance(event, types.CallbackQuery):
                    await message.edit_caption(skin['image'], caption=caption,
                                               reply_markup=create_inline_kb(kb),

                                               parse_mode='HTML')

            else:
                if isinstance(event, types.Message):
                    await message.answer_photo(skin['image'], caption=caption,

                                               reply_markup=create_inline_kb(kb),
                                               parse_mode='HTML')
                    # await message.delete()
                elif isinstance(event, types.CallbackQuery):
                    await message.edit_caption(skin['image'], caption=caption,

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
        print(skincalldata[3])
        _ = skincalldata[3]

        stattrak = True
    except:
        stattrak = False

    skin = await get_skin(skin_id, 'ru')

    # skins_price = await get_skin_price(skin["req_name"], condition)

    caption, kb, _ = await build_skin_message(user_id=user_id, skin=skin,
                                              condition=condition, stattrak=stattrak)
    if stattrak:
        caption = f"{caption}"
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
async def skins_add(call: types.CallbackQuery):
    user_id = call.from_user.id
    skincalldata = call.data.split('|')
    skin_id = skincalldata[1]
    lowest_price = skincalldata[2]
    condition = skincalldata[3]
    stattrak = skincalldata[4]
    stattrak = stattrak.lower() == "true"
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
    await add_user_skin(user_id, skin_id, req_name, lowest_price_decimal,
                        condition)

    await call.answer("Педмет добавлен в инвентарь!", show_alert=True)
    caption, kb, _ = await build_skin_message(user_id=user_id, skin=skin, condition=condition
                                              )

    await call.message.edit_caption(caption=caption,
                                    reply_markup=create_inline_kb(kb),

                                    parse_mode='HTML')


async def inventory_show(user_id, index, call: types.CallbackQuery, delete=False):
    user_skins = await get_user_skins(user_id)

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

    caption, _, _ = await build_skin_message(user_id=user_id, skin=skin,
                                             condition=condition)

    caption = f"<b>Инвентарь 🗄️</b>\n<i>Предмет {index + 1}/{user_skins_len}</i>\n\n{caption}"
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
async def inventory(call: types.CallbackQuery):
    user_id = call.from_user.id

    index = call.data.split('_')[-1]
    index = int(index)
    await inventory_show(user_id, index, call)


@user_private_router.callback_query(F.data.startswith('delete'))
async def delete_skin(call: types.CallbackQuery):
    user_id = call.from_user.id
    skincalldata = call.data.split('|')
    skin_id = skincalldata[1]
    condition = skincalldata[2]

    await delete_user_skin(user_id, skin_id, condition)
    skin = await get_skin(skin_id, 'ru')

    caption, _, _ = await build_skin_message(user_id=user_id, skin=skin, condition=condition)
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

    increase_by = [0.10, 1, 5, 10, 50, 100]
    data = await state.get_data()
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
    caption, _, last_price = await build_skin_message(user_id=user_id, skin=skin,
                                                      condition=condition)
    user_skins = await get_user_skins(user_id)
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
                                str(last_price.replace("$", "").replace(",", "")))
    current = f"Отслеживать изменение цены на <b>{current:.2f}$</b>" if current else 'Для отслеживание цены нажмите на <b>"+"</b>'
    caption = f"<b>Настройки 🛠️</b>\n\n{caption}\n\nОтслеживаемых предметов <b>({count})</b>\n\n{current}"
    kb = {}
    #

    kb['-'] = f'price|{skin_id}|{condition}|{index}|minus'
    kb['+'] = f'price|{skin_id}|{condition}|{index}|plus'
    kb['<'] = f'increase_by|{skin_id}|{condition}|{index}|minus'
    kb[f'Шаг {new_value:.2f}$'] = 'None'
    kb['>'] = f'increase_by|{skin_id}|{condition}|{index}|plus'

    if condition.lower() != 'none':
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

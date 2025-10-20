from middlewares.loader import skins_en, skins_ru
from aiogram import types
import re
from rapidfuzz import process, fuzz


# --- нормализация текста ---
def normalize(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = text.replace("ё", "е")
    text = re.sub(r'[«»"\'`|]', ' ', text)  # ← заменяем | на пробел
    text = re.sub(r'\s+', ' ', text)  # схлопываем пробелы
    return text.strip()


# --- функция для поиска скина/кейса ---
async def get_skin_id(skins_name: str, threshold=70):
    query = normalize(skins_name)

    is_cyrillic = any("а" <= c <= "я" or "А" <= c <= "Я" for c in query)
    search_list = skins_ru if is_cyrillic else skins_en
    iterable = search_list.values() if isinstance(search_list, dict) else search_list

    # собираем все варианты для поиска (имена скинов + имена кейсов)
    search_choices = []
    lookup = {}  # чтобы потом знать, какой id вернуть

    for s in iterable:
        name = s.get("name", "")
        norm_name = normalize(name)
        search_choices.append(norm_name)
        lookup[norm_name] = s.get("id")
    # elif s.get("id").startswith('key'):
    #     for crate in s.get("crates", []):
    #         crate_name = crate.get("name", "")
    #         norm_crate_name = normalize(crate_name)
    #         search_choices.append(norm_crate_name)
    #         lookup[norm_crate_name] = crate.get("id")
    # elif s.get("id").startswith('graffiti'):
    #     name = s.get("name", "")
    #     norm_name = normalize(name)
    #     search_choices.append(norm_name)
    #     lookup[norm_name] = s.get("skin_id")

    # ищем лучшее совпадение с помощью rapidfuzz
    best_match = process.extractOne(query, search_choices, scorer=fuzz.partial_ratio, score_cutoff=threshold)

    if best_match:
        match_text, score, _ = best_match
        return lookup[match_text]

    return None


async def skin_lang(skin_id, lang):
    skins = skins_en if lang == 'en' else skins_ru

    # Проверка списка или словаря
    if isinstance(skins, dict):
        iterable = skins.values()
    else:
        iterable = skins

    for s in iterable:
        # and not
        if skin_id.lower() == s.get("id", "").lower():
            if s.get("id").startswith('collection'):

                for crate in s.get("crates", []):
                    if crate.get('id').startswith('crate'):
                        return "crates", s.get("crates")[0]
            if s.get("id").startswith('skin'):
                return "skin", s
            else:
                return 'other', s
        #
        #
        # elif s.get("id").startswith('key') and skin_id.lower() == s.get("id", "").lower():
        #     for crate in s.get("crates", []):
        #         if skin_id.lower() == crate.get("id", "").lower():
        #             return "case", crate
        # elif s.get("id").startswith('graffiti') and skin_id.lower() == s.get("id", "").lower():
        #     if skin_id.lower() == s.get("id", "").lower():
        #         return "graffiti", s
    return None, None


async def get_skin(skin_id, lang):
    type, skins_data_en = await skin_lang(skin_id, 'en')
    if not type or not skins_data_en:
        # print(f"⚠️ skin_lang не вернула данные для {skin_id}")
        return None
    # if type == 'skin':
    #     name_for_request = f"{skins_data_en.get('weapon').get('name')} | {skins_data_en.get('pattern').get('name')}"
    # else:
    name_for_request = skins_data_en.get('name')
    clean_name_for_request = re.sub(r"\s*\(.*?\)", "", name_for_request).strip()
    type, skins_data = await skin_lang(skin_id, lang)

    if not skins_data:
        return None, name_for_request, None, None
    # print(skins_data)

    # if type == 'skin':
    #     weapon = skins_data.get('weapon').get('name')
    #     pattern = skins_data.get('pattern').get('name')
    #      # кейсы могут не иметь description
    #     show_name = f"{weapon} | {pattern}"
    # else:
    show_name = skins_data.get('name')
    clean_name = re.sub(r"★|\s*\(.*?\)", "", show_name).strip()

    descr = skins_data.get('description', '')
    image = skins_data.get('image')
    descr = (descr or "").replace('\\r\\n', '\n').replace('\\n', '\n').replace("<br>", "\n")
    # rarity_data = skins_data.get('rarity')
    # rarity = rarity_data.get('name') if rarity_data else None
    rarity_data_en =skins_data_en.get('rarity')
    rarity_en = rarity_data_en.get('name') if rarity_data_en else None

    # return type, image, clean_name_for_request, clean_name, descr
    return {
        "skin_id": skin_id,
        "type": type,
        "image": image,
        "req_name": clean_name_for_request,
        "show_name": clean_name,
        "descr": descr,
        "rarity": f"{rarity_translate[lang].get(rarity_en)}"
    }


lang = {
    "ru": {
        'Factory New': 'Прямо с завода',
        'Minimal Wear': 'Немного поношенное',
        'Field-Tested': 'После полевых испытаний',
        'Well-Worn': 'Поношенное',
        'Battle-Scarred': 'Закалённое в боях'
    }
}


rarity_translate ={
    'ru':{
        'Consumer Grade': '🤍Ширпотреб',  # ширпотреб
        'Industrial Grade': '🩵Промышленное какчество',  # промышленное какчество
        'Mil-Spec Grade': '💙Армейское качество',  # армейские
        'Restricted': '💜Запрещенное',  # запрещенное
        'Classified': '🩷Засекреченное ',  # засекреченное
        'Covert': '❤️Тайное',  # тайное
        'Extraordinary': '💛Редкое',  # крайне редкий предмет или контрабандное
        'Contraband': '🧡Contraband'  # Контрабанда
    },
    'en': {
        'Consumer Grade': '🤍Consumer Grade',  # ширпотреб
        'Industrial Grade': '🩵Industrial Grade',  # промышленное какчество
        'Mil-Spec Grade': '💙Mil-Spec',  # армейские
        'Restricted': '💜Restricted',  # запрещенное
        'Classified': '🩷Classified ',  # засекреченное
        'Covert': '❤️Covert',  # тайное
        'Extraordinary': '💛Exceedingly Rare',  # крайне редкий предмет или контрабандное
        'Contraband': '🧡Контрабандное'  # Контрабанда
    }
}

rarity_color = {
        'Consumer Grade':'',#ширпотреб
        'Industrial Grade':'',#промышленное какчество
        'Mil-Spec Grade':'', #армейские
        'Restricted':'',#запрещенное
        'Classified':'',#засекреченное
        'Covert':'',#тайное
        'Extraordinary':'',#крайне редкий предмет или контрабандное
        'Contraband':''#Контрабанда

    }
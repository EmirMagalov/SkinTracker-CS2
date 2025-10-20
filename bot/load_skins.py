import requests
import json

def load_skins():
    url = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/ru/all.json"
    data = requests.get(url).json()
    with open("all_skins_ru.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print("✅ Скины сохранены локально")

load_skins()
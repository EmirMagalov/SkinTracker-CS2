from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def condition_kbds(skin_id: str):
    builder = InlineKeyboardBuilder()
    #'🟩'
    #'🟦'
    #'🟨'
    #'🟧'
    #'🟥'
    conditions = {
        'Прямо с завода': 'Factory New',
        'Немного поношенное': 'Minimal Wear',
        'После полевых испытаний': 'Field-Tested',
        'Поношенное': 'Well-Worn',
        'Закалённое в боях': 'Battle-Scarred',
    }

    # Добавляем кнопки выбора состояния
    for name, condition in conditions.items():
        builder.button(
            text=name,
            callback_data=f"skincalldata|{skin_id}|{condition}"
        )

    builder.adjust(1)

    # Добавляем кнопку «Инвентарь»
    builder.row(
        InlineKeyboardButton(
            text="Инвентарь 🗄️",
            callback_data="inventory_0"
        )
    )

    return builder.as_markup()


def create_inline_kb(data: dict[str, str],row1=1,row2=1):
    inline_kb = InlineKeyboardBuilder()
    for text, callback in data.items():
        inline_kb.add(InlineKeyboardButton(text=text, callback_data=callback))
    inline_kb.adjust(row1,row2)

    return inline_kb.as_markup()

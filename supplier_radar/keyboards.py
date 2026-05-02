from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def lead_keyboard(lead_id: int, author_username: str | None = None, message_link: str | None = None):
    rows = [
        [
            InlineKeyboardButton(text="✅ Валидный", callback_data=f"lead:valid:{lead_id}"),
            InlineKeyboardButton(text="❌ Спам", callback_data=f"lead:spam:{lead_id}"),
        ],
        [
            InlineKeyboardButton(text="📌 Обработан", callback_data=f"lead:done:{lead_id}"),
        ],
    ]

    link_buttons = []
    if author_username:
        link_buttons.append(InlineKeyboardButton(text="💬 Написать автору", url=f"https://t.me/{author_username}"))
    if message_link:
        link_buttons.append(InlineKeyboardButton(text="🔗 Открыть сообщение", url=message_link))

    if link_buttons:
        rows.append(link_buttons)

    return InlineKeyboardMarkup(inline_keyboard=rows)

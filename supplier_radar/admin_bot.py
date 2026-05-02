import html

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from supplier_radar.database import Database
from supplier_radar.filters import DISCOVERY_QUERIES, INTENT_WORDS, TOPIC_WORDS, NEGATIVE_WORDS
from supplier_radar.notifier import h
from supplier_radar.runtime_config import settings


def is_admin(user_id: int) -> bool:
    return user_id in settings.admin_ids


async def run_admin_bot(db: Database, discovery, listener):
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def start(message: Message):
        if not is_admin(message.from_user.id):
            await message.answer("⛔️ У вас нет доступа к этому боту.")
            return

        await message.answer(
            "👋 <b>Supplier Radar запущен</b>\n\n"
            "Я ищу в Telegram людей, которые пишут запросы про поставщиков, "
            "базы, закуп, косметику, WB/Ozon и открытие магазина.\n\n"
            "Команды:\n"
            "/id — узнать свой Telegram ID\n"
            "/stats — статистика\n"
            "/leads — последние лиды\n"
            "/groups — найденные группы\n"
            "/discovery — статус автопоиска групп\n"
            "/findgroups — запустить поиск групп вручную\n"
            "/keywords — ключевые слова\n"
            "/help — помощь"
        )

    @dp.message(Command("id"))
    async def my_id(message: Message):
        await message.answer(f"Ваш Telegram ID:\n<code>{message.from_user.id}</code>")

    @dp.message(Command("stats"))
    async def stats(message: Message):
        if not is_admin(message.from_user.id):
            return

        s = db.stats()
        await message.answer(
            "📊 <b>Статистика</b>\n\n"
            f"Всего лидов: <b>{s['total_leads']}</b>\n"
            f"Новые: <b>{s['new_leads']}</b>\n"
            f"Валидные: <b>{s['valid_leads']}</b>\n"
            f"Спам: <b>{s['spam_leads']}</b>\n\n"
            f"Групп в базе: <b>{s['groups']}</b>\n"
            f"Подключено/вступил: <b>{s['joined']}</b>"
        )

    @dp.message(Command("leads"))
    async def leads(message: Message):
        if not is_admin(message.from_user.id):
            return

        rows = db.get_recent_leads(10)
        if not rows:
            await message.answer("Пока лидов нет.")
            return

        parts = ["🔥 <b>Последние лиды</b>\n"]
        for row in rows:
            author = f"@{h(row['author_username'])}" if row["author_username"] else h(row["author_name"] or row["author_id"])
            parts.append(
                f"\n<b>#{row['id']}</b> | score {row['score']} | {h(row['status'])}\n"
                f"Группа: {h(row['chat_title'])}\n"
                f"Автор: {author}\n"
                f"Текст: {h((row['text'] or '')[:300])}\n"
            )

        await message.answer("\n".join(parts), disable_web_page_preview=True)

    @dp.message(Command("groups"))
    async def groups(message: Message):
        if not is_admin(message.from_user.id):
            return

        rows = db.list_groups(20)
        if not rows:
            await message.answer("Пока групп в базе нет.")
            return

        parts = ["👥 <b>Последние группы</b>\n"]
        for row in rows:
            username = f"@{h(row['username'])}" if row["username"] else "нет username"
            joined = "✅ joined" if row["joined"] else "➕ found"
            members = row["members_count"] or "?"
            parts.append(
                f"\n{joined} <b>{h(row['title'])}</b>\n"
                f"{username} | участников: {members}\n"
                f"источник: {h(row['source_query'])}"
            )

        await message.answer("\n".join(parts), disable_web_page_preview=True)

    @dp.message(Command("discovery"))
    async def discovery_status(message: Message):
        if not is_admin(message.from_user.id):
            return

        st = db.discovery_status()
        await message.answer(
            "🔎 <b>Статус автопоиска групп</b>\n\n"
            f"Включен: <b>{'да' if settings.auto_discovery_enabled else 'нет'}</b>\n"
            f"Сейчас работает: <b>{h(st.get('discovery_running') or 'false')}</b>\n"
            f"Последний старт: <code>{h(st.get('discovery_last_start') or 'нет')}</code>\n"
            f"Последнее завершение: <code>{h(st.get('discovery_last_finish') or 'нет')}</code>\n"
            f"Следующий запуск: <code>{h(st.get('discovery_next_run') or 'нет')}</code>\n"
            f"FloodWait до: <code>{h(st.get('discovery_floodwait_until') or 'нет')}</code>\n"
            f"Последний результат: {h(st.get('discovery_last_summary') or 'нет')}\n"
            f"Последняя ошибка: <code>{h(st.get('discovery_last_error') or 'нет')}</code>"
        )

    @dp.message(Command("findgroups"))
    async def findgroups(message: Message):
        if not is_admin(message.from_user.id):
            return

        await message.answer("🔎 Запускаю ручной поиск групп. Результат пришлю отдельным сообщением.")
        result = await discovery.run_manual()
        await message.answer(f"Готово: <code>{h(result)}</code>")

    @dp.message(Command("keywords"))
    async def keywords(message: Message):
        if not is_admin(message.from_user.id):
            return

        await message.answer(
            "🔑 <b>Ключевые слова</b>\n\n"
            "<b>Запросы для поиска групп:</b>\n"
            + "\n".join(f"— {h(x)}" for x in DISCOVERY_QUERIES)
            + "\n\n<b>Намерение клиента:</b>\n"
            + ", ".join(h(x) for x in INTENT_WORDS[:20])
            + "\n\n<b>Темы:</b>\n"
            + ", ".join(h(x) for x in TOPIC_WORDS[:25])
            + "\n\n<b>Минус-слова:</b>\n"
            + ", ".join(h(x) for x in NEGATIVE_WORDS[:25])
        )

    @dp.message(Command("help"))
    async def help_cmd(message: Message):
        if not is_admin(message.from_user.id):
            return

        await message.answer(
            "ℹ️ <b>Как работает бот</b>\n\n"
            "1. Telethon-аккаунт читает группы, где он состоит.\n"
            "2. Бот сам ищет новые публичные группы по ключевым словам.\n"
            "3. Если группа публичная, бот может сам вступить.\n"
            "4. Когда Telegram дает FloodWait, бот уведомляет админа, ждёт и потом сам запускает новый поиск.\n"
            "5. Найденные заявки приходят сюда карточками."
        )

    @dp.callback_query()
    async def callbacks(callback: CallbackQuery):
        if not callback.from_user or not is_admin(callback.from_user.id):
            await callback.answer("Нет доступа", show_alert=True)
            return

        data = callback.data or ""
        if data.startswith("lead:"):
            _, status, lead_id_raw = data.split(":")
            lead_id = int(lead_id_raw)

            status_map = {
                "valid": "valid",
                "spam": "spam",
                "done": "done",
            }
            db.update_lead_status(lead_id, status_map.get(status, status))
            await callback.answer("Сохранено")
            await callback.message.answer(f"Лид #{lead_id} отмечен как: <b>{h(status)}</b>")
            return

        await callback.answer()

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

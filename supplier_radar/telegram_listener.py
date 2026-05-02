import logging
from typing import Optional

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import Channel, Chat, User

from supplier_radar.database import Database
from supplier_radar.filters import score_message
from supplier_radar.keyboards import lead_keyboard
from supplier_radar.notifier import Notifier, h
from supplier_radar.runtime_config import settings

logger = logging.getLogger(__name__)


class TelegramLeadListener:
    def __init__(self, db: Database, notifier: Notifier):
        self.db = db
        self.notifier = notifier
        self.client: TelegramClient | None = None
        self.ready = False

    async def start(self):
        if not settings.session_string:
            await self.notifier.send_admins(
                "❌ <b>SESSION_STRING не заполнен</b>\n\n"
                "Сначала запусти <code>python make_session.py</code>, получи строку "
                "и вставь её в <code>config.py</code>."
            )
            raise RuntimeError("SESSION_STRING is empty")

        if not settings.bot_token or "PASTE" in settings.bot_token:
            raise RuntimeError("BOT_TOKEN is empty")

        logger.info("Starting Telethon listener...")
        self.client = TelegramClient(StringSession(settings.session_string), settings.api_id, settings.api_hash)
        await self.client.start()

        self.client.add_event_handler(self.on_new_message, events.NewMessage)

        self.ready = True
        me = await self.client.get_me()
        username = getattr(me, "username", None)
        await self.notifier.send_admins(
            "✅ <b>Telegram session подключена</b>\n"
            f"Аккаунт: {h(getattr(me, 'first_name', ''))} {h(getattr(me, 'last_name', ''))}\n"
            f"Username: @{h(username) if username else 'нет'}\n\n"
            "Бот начинает мониторить группы."
        )

        if settings.scan_existing_dialogs:
            await self.scan_existing_dialogs()

        await self.client.run_until_disconnected()

    async def on_new_message(self, event):
        try:
            text = event.raw_text or ""
            if not text or len(text) < 5:
                return

            lead_score = score_message(text)
            if not lead_score.is_valid:
                return

            chat = await event.get_chat()
            sender = await event.get_sender()

            await self.process_lead(event, chat, sender, text, lead_score)

        except Exception as e:
            logger.exception("Error in on_new_message: %s", e)

    async def process_lead(self, event, chat, sender, text, lead_score):
        chat_id = getattr(chat, "id", None)
        message_id = getattr(event.message, "id", None)

        message_uid = f"{chat_id}:{message_id}"

        chat_title = getattr(chat, "title", "Неизвестная группа")
        chat_username = getattr(chat, "username", None)

        author_id = getattr(sender, "id", None)
        author_username = getattr(sender, "username", None)

        first_name = getattr(sender, "first_name", "") or ""
        last_name = getattr(sender, "last_name", "") or ""
        author_name = (first_name + " " + last_name).strip()

        message_link = None
        if chat_username and message_id:
            message_link = f"https://t.me/{chat_username}/{message_id}"

        data = {
            "message_uid": message_uid,
            "chat_id": chat_id,
            "chat_title": chat_title,
            "chat_username": chat_username,
            "message_id": message_id,
            "author_id": author_id,
            "author_username": author_username,
            "author_name": author_name,
            "text": text,
            "score": lead_score.score,
            "reasons": "; ".join(lead_score.reasons),
        }

        is_new = self.db.add_lead(data)
        if not is_new:
            return

        recent = self.db.get_recent_leads(1)
        lead_id = recent[0]["id"] if recent else 0

        author_line = f"@{h(author_username)}" if author_username else h(author_name or author_id or "нет username")
        group_line = h(chat_title)
        if chat_username:
            group_line += f" (@{h(chat_username)})"

        msg = (
            "🔥 <b>Новый лид найден</b>\n\n"
            f"<b>Запрос:</b>\n{h(text[:1500])}\n\n"
            f"<b>Группа:</b> {group_line}\n"
            f"<b>Автор:</b> {author_line}\n"
            f"<b>Оценка:</b> {lead_score.score}/10\n"
        )

        await self.notifier.send_admins(
            msg,
            reply_markup=lead_keyboard(lead_id, author_username, message_link),
        )

    async def scan_existing_dialogs(self):
        if not self.client:
            return

        await self.notifier.send_admins(
            "🔎 <b>Сканирую уже подключенные группы</b>\n"
            f"Проверяю последние {settings.recent_scan_limit} сообщений в группах аккаунта."
        )

        dialogs_count = 0
        checked_messages = 0
        found = 0

        async for dialog in self.client.iter_dialogs():
            entity = dialog.entity

            is_group = getattr(dialog, "is_group", False)
            is_channel = getattr(dialog, "is_channel", False)
            if not (is_group or is_channel):
                continue

            # Сохраняем группу/чат
            self.db.upsert_group({
                "chat_id": getattr(entity, "id", None),
                "title": getattr(entity, "title", dialog.name),
                "username": getattr(entity, "username", None),
                "members_count": getattr(entity, "participants_count", None),
                "source_query": "existing_dialog",
                "status": "existing",
                "joined": True,
            })

            dialogs_count += 1

            try:
                async for message in self.client.iter_messages(entity, limit=settings.recent_scan_limit):
                    checked_messages += 1
                    text = message.raw_text or ""
                    if not text:
                        continue

                    lead_score = score_message(text)
                    if not lead_score.is_valid:
                        continue

                    fake_event = type("EventLike", (), {"message": message})()
                    fake_event.message = message
                    chat = entity
                    sender = await message.get_sender()
                    before = len(self.db.get_recent_leads(1))
                    await self.process_lead(fake_event, chat, sender, text, lead_score)
                    found += 1

            except Exception as e:
                logger.warning("Failed to scan dialog %s: %s", dialog.name, e)

        await self.notifier.send_admins(
            "✅ <b>Первичный скан завершен</b>\n\n"
            f"Групп просмотрено: <b>{dialogs_count}</b>\n"
            f"Сообщений проверено: <b>{checked_messages}</b>\n"
            f"Похожих лидов найдено: <b>{found}</b>"
        )

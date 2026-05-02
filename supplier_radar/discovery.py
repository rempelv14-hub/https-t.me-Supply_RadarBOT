import asyncio
import logging
from datetime import datetime, timezone, timedelta

from telethon.errors import FloodWaitError, UserAlreadyParticipantError
from telethon.tl.functions.contacts import SearchRequest
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import Channel

from supplier_radar.database import Database, now_iso
from supplier_radar.filters import DISCOVERY_QUERIES, is_valid_group
from supplier_radar.notifier import Notifier, h
from supplier_radar.runtime_config import settings

logger = logging.getLogger(__name__)


def fmt_seconds(seconds: int) -> str:
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours:
        parts.append(f"{hours} ч.")
    if minutes:
        parts.append(f"{minutes} мин.")
    if secs or not parts:
        parts.append(f"{secs} сек.")
    return " ".join(parts)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso(dt: datetime) -> str:
    return dt.isoformat()


class DiscoveryManager:
    def __init__(self, db: Database, notifier: Notifier, listener):
        self.db = db
        self.notifier = notifier
        self.listener = listener
        self._lock = asyncio.Lock()

    async def start_scheduler(self):
        if not settings.auto_discovery_enabled:
            logger.info("Auto discovery disabled.")
            return

        await asyncio.sleep(settings.auto_discovery_start_delay_seconds)

        while True:
            try:
                await self.run_cycle(reason="scheduler")
                next_run = utc_now() + timedelta(hours=settings.auto_discovery_interval_hours)
                self.db.set_state("discovery_next_run", iso(next_run))
                await asyncio.sleep(settings.auto_discovery_interval_hours * 3600)

            except FloodWaitError as e:
                wait_seconds = int(e.seconds) + settings.floodwait_extra_seconds
                until = utc_now() + timedelta(seconds=wait_seconds)
                self.db.set_state("discovery_floodwait_until", iso(until))
                self.db.set_state("discovery_next_run", iso(until))
                self.db.set_state("discovery_last_error", f"FloodWait {e.seconds} sec")

                if settings.discovery_notify_floodwait:
                    await self.notifier.send_admins(
                        "⏳ <b>Telegram дал FloodWait при автопоиске групп</b>\n\n"
                        f"Пауза: <b>{fmt_seconds(e.seconds)}</b>\n"
                        f"Доп. запас: <b>{fmt_seconds(settings.floodwait_extra_seconds)}</b>\n"
                        f"Новый запуск после: <code>{h(iso(until))}</code>\n\n"
                        "Бот не сломался. Я сам продолжу поиск после окончания лимита."
                    )

                await asyncio.sleep(wait_seconds)

                self.db.set_state("discovery_floodwait_until", "")
                if settings.discovery_notify_resume:
                    await self.notifier.send_admins(
                        "✅ <b>FloodWait закончился</b>\n\n"
                        "🔄 Запускаю новый поиск групп прямо сейчас.\n"
                        "Если Telegram снова даст лимит, я опять предупрежу и продолжу после паузы."
                    )

            except Exception as e:
                logger.exception("Discovery scheduler error: %s", e)
                self.db.set_state("discovery_last_error", str(e))
                await self.notifier.send_admins(
                    "⚠️ <b>Ошибка автопоиска групп</b>\n\n"
                    f"<code>{h(e)}</code>\n\n"
                    "Через 10 минут попробую снова."
                )
                await asyncio.sleep(600)

    async def run_cycle(self, reason: str = "manual"):
        if self._lock.locked():
            return "already_running"

        async with self._lock:
            if not self.listener.client or not self.listener.ready:
                await self.notifier.send_admins(
                    "⏳ <b>Автопоиск групп ждёт Telegram session</b>\n"
                    "Сначала должна подключиться Telethon-сессия."
                )
                await asyncio.sleep(10)
                return "not_ready"

            self.db.set_state("discovery_running", "true")
            self.db.set_state("discovery_last_start", now_iso())
            self.db.set_state("discovery_last_error", "")

            if settings.discovery_notify_start:
                await self.notifier.send_admins(
                    "🔎 <b>Запускаю автопоиск новых групп</b>\n\n"
                    f"Запросов: <b>{len(DISCOVERY_QUERIES)}</b>\n"
                    f"Лимит на запрос: <b>{settings.auto_discovery_limit_per_query}</b>\n"
                    f"Авто-вступление: <b>{'включено' if settings.auto_join_public_groups else 'выключено'}</b>"
                )

            found_total = 0
            saved_total = 0
            joined_total = 0
            skipped_total = 0

            try:
                for query in DISCOVERY_QUERIES:
                    found, saved, joined, skipped = await self.search_query(query)
                    found_total += found
                    saved_total += saved
                    joined_total += joined
                    skipped_total += skipped

                    # Небольшая пауза между поисками, чтобы не давить Telegram
                    await asyncio.sleep(5)

                summary = (
                    f"Найдено: {found_total}, сохранено: {saved_total}, "
                    f"вступил: {joined_total}, пропущено: {skipped_total}"
                )
                self.db.set_state("discovery_last_summary", summary)
                self.db.set_state("discovery_last_finish", now_iso())
                self.db.set_state("discovery_running", "false")

                if settings.discovery_notify_summary:
                    await self.notifier.send_admins(
                        "✅ <b>Автопоиск групп завершен</b>\n\n"
                        f"Найдено: <b>{found_total}</b>\n"
                        f"Сохранено в базу: <b>{saved_total}</b>\n"
                        f"Вступил в группы: <b>{joined_total}</b>\n"
                        f"Пропущено: <b>{skipped_total}</b>"
                    )

                return summary

            finally:
                self.db.set_state("discovery_running", "false")

    async def search_query(self, query: str):
        client = self.listener.client
        assert client is not None

        logger.info("Discovery search query: %s", query)

        result = await client(SearchRequest(
            q=query,
            limit=settings.auto_discovery_limit_per_query,
        ))

        found = 0
        saved = 0
        joined = 0
        skipped = 0

        for chat in result.chats:
            found += 1

            title = getattr(chat, "title", "") or ""
            username = getattr(chat, "username", None)
            participants_count = getattr(chat, "participants_count", None) or 0

            is_channel = isinstance(chat, Channel)
            is_megagroup = getattr(chat, "megagroup", False)

            if not is_channel or not is_megagroup:
                skipped += 1
                continue

            if participants_count and participants_count < settings.min_group_members:
                skipped += 1
                continue

            if not is_valid_group(title=title, username=username):
                skipped += 1
                continue

            self.db.upsert_group({
                "chat_id": getattr(chat, "id", None),
                "title": title,
                "username": username,
                "members_count": participants_count,
                "source_query": query,
                "status": "found",
                "joined": False,
            })
            saved += 1

            if settings.auto_join_public_groups and username:
                did_join = await self.try_join(chat)
                if did_join:
                    joined += 1
                    self.db.upsert_group({
                        "chat_id": getattr(chat, "id", None),
                        "title": title,
                        "username": username,
                        "members_count": participants_count,
                        "source_query": query,
                        "status": "joined",
                        "joined": True,
                    })

        return found, saved, joined, skipped

    async def try_join(self, chat) -> bool:
        client = self.listener.client
        assert client is not None

        joined_count = self.db.count_auto_joins_today()
        if joined_count >= settings.max_auto_joins_per_day:
            return False

        try:
            await client(JoinChannelRequest(chat))
            await asyncio.sleep(3)
            return True

        except UserAlreadyParticipantError:
            return True

        except FloodWaitError:
            raise

        except Exception as e:
            logger.warning("Failed to join group %s: %s", getattr(chat, "title", ""), e)
            return False

    async def run_manual(self):
        return await self.run_cycle(reason="manual")

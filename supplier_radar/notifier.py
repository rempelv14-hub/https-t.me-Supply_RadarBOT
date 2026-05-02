import html
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

logger = logging.getLogger(__name__)


class Notifier:
    def __init__(self, bot_token: str, admin_ids: list[int]):
        self.bot_token = bot_token
        self.admin_ids = admin_ids
        self.bot = Bot(
            token=bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

    async def send_admins(self, text: str, reply_markup=None):
        for admin_id in self.admin_ids:
            try:
                await self.bot.send_message(
                    admin_id,
                    text,
                    reply_markup=reply_markup,
                    disable_web_page_preview=True,
                )
            except Exception as e:
                logger.warning("Failed to notify admin %s: %s", admin_id, e)

    async def close(self):
        await self.bot.session.close()


def h(value) -> str:
    return html.escape(str(value or ""))

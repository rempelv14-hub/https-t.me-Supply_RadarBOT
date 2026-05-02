import asyncio
import logging
import os

from supplier_radar.admin_bot import run_admin_bot
from supplier_radar.database import Database
from supplier_radar.discovery import DiscoveryManager
from supplier_radar.health import run_health_server
from supplier_radar.notifier import Notifier
from supplier_radar.telegram_listener import TelegramLeadListener
from supplier_radar.runtime_config import settings


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    db = Database(settings.db_path)
    db.init()

    notifier = Notifier(settings.bot_token, settings.admin_ids)

    listener = TelegramLeadListener(db=db, notifier=notifier)

    discovery = DiscoveryManager(
        db=db,
        notifier=notifier,
        listener=listener,
    )

    tasks = [
        asyncio.create_task(run_health_server(settings.port)),
        asyncio.create_task(listener.start()),
        asyncio.create_task(discovery.start_scheduler()),
        asyncio.create_task(run_admin_bot(db=db, discovery=discovery, listener=listener)),
    ]

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")

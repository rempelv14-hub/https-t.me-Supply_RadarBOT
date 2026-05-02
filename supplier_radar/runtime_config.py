import os
from pathlib import Path

import config as local_config


def _env(name: str, default):
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return int(value)


def _env_admin_ids(default_ids):
    raw = os.getenv("ADMIN_IDS")
    if raw:
        return [int(x.strip()) for x in raw.split(",") if x.strip()]
    return list(default_ids)


class Settings:
    bot_token: str = _env("BOT_TOKEN", local_config.BOT_TOKEN)
    admin_ids = _env_admin_ids(local_config.ADMIN_IDS)

    api_id: int = _env_int("API_ID", int(local_config.API_ID))
    api_hash: str = _env("API_HASH", local_config.API_HASH)
    session_string: str = _env("SESSION_STRING", local_config.SESSION_STRING)

    data_dir: str = _env("DATA_DIR", local_config.DATA_DIR)
    db_path: Path = Path(data_dir) / "supplier_radar.sqlite3"

    min_score: int = _env_int("MIN_SCORE", local_config.MIN_SCORE)
    scan_existing_dialogs: bool = _env_bool("SCAN_EXISTING_DIALOGS", local_config.SCAN_EXISTING_DIALOGS)
    recent_scan_limit: int = _env_int("RECENT_SCAN_LIMIT", local_config.RECENT_SCAN_LIMIT)

    auto_discovery_enabled: bool = _env_bool("AUTO_DISCOVERY_ENABLED", local_config.AUTO_DISCOVERY_ENABLED)
    auto_discovery_start_delay_seconds: int = _env_int(
        "AUTO_DISCOVERY_START_DELAY_SECONDS",
        local_config.AUTO_DISCOVERY_START_DELAY_SECONDS,
    )
    auto_discovery_interval_hours: int = _env_int(
        "AUTO_DISCOVERY_INTERVAL_HOURS",
        local_config.AUTO_DISCOVERY_INTERVAL_HOURS,
    )
    auto_discovery_limit_per_query: int = _env_int(
        "AUTO_DISCOVERY_LIMIT_PER_QUERY",
        local_config.AUTO_DISCOVERY_LIMIT_PER_QUERY,
    )
    auto_join_public_groups: bool = _env_bool("AUTO_JOIN_PUBLIC_GROUPS", local_config.AUTO_JOIN_PUBLIC_GROUPS)
    max_auto_joins_per_day: int = _env_int("MAX_AUTO_JOINS_PER_DAY", local_config.MAX_AUTO_JOINS_PER_DAY)
    min_group_members: int = _env_int("MIN_GROUP_MEMBERS", local_config.MIN_GROUP_MEMBERS)
    only_valid_groups: bool = _env_bool("ONLY_VALID_GROUPS", local_config.ONLY_VALID_GROUPS)
    floodwait_extra_seconds: int = _env_int("FLOODWAIT_EXTRA_SECONDS", local_config.FLOODWAIT_EXTRA_SECONDS)

    discovery_notify_start: bool = _env_bool("DISCOVERY_NOTIFY_START", local_config.DISCOVERY_NOTIFY_START)
    discovery_notify_summary: bool = _env_bool("DISCOVERY_NOTIFY_SUMMARY", local_config.DISCOVERY_NOTIFY_SUMMARY)
    discovery_notify_floodwait: bool = _env_bool("DISCOVERY_NOTIFY_FLOODWAIT", local_config.DISCOVERY_NOTIFY_FLOODWAIT)
    discovery_notify_resume: bool = _env_bool("DISCOVERY_NOTIFY_RESUME", local_config.DISCOVERY_NOTIFY_RESUME)

    port: int = _env_int("PORT", local_config.PORT)


settings = Settings()
settings.db_path.parent.mkdir(parents=True, exist_ok=True)

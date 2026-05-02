# ==============================
# НАСТРОЙКИ БОТА
# ==============================
# Здесь нужно вставить только свои данные.
# Важно: кавычки оставляем там, где они уже стоят.

# 1) Токен бота из BotFather
BOT_TOKEN = "PASTE_BOT_TOKEN_HERE"

# 2) Твой Telegram ID. Можно узнать у @userinfobot
# Пример: ADMIN_IDS = [123456789]
ADMIN_IDS = [123456789]

# 3) API_ID и API_HASH с https://my.telegram.org/apps
API_ID = 12345678
API_HASH = "PASTE_API_HASH_HERE"

# 4) Сюда вставишь SESSION_STRING после запуска make_session.py
SESSION_STRING = ""

# ==============================
# ОСНОВНЫЕ НАСТРОЙКИ
# ==============================

DATA_DIR = "data"

# Минимальная оценка, чтобы сообщение считалось лидом
MIN_SCORE = 8

# Сканировать последние сообщения в уже подключенных группах при старте
SCAN_EXISTING_DIALOGS = True
RECENT_SCAN_LIMIT = 30

# ==============================
# АВТОПОИСК ГРУПП
# ==============================

AUTO_DISCOVERY_ENABLED = True

# Через сколько секунд после запуска начать первый автопоиск групп
AUTO_DISCOVERY_START_DELAY_SECONDS = 15

# Как часто запускать новый поиск групп, если нет FloodWait
AUTO_DISCOVERY_INTERVAL_HOURS = 12

# Сколько групп брать максимум на один поисковый запрос
AUTO_DISCOVERY_LIMIT_PER_QUERY = 5

# Вступать ли автоматически в публичные группы
# Лучше сначала False, чтобы не ловить лимиты Telegram.
AUTO_JOIN_PUBLIC_GROUPS = False

# Максимум авто-вступлений в группы за сутки
MAX_AUTO_JOINS_PER_DAY = 10

# Не брать слишком маленькие группы
MIN_GROUP_MEMBERS = 100

# Оставлять только похожие на нужную нишу группы
ONLY_VALID_GROUPS = True

# Дополнительная пауза после FloodWait, чтобы не запускаться в ту же секунду
FLOODWAIT_EXTRA_SECONDS = 60

# Уведомления админу
DISCOVERY_NOTIFY_START = True
DISCOVERY_NOTIFY_SUMMARY = True
DISCOVERY_NOTIFY_FLOODWAIT = True
DISCOVERY_NOTIFY_RESUME = True

# Порт для Railway. На компьютере можно не трогать.
PORT = 8080

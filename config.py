import os

# Токен бота (получить у @BotFather)
BOT_TOKEN = os.getenv("BOT_TOKEN", "ВСТАВЬ_СЮДА_ТОКЕН_БОТА")

# ID главного админа (твой ID)
MAIN_ADMIN_ID = 1780243264

# База данных
DB_PATH = "data/casino.db"

# Настройки казино
HOUSE_EDGE = 0.65  # 65% шанс проигрыша (казино всегда в плюсе)
MIN_BET = 1  # Минимальная ставка
DEFAULT_MIN_WITHDRAW = 10  # Минимальный вывод по умолчанию

# Контакты для пополнения
DEPOSIT_USERNAME = "@v1nk_molik"

# Ссылка на твоего сервер/кастомный клиент (если нужно)
CUSTOM_SERVER_URL = "http://67.211.221.152:8888"

import os
from dotenv import load_dotenv

load_dotenv()

# --- Основные настройки ---
# Добавьте .strip(), чтобы убрать невидимые пробелы
BOT_TOKEN = os.getenv("BOT_TOKEN", "8434887547:AAH6PGGTgTJTuJfzDgOGoMY8LCEQAdqJegE").strip()
ADMIN_IDS = [7544069555]
DB_NAME = "shop.db"
SUPPORT_LINK = "https://t.me/Nyawka_CuteUwU"

# --- API Telegram (для работы сессий) ---
API_ID = int(os.getenv("API_ID", "27720808"))
API_HASH = os.getenv("API_HASH", "f404d028ebe5d98725cd21ea5537d015")

# --- Платежные настройки ---
# CryptoBot
CRYPTOBOT_TOKEN = os.getenv("CRYPTOBOT_TOKEN", "523629:AAExhvNXQqXYrUzU4jmeQdUHB7yN4DapdJF")

# Прямой TON (Tonkeeper и др.)
# ЗАМЕНИ НА СВОЙ АДРЕС!
TON_ADDRESS = os.getenv("TON_ADDRESS", "UQATdKOx6zduWyIgo0ABWLxuI9T3SE7RpsG0scYsdC7UELE8") 
# API ключ можно взять бесплатно в @toncenter_bot (для mainnet)
TONCENTER_API_KEY = os.getenv("TONCENTER_API_KEY", "5188aec082604014b83c74f625c02796a216f46dcfccac7747f4c05545ddc8a3") 

# Курсы
STAR_RATE = 1.3  # 1 звезда = 1.3 рубля

TON_EXCHANGE_RATE = 160.0 # Примерный курс TON/RUB (лучше обновлять динамически)

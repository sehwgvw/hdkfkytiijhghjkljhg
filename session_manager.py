import os
import asyncio
import shutil
import zipfile
from telethon import TelegramClient
from config import API_ID, API_HASH

# Папка для хранения сессий
SESSIONS_DIR = "sessions_store"
TDATA_DIR = "tdata_store"

if not os.path.exists(SESSIONS_DIR):
    os.makedirs(SESSIONS_DIR)
if not os.path.exists(TDATA_DIR):
    os.makedirs(TDATA_DIR)

class SessionManager:
    @staticmethod
    async def get_phone_from_session(session_path):
        """Проверяет сессию и возвращает номер телефона."""
        client = TelegramClient(session_path, API_ID, API_HASH)
        phone = None
        try:
            await client.connect()
            if await client.is_user_authorized():
                me = await client.get_me()
                phone = f"+{me.phone}"
            await client.disconnect()
        except Exception as e:
            print(f"Error reading session: {e}")
        return phone

    @staticmethod
    async def get_latest_code(session_path):
        """Парсит код из системных сообщений Telegram."""
        client = TelegramClient(session_path, API_ID, API_HASH)
        result_code = None
        try:
            await client.connect()
            if not await client.is_user_authorized():
                return "❌ Сессия неавторизована."

            found = False
            async for message in client.iter_messages(777000, limit=10):
                if message.message and any(x in message.message for x in ["Login code", "Код"]):
                    import re
                    match = re.search(r'\b(\d{5})\b', message.message)
                    if match:
                        result_code = (f"🔔 <b>Ваш код:</b> <code>{match.group(1)}</code>\n"
                                     f"🕒 Получен: {message.date.strftime('%H:%M:%S')}")
                        found = True
                        break
            
            if not found:
                 result_code = "⏳ Код не найден. Отправьте код в приложении и нажмите 'Обновить'."
        except Exception as e:
            result_code = f"⚠️ Ошибка: {str(e)}"
        finally:
            await client.disconnect()
        return result_code

    @staticmethod
    def get_tdata_zip_path(session_path, item_id):
        """Создает ZIP архив с сессией (эмуляция TData)."""
        zip_path = os.path.join(TDATA_DIR, f"tdata_{item_id}.zip")
        
        # Если архива нет, создаем его
        if not os.path.exists(zip_path):
            with zipfile.ZipFile(zip_path, 'w') as zf:
                # В реальном софте тут идет конвертация, 
                # здесь мы кладем саму сессию для примера
                zf.write(session_path, os.path.basename(session_path))
        
        return zip_path
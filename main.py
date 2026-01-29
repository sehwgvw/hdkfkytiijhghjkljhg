import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from database import create_tables

# Импортируем роутеры
from admin_handlers import router as admin_router
from user_handlers import router as user_router

async def main():
    # Настройка логов
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    # Инициализация БД
    await create_tables()
    
    # Запуск бота
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрируем роутеры (админский первый, чтобы перехватывал команды)
    dp.include_router(admin_router)
    dp.include_router(user_router)
    
    try:
        logging.info("Bot started...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped.")
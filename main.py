import asyncio
import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode

from config import BOT_TOKEN, MAIN_ADMIN_ID
from database import db
from handlers import start, game, profile, admin, deposit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Web server dummy to keep Render Web Service port open
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

    def log_message(self, format, *args):
        pass  # Quiet HTTP logs

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"🌐 HTTP health check server running on port {port}")
    server.serve_forever()

async def main():
    # Запуск фонового веб-сервера для Render
    threading.Thread(target=run_web_server, daemon=True).start()

    # Проверяем токен
    if not BOT_TOKEN or BOT_TOKEN == "ВСТАВЬ_СЮДА_ТОКЕН_БОТА":
        logger.error("❌ Не указан токен бота! Установи BOT_TOKEN в переменных окружения")
        return

    # Добавляем главного админа
    db.add_user(MAIN_ADMIN_ID, "main_admin")
    db.add_admin(MAIN_ADMIN_ID)
    logger.info(f"✅ Главный админ {MAIN_ADMIN_ID} добавлен")

    bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем роутеры
    dp.include_router(start.router)
    dp.include_router(game.router)
    dp.include_router(profile.router)
    dp.include_router(deposit.router)
    dp.include_router(admin.router)

    logger.info("🤖 Бот запущен!")

    # Удаляем вебхук и запускаем polling
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

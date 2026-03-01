import asyncio
import sys
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database.db import init_db

from handlers.private import start, voyage, ship, shop, inventory, casino
from handlers.group import group_commands, group_voyage
from handlers.admin import admin_panel, lottery

import logging
logging.disable(logging.CRITICAL)

sys.stdout.reconfigure(line_buffering=True)


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Начать игру")
    ]
    await bot.set_my_commands(commands)


async def on_startup(bot: Bot):
    print("Бот запускается...")
    await bot.delete_webhook(drop_pending_updates=True)


async def on_shutdown(bot: Bot):
    print("Бот останавливается...")
    await bot.session.close()


async def main():
    print("Запуск бота...")

    if not config.BOT_TOKEN:
        print("BOT_TOKEN не найден в .env файле")
        return

    print("Инициализация базы данных...")
    await init_db()
    print("База данных готова")

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.include_router(lottery.router) 
    dp.include_router(start.router)
    dp.include_router(inventory.router)
    dp.include_router(voyage.router)
    dp.include_router(ship.router)
    dp.include_router(shop.router)
    
    dp.include_router(casino.router)

    dp.include_router(group_commands.router)
    dp.include_router(group_voyage.router)

    dp.include_router(admin_panel.router)
    
    await set_commands(bot)

    print("✅ Бот запущен и готов к работе")

    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен пользователем")
from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from app.config import Settings, get_settings
from app.handlers import admin, broadcasts, cabinet, community_moderation, photos, profile, referral, start, subscribers, subscription
from app.middlewares.db import DbSessionMiddleware


async def set_bot_commands(bot: Bot, settings: Settings) -> None:
    default_commands = [
        BotCommand(command="start", description="Запуск"),
        BotCommand(command="cabinet", description="Личный кабинет"),
        BotCommand(command="priglasil", description="Кто меня пригласил"),
    ]
    await bot.set_my_commands(default_commands, scope=BotCommandScopeDefault())

    admin_commands = [
        *default_commands,
        BotCommand(command="admin", description="Админ-панель"),
    ]
    for admin_id in settings.admin_ids:
        await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))


async def main() -> None:
    settings = get_settings()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    bot = Bot(token=settings.bot_token)
    storage = RedisStorage.from_url(settings.redis_url)
    dp = Dispatcher(storage=storage)

    dp.update.middleware.register(DbSessionMiddleware())

    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(cabinet.router)
    dp.include_router(subscription.router)
    dp.include_router(referral.router)
    dp.include_router(photos.router)
    dp.include_router(profile.router)
    dp.include_router(subscribers.router)
    dp.include_router(broadcasts.router)
    dp.include_router(community_moderation.router)

    await set_bot_commands(bot, settings)
    await bot.delete_webhook(drop_pending_updates=True)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await storage.close()


if __name__ == "__main__":
    asyncio.run(main())

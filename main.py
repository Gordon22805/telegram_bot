import asyncio
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from handlers.user_handlers import router as user_router
from handlers.admin_handlers import router as admin_router
from services.crypto_service import close_crypto
from utils.db import init_db

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# include routers
dp.include_router(user_router)
dp.include_router(admin_router)


async def main():
    try:
        init_db()
        print("Bot starting...")
        await dp.start_polling(bot)
    finally:
        # cleanup
        try:
            await close_crypto()
        except Exception:
            pass
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

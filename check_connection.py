
import asyncio

from aiogram import Bot
from config import Settings


async def main():
    settings = Settings.from_env()

    bot = Bot(token=settings.bot_token)

    try:
        me = await bot.get_me()

        print("Telegram connection successful!")
        print(f"Bot username: @{me.username}")
        print(f"Bot ID: {me.id}")

    except Exception as error:
        print("Telegram connection failed!")
        print(f"Error type: {type(error).__name__}")
        print(f"Error: {error}")

    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

"""
Основной файл для запуска бота
"""
import asyncio
import logging
import sys
from config.settings import settings

# Проверяем наличие токена
if not settings.BOT_TOKEN:
    print("❌ Ошибка: BOT_TOKEN не установлен!")
    print("Создайте файл .env и добавьте ваш токен бота:")
    print("BOT_TOKEN=your_bot_token_here")
    sys.exit(1)

# Проверяем наличие admin_user_id
if not settings.ADMIN_USER_ID:
    print("❌ Ошибка: ADMIN_USER_ID не установлен!")
    print("Добавьте в файл .env ваш Telegram ID:")
    print("ADMIN_USER_ID=123456789")
    sys.exit(1)

from main import GiveawayBot


def main():
    """Основная функция запуска"""
    print("🤖 Запуск Telegram бота для розыгрышей...")
    print(f"📊 Администратор: {settings.ADMIN_USER_ID}")

    bot = GiveawayBot()

    try:
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logging.error(f"Критическая ошибка при запуске бота: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Минимальный тестовый бот для проверки работоспособности
"""
import os
import asyncio
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Получаем настройки
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    logger.info(f"Команда /start от пользователя {user.id}")

    if user.id == ADMIN_USER_ID:
        await update.message.reply_text(
            f"🤖 Привет, {user.first_name}!\n\n"
            "Вы вошли как администратор.\n"
            "Бот работает корректно! ✅"
        )
    else:
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            "Добро пожаловать в бот для розыгрышей!\n"
            "Бот работает корректно! ✅"
        )


async def test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тестовая команда"""
    await update.message.reply_text("🧪 Тест пройден успешно!")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Ошибка: {context.error}")


async def main():
    """Основная функция"""
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не найден в .env файле!")
        return

    if not ADMIN_USER_ID:
        print("❌ ADMIN_USER_ID не найден в .env файле!")
        return

    print("🚀 Запуск минимального тестового бота...")
    print(f"👤 ID администратора: {ADMIN_USER_ID}")

    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()

    # Проверяем подключение
    try:
        bot_info = await application.bot.get_me()
        print(f"🤖 Подключение успешно: @{bot_info.username}")
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return

    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("test", test_command))
    application.add_error_handler(error_handler)

    # Запускаем бота
    print("🟢 Минимальный бот запущен! Нажмите Ctrl+C для остановки.")
    await application.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
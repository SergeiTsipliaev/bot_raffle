"""
Основной файл для запуска бота
"""
import logging
import sys
import os

# Добавляем текущую директорию в путь Python
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import settings

# Проверяем настройки
validation_errors = settings.validate()
if validation_errors:
    print("❌ Ошибки конфигурации:")
    for error in validation_errors:
        print(f"  • {error}")

    print("\n📝 Инструкция по настройке:")
    print("1. Создайте файл .env в корневой папке проекта")
    print("2. Добавьте следующие строки:")
    print("   BOT_TOKEN=ваш_токен_от_BotFather")
    print("   ADMIN_USER_ID=ваш_telegram_id")
    print("3. Получите ваш Telegram ID от бота @userinfobot")
    print("4. Получите токен бота от @BotFather")
    sys.exit(1)

# Импортируем main только после проверки настроек
try:
    from main import GiveawayBot
except ImportError as e:
    print(f"❌ Ошибка импорта: {e}")
    print("Попробуйте запустить минимальную версию: python minimal_bot.py")
    sys.exit(1)


def main():
    """Основная функция запуска"""
    print("🤖 Запуск Telegram бота для розыгрышей...")
    print(f"📊 Администратор: {settings.ADMIN_USER_ID}")

    # Создаем директории если их нет
    os.makedirs('logs', exist_ok=True)
    os.makedirs('media/giveaways', exist_ok=True)
    os.makedirs('media/prizes', exist_ok=True)

    # Настраиваем логирование в файл
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Создаем и запускаем бота
    bot = GiveawayBot()

    try:
        # Используем правильный способ запуска для избежания проблем с event loop
        import asyncio
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        # Проверяем, есть ли уже запущенный event loop
        try:
            loop = asyncio.get_running_loop()
            print("⚠️ Event loop уже запущен, используем текущий")
        except RuntimeError:
            # Event loop не запущен, создаем новый
            asyncio.run(bot.run())

    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
        logging.error(f"Критическая ошибка при запуске бота: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
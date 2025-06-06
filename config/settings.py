import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()


class Settings:
    # Основные настройки бота
    BOT_TOKEN = os.getenv('BOT_TOKEN')

    # Преобразуем ADMIN_USER_ID в int с проверкой
    admin_user_id_str = os.getenv('ADMIN_USER_ID', '0')
    try:
        ADMIN_USER_ID = int(admin_user_id_str)
    except (ValueError, TypeError):
        ADMIN_USER_ID = 0

    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///giveaway_bot.db')
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key_change_this')

    # Настройки бота
    MAX_GIVEAWAY_NAME_LENGTH = 80
    MAX_PARTICIPANTS_DEFAULT = 1000
    MAX_MEDIA_FILES = 10

    # Сообщения
    MESSAGES = {
        'welcome_admin': "🤖 Добро пожаловать, {name}!\n\nВы вошли как администратор.\nВыберите действие:",
        'welcome_user': "👋 Привет, {name}!\n\nДобро пожаловать в бот для розыгрышей!\nИщите активные конкурсы в каналах.",
        'giveaway_created': "✅ Розыгрыш '{name}' успешно создан!",
        'giveaway_published': "📢 Розыгрыш опубликован в канале!",
        'participation_success': "🎉 Вы успешно участвуете в розыгрыше!",
        'already_participating': "⚠️ Вы уже участвуете в этом розыгрыше!",
        'subscription_required': "❌ Для участия необходимо подписаться на каналы:",
        'winners_selected': "🏆 Победители выбраны!",
        'data_collection': "📝 Для получения приза заполните свои данные:",
    }

    # Эмодзи для кнопок
    EMOJIS = {
        'create': '🎯',
        'list': '📋',
        'participants': '👥',
        'winners': '🏆',
        'settings': '⚙️',
        'stats': '📊',
        'back': '🔙',
        'edit': '✏️',
        'delete': '🗑️',
        'publish': '📢',
        'play': '▶️',
        'stop': '⏹️',
        'refresh': '🔄',
        'export': '📤',
        'add': '➕',
        'remove': '➖',
    }

    @classmethod
    def validate(cls):
        """Проверка настроек"""
        errors = []

        if not cls.BOT_TOKEN:
            errors.append("BOT_TOKEN не установлен")

        if not cls.ADMIN_USER_ID or cls.ADMIN_USER_ID == 0:
            errors.append("ADMIN_USER_ID не установлен или некорректен")

        return errors


# Создаем экземпляр настроек
settings = Settings()
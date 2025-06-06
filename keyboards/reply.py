from telegram import ReplyKeyboardMarkup, KeyboardButton
from config.settings import settings

class ReplyKeyboards:
    @staticmethod
    def admin_main_menu():
        """Главное меню администратора"""
        keyboard = [
            [
                KeyboardButton(f"{settings.EMOJIS['create']} Создать розыгрыш"),
                KeyboardButton(f"{settings.EMOJIS['list']} Мои розыгрыши")
            ],
            [
                KeyboardButton(f"{settings.EMOJIS['participants']} Участники"),
                KeyboardButton(f"{settings.EMOJIS['winners']} Победители")
            ],
            [
                KeyboardButton(f"{settings.EMOJIS['settings']} Настройки"),
                KeyboardButton(f"{settings.EMOJIS['stats']} Статистика")
            ]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def user_main_menu():
        """Главное меню пользователя"""
        keyboard = [
            [KeyboardButton("🎯 Участвовать в розыгрышах")],
            [KeyboardButton("📋 Мои участия"), KeyboardButton("🏆 Мои победы")],
            [KeyboardButton("ℹ️ Помощь")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def cancel_menu():
        """Меню отмены"""
        keyboard = [[KeyboardButton("❌ Отмена")]]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def yes_no_menu():
        """Меню да/нет"""
        keyboard = [
            [KeyboardButton("✅ Да"), KeyboardButton("❌ Нет")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    @staticmethod
    def contact_menu():
        """Меню для запроса контакта"""
        keyboard = [
            [KeyboardButton("📱 Поделиться номером", request_contact=True)],
            [KeyboardButton("❌ Отмена")]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

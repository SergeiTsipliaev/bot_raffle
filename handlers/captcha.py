from typing import List, Dict
import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config.settings import settings


class CaptchaHandler:
    """Обработчик системы капчи"""

    CAPTCHA_IMAGES = {
        'пончики': ['🍩', '🥖', '🍞', '🧁', '🍰', '🍩'],
        'животные': ['🐶', '🐱', '🐭', '🐰', '🦊', '🐶'],
        'фрукты': ['🍎', '🍌', '🍊', '🍇', '🍓', '🍎'],
        'транспорт': ['🚗', '✈️', '🚂', '🚲', '🛥️', '🚗'],
        'цветы': ['🌸', '🌼', '🌺', '🌻', '🌷', '🌸']
    }

    def __init__(self, db_manager):
        self.db = db_manager
        self.active_captchas = {}  # user_id: captcha_data

    async def generate_captcha(self, user_id: int, giveaway_id: str) -> Dict:
        """Генерация капчи для пользователя"""
        # Выбираем случайную категорию
        category = random.choice(list(self.CAPTCHA_IMAGES.keys()))
        images = self.CAPTCHA_IMAGES[category].copy()

        # Выбираем правильный ответ
        correct_image = images[0]  # Первый элемент - правильный

        # Перемешиваем для отображения
        random.shuffle(images)

        # Находим позицию правильного ответа
        correct_position = images.index(correct_image)

        captcha_data = {
            'giveaway_id': giveaway_id,
            'category': category,
            'images': images,
            'correct_position': correct_position,
            'attempts': 0,
            'max_attempts': 3
        }

        self.active_captchas[user_id] = captcha_data

        return captcha_data

    def create_captcha_keyboard(self, images: List[str], captcha_id: str) -> InlineKeyboardMarkup:
        """Создание клавиатуры для капчи"""
        keyboard = []
        row = []

        for i, image in enumerate(images):
            row.append(InlineKeyboardButton(
                image,
                callback_data=f"captcha_{captcha_id}_{i}"
            ))

            if len(row) == 3:  # 3 изображения в ряд
                keyboard.append(row)
                row = []

        if row:  # Добавляем оставшиеся изображения
            keyboard.append(row)

        return InlineKeyboardMarkup(keyboard)

    async def show_captcha(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                           user_id: int, giveaway_id: str):
        """Показ капчи пользователю"""
        captcha_data = await self.generate_captcha(user_id, giveaway_id)

        category = captcha_data['category']
        images = captcha_data['images']

        keyboard = self.create_captcha_keyboard(images, f"{user_id}_{giveaway_id}")

        text = (
            f"🛡️ **Защита от ботов**\n\n"
            f"Для участия в розыгрыше необходимо пройти проверку.\n\n"
            f"Выберите все изображения с **{category}**:"
        )

        await update.callback_query.edit_message_text(
            text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )

    async def verify_captcha(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Проверка ответа капчи"""
        callback_data = update.callback_query.data
        parts = callback_data.split('_')

        if len(parts) != 4 or parts[0] != 'captcha':
            return False

        user_id = int(parts[1])
        giveaway_id = parts[2]
        selected_position = int(parts[3])

        if user_id not in self.active_captchas:
            await update.callback_query.answer("❌ Сессия капчи истекла!", show_alert=True)
            return False

        captcha_data = self.active_captchas[user_id]
        correct_position = captcha_data['correct_position']

        if selected_position == correct_position:
            # Правильный ответ
            del self.active_captchas[user_id]
            await update.callback_query.answer("✅ Проверка пройдена!", show_alert=True)
            return True
        else:
            # Неправильный ответ
            captcha_data['attempts'] += 1

            if captcha_data['attempts'] >= captcha_data['max_attempts']:
                del self.active_captchas[user_id]
                await update.callback_query.answer(
                    "❌ Превышено количество попыток! Попробуйте позже.",
                    show_alert=True
                )
                return False
            else:
                remaining_attempts = captcha_data['max_attempts'] - captcha_data['attempts']
                await update.callback_query.answer(
                    f"❌ Неправильно! Осталось попыток: {remaining_attempts}",
                    show_alert=True
                )
                return False
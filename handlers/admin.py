from datetime import datetime
import logging
import aiosqlite
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database.models import DatabaseManager
from keyboards.inline import InlineKeyboards
from keyboards.reply import ReplyKeyboards
from config.settings import settings

logger = logging.getLogger(__name__)

# Состояния для создания розыгрыша
GIVEAWAY_NAME, GIVEAWAY_DESCRIPTION, GIVEAWAY_SETTINGS = range(3)


class AdminHandlers:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def admin_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Стартовое меню для администратора"""
        user = update.effective_user

        welcome_text = settings.MESSAGES['welcome_admin'].format(name=user.first_name)
        keyboard = InlineKeyboards.admin_main_menu()

        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    welcome_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    welcome_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
        except Exception as e:
            logger.error(f"Ошибка в admin_start: {e}")
            if update.callback_query:
                await update.callback_query.message.reply_text(
                    welcome_text,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )

    async def my_giveaways(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список розыгрышей администратора"""
        try:
            giveaways = await self.db.get_giveaways_by_admin(update.effective_user.id)

            if not giveaways:
                keyboard = InlineKeyboards.admin_main_menu()
                await update.callback_query.edit_message_text(
                    "📋 **Мои розыгрыши**\n\n"
                    "У вас пока нет созданных розыгрышей.\n"
                    "Создайте первый розыгрыш!",
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
                return

            # Показываем первый розыгрыш
            context.user_data['giveaways_list'] = giveaways
            context.user_data['current_giveaway_index'] = 0

            await self.show_giveaway_details(update, context, 0)
        except Exception as e:
            logger.error(f"Ошибка в my_giveaways: {e}")
            await update.callback_query.edit_message_text(
                "❌ Произошла ошибка при загрузке розыгрышей."
            )

    async def show_giveaway_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, index: int):
        """Показать детали розыгрыша"""
        try:
            giveaways = context.user_data.get('giveaways_list', [])

            if not giveaways or index >= len(giveaways):
                return

            giveaway = giveaways[index]
            participants_count = await self.db.get_participants_count(giveaway['id'])

            # Формируем информацию о розыгрыше
            info_text = await self.format_giveaway_info_local(giveaway, participants_count)

            # Клавиатура управления
            management_keyboard = InlineKeyboards.giveaway_management(
                giveaway['id'],
                giveaway['status']
            )

            # Навигация
            if len(giveaways) > 1:
                nav_keyboard = InlineKeyboards.giveaway_navigation(
                    index,
                    len(giveaways),
                    "giveaway"
                )
                # Объединяем клавиатуры
                combined_keyboard = management_keyboard.inline_keyboard + nav_keyboard.inline_keyboard
                management_keyboard.inline_keyboard = combined_keyboard

            await update.callback_query.edit_message_text(
                info_text,
                reply_markup=management_keyboard,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка в show_giveaway_details: {e}")

    async def format_giveaway_info_local(self, giveaway: dict, participants_count: int) -> str:
        """Локальное форматирование информации о розыгрыше"""
        status_emoji = {
            'created': '🔧',
            'published': '📢',
            'finished': '🏁'
        }

        status_text = {
            'created': 'Создан',
            'published': 'Опубликован',
            'finished': 'Завершен'
        }

        status = giveaway.get('status', 'created')

        text = f"📋 **Информация о розыгрыше**\n\n"
        text += f"**Название:** {giveaway['name']}\n"
        text += f"**Статус:** {status_emoji.get(status, '❓')} {status_text.get(status, 'Неизвестен')}\n"
        text += f"**ID:** `{giveaway['id']}`\n"

        max_participants = giveaway.get('max_participants', 0)
        if max_participants > 0:
            text += f"**Участники:** {participants_count} из {max_participants}\n"
        else:
            text += f"**Участники:** {participants_count} из ∞\n"

        text += f"**Призовых мест:** {giveaway.get('prizes_count', 1)}\n"

        if giveaway.get('description'):
            text += f"**Описание:** {giveaway['description']}\n"

        if giveaway.get('referral_enabled'):
            text += f"**Реферальная система:** ✅ Включена\n"

        if giveaway.get('captcha_enabled'):
            text += f"**Защита от ботов:** ✅ Включена\n"

        # Безопасная обработка даты
        try:
            created_at_str = giveaway['created_at']
            if created_at_str:
                # Простая обработка даты
                text += f"**Создан:** {created_at_str[:16]}\n"
        except (ValueError, KeyError):
            text += f"**Создан:** -\n"

        return text

    async def navigate_giveaways(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Навигация по розыгрышам"""
        try:
            callback_data = update.callback_query.data
            new_index = int(callback_data.split('_')[-1])

            context.user_data['current_giveaway_index'] = new_index
            await self.show_giveaway_details(update, context, new_index)
        except Exception as e:
            logger.error(f"Ошибка в navigate_giveaways: {e}")

    async def manage_giveaway(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Управление конкретным розыгрышем"""
        try:
            callback_data = update.callback_query.data
            giveaway_id = callback_data.split('_')[1]

            giveaway = await self.db.get_giveaway(giveaway_id)
            if not giveaway:
                await update.callback_query.edit_message_text("❌ Розыгрыш не найден!")
                return

            participants_count = await self.db.get_participants_count(giveaway_id)
            info_text = await self.format_giveaway_info_local(giveaway, participants_count)

            keyboard = InlineKeyboards.giveaway_management(giveaway_id, giveaway['status'])

            await update.callback_query.edit_message_text(
                info_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка в manage_giveaway: {e}")

    async def publish_giveaway(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Меню публикации розыгрыша"""
        try:
            callback_data = update.callback_query.data
            giveaway_id = callback_data.split('_')[1]

            keyboard = InlineKeyboards.publish_options(giveaway_id)

            await update.callback_query.edit_message_text(
                "📢 **Публикация розыгрыша**\n\n"
                "Выберите способ публикации:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка в publish_giveaway: {e}")

    async def instant_publish(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Мгновенная публикация"""
        try:
            callback_data = update.callback_query.data
            giveaway_id = callback_data.split('_')[2]

            # Обновляем статус в базе данных
            await self.db.update_giveaway(giveaway_id, {
                'status': 'published',
                'published_at': datetime.now().isoformat()
            })

            await update.callback_query.edit_message_text(
                "✅ Розыгрыш опубликован мгновенно!\n\n"
                "Участники могут теперь принимать участие."
            )
        except Exception as e:
            logger.error(f"Ошибка в instant_publish: {e}")
            await update.callback_query.edit_message_text(
                "❌ Произошла ошибка при публикации розыгрыша."
            )
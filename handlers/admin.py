from datetime import datetime
import logging
import aiosqlite
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from database.models import DatabaseManager
from keyboards.inline import InlineKeyboards
from keyboards.reply import ReplyKeyboards
from config.settings import settings
from utils.helpers import format_giveaway_info, generate_referral_link

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

    async def create_giveaway_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Начало создания розыгрыша"""
        # Убираем ответ на callback query - он уже обработан в main.py

        try:
            await update.callback_query.edit_message_text(
                "🎯 **Создание нового розыгрыша**\n\n"
                f"Введите название розыгрыша (максимум {settings.MAX_GIVEAWAY_NAME_LENGTH} символов):",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Ошибка в create_giveaway_start: {e}")
            await update.callback_query.message.reply_text(
                "🎯 **Создание нового розыгрыша**\n\n"
                f"Введите название розыгрыша (максимум {settings.MAX_GIVEAWAY_NAME_LENGTH} символов):",
                parse_mode='Markdown'
            )

        return GIVEAWAY_NAME

    async def receive_giveaway_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение названия розыгрыша"""
        name = update.message.text.strip()

        if len(name) > settings.MAX_GIVEAWAY_NAME_LENGTH:
            await update.message.reply_text(
                f"❌ Название слишком длинное! Максимум {settings.MAX_GIVEAWAY_NAME_LENGTH} символов."
            )
            return GIVEAWAY_NAME

        context.user_data['giveaway_name'] = name

        await update.message.reply_text(
            "📝 **Описание розыгрыша**\n\n"
            "Введите описание розыгрыша (необязательно).\n"
            "Отправьте /skip чтобы пропустить:",
            parse_mode='Markdown'
        )

        return GIVEAWAY_DESCRIPTION

    async def receive_giveaway_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Получение описания розыгрыша"""
        if update.message.text == '/skip':
            description = ""
        else:
            description = update.message.text.strip()

        context.user_data['giveaway_description'] = description

        try:
            # Создаем розыгрыш в базе данных
            giveaway_data = {
                'name': context.user_data['giveaway_name'],
                'description': description,
                'admin_id': update.effective_user.id
            }

            giveaway_id = await self.db.create_giveaway(giveaway_data)
            context.user_data['current_giveaway_id'] = giveaway_id

            success_message = settings.MESSAGES['giveaway_created'].format(
                name=context.user_data['giveaway_name']
            )

            keyboard = InlineKeyboards.giveaway_management(giveaway_id)

            await update.message.reply_text(
                f"✅ {success_message}\n\n"
                f"**ID розыгрыша:** `{giveaway_id}`\n\n"
                "Выберите действие для настройки:",
                reply_markup=keyboard,
                parse_mode='Markdown'
            )

        except Exception as e:
            logger.error(f"Ошибка создания розыгрыша: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при создании розыгрыша. Попробуйте позже."
            )

        return ConversationHandler.END

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

            info_text = await format_giveaway_info(giveaway, participants_count)

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
            info_text = await format_giveaway_info(giveaway, participants_count)

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
            async with aiosqlite.connect(self.db.db_path) as db:
                await db.execute(
                    'UPDATE giveaways SET status = ?, published_at = ? WHERE id = ?',
                    ('published', datetime.now().isoformat(), giveaway_id)
                )
                await db.commit()

            await update.callback_query.edit_message_text(
                "✅ Розыгрыш опубликован мгновенно!\n\n"
                "Участники могут теперь принимать участие."
            )
        except Exception as e:
            logger.error(f"Ошибка в instant_publish: {e}")
            await update.callback_query.edit_message_text(
                "❌ Произошла ошибка при публикации розыгрыша."
            )
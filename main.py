import logging
import asyncio
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler
from telegram.ext import filters
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from config.settings import settings
from database.models import DatabaseManager
from handlers.admin import AdminHandlers, GIVEAWAY_NAME, GIVEAWAY_DESCRIPTION
from handlers.user import UserHandlers
from handlers.giveaway import GiveawayHandlers
from handlers.captcha import CaptchaHandler
from handlers.export import ExportHandler
from handlers.media import MediaHandler
from utils.helpers import parse_referral_link

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


class GiveawayBot:
    def __init__(self):
        self.token = settings.BOT_TOKEN
        self.db = DatabaseManager()
        self.admin_handlers = AdminHandlers(self.db)
        self.user_handlers = UserHandlers(self.db)
        self.giveaway_handlers = GiveawayHandlers(self.db)
        self.captcha_handler = CaptchaHandler(self.db)
        self.export_handler = ExportHandler(self.db)
        self.media_handler = MediaHandler(self.db)

    async def start_command(self, update, context):
        """Обработчик команды /start"""
        try:
            user = update.effective_user
            logger.info(f"Пользователь {user.id} (@{user.username}) запустил бота")

            # Добавляем пользователя в базу данных
            await self.db.add_user({
                'user_id': user.id,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'language_code': user.language_code
            })

            # Обрабатываем реферальную ссылку
            if context.args:
                start_param = context.args[0]
                referral_data = parse_referral_link(start_param)
                if referral_data:
                    context.user_data['referred_by'] = referral_data['referrer_id']

            # Проверяем, является ли пользователь администратором
            is_admin = await self.db.is_admin(user.id)
            logger.info(f"Пользователь {user.id} - администратор: {is_admin}")

            if is_admin:
                await self.admin_handlers.admin_start(update, context)
            else:
                await self.user_handlers.user_start(update, context)

        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
            await update.message.reply_text("❌ Произошла ошибка при запуске. Попробуйте позже.")

    async def callback_query_handler(self, update, context):
        """Обработчик callback запросов"""
        try:
            query = update.callback_query
            data = query.data
            user_id = update.effective_user.id

            logger.info(f"Callback от пользователя {user_id}: {data}")

            # Проверяем права администратора для admin команд
            admin_commands = [
                'create_giveaway', 'my_giveaways', 'manage_', 'edit_',
                'publish_', 'delete_', 'draw_', 'settings', 'statistics',
                'export_', 'channels_', 'protection_', 'schedule_',
                'advanced_', 'participants_', 'winners_', 'redraw_'
            ]

            is_admin_command = any(data.startswith(cmd) for cmd in admin_commands)

            if is_admin_command:
                is_admin = await self.db.is_admin(user_id)
                if not is_admin:
                    await query.answer("❌ У вас нет прав администратора!", show_alert=True)
                    return

            # Отвечаем на callback query
            await query.answer()

            # Маршрутизация callback запросов
            if data == 'admin_menu':
                await self.admin_handlers.admin_start(update, context)
            elif data == 'my_giveaways':
                await self.admin_handlers.my_giveaways(update, context)
            elif data.startswith('giveaway_nav_'):
                await self.admin_handlers.navigate_giveaways(update, context)
            elif data.startswith('manage_'):
                await self.admin_handlers.manage_giveaway(update, context)
            elif data.startswith('publish_'):
                await self.admin_handlers.publish_giveaway(update, context)
            elif data.startswith('publish_instant_'):
                await self.admin_handlers.instant_publish(update, context)
            elif data.startswith('participate_'):
                await self.user_handlers.participate_in_giveaway(update, context)
            elif data.startswith('draw_'):
                await self.giveaway_handlers.draw_winners(update, context)
            elif data.startswith('captcha_'):
                success = await self.captcha_handler.verify_captcha(update, context)
                if success:
                    # Продолжаем процесс участия после успешной капчи
                    callback_data = update.callback_query.data
                    parts = callback_data.split('_')
                    if len(parts) >= 3:
                        giveaway_id = parts[2]
                        giveaway = await self.db.get_giveaway(giveaway_id)
                        if giveaway:
                            await self.user_handlers._add_participant_to_giveaway(
                                update, context, giveaway_id, giveaway
                            )
            elif data.startswith('export_'):
                await self.export_handler.export_participants_csv(update, context)
            elif data == 'statistics':
                await self.export_handler.export_statistics_json(update, context)
            else:
                await query.edit_message_text("🔧 Функция в разработке")

        except Exception as e:
            logger.error(f"Ошибка в callback_query_handler: {e}")
            try:
                if update.callback_query:
                    await update.callback_query.edit_message_text("❌ Произошла ошибка. Попробуйте позже.")
            except:
                pass

    async def text_message_handler(self, update, context):
        """Обработчик текстовых сообщений"""
        try:
            text = update.message.text
            user_id = update.effective_user.id

            logger.info(f"Текстовое сообщение от {user_id}: {text}")

            is_admin = await self.db.is_admin(user_id)

            if is_admin:
                if text == f"{settings.EMOJIS['create']} Создать розыгрыш":
                    keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton("🎯 Создать розыгрыш", callback_data="create_giveaway")
                    ]])

                    await update.message.reply_text(
                        "🎯 **Создание розыгрыша**\n\nВыберите действие:",
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                elif text == f"{settings.EMOJIS['list']} Мои розыгрыши":
                    keyboard = InlineKeyboardMarkup([[
                        InlineKeyboardButton("📋 Мои розыгрыши", callback_data="my_giveaways")
                    ]])

                    await update.message.reply_text(
                        "📋 **Мои розыгрыши**\n\nВыберите действие:",
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
                else:
                    await update.message.reply_text(
                        "🤖 Используйте кнопки меню для навигации."
                    )
            else:
                if text == "📋 Мои участия":
                    await self.user_handlers.show_user_participations(update, context)
                elif text == "🏆 Мои победы":
                    await self.user_handlers.show_user_wins(update, context)
                else:
                    await update.message.reply_text(
                        "👋 Добро пожаловать! Для участия в розыгрышах найдите активные конкурсы в каналах."
                    )
        except Exception as e:
            logger.error(f"Ошибка в text_message_handler: {e}")
            await update.message.reply_text("❌ Произошла ошибка при обработке сообщения.")

    async def media_message_handler(self, update, context):
        """Обработчик медиа сообщений"""
        try:
            user_id = update.effective_user.id
            is_admin = await self.db.is_admin(user_id)

            logger.info(f"Медиа сообщение от {user_id}, админ: {is_admin}")

            if is_admin:
                await self.media_handler.process_forwarded_message(update, context)
            else:
                await update.message.reply_text(
                    "👋 Добро пожаловать! Для участия в розыгрышах найдите активные конкурсы в каналах."
                )
        except Exception as e:
            logger.error(f"Ошибка в media_message_handler: {e}")

    def setup_handlers(self, application):
        """Настройка обработчиков"""
        logger.info("Настройка обработчиков...")

        # Conversation handler для создания розыгрыша
        create_giveaway_conv = ConversationHandler(
            entry_points=[CallbackQueryHandler(
                self.admin_handlers.create_giveaway_start,
                pattern='^create_giveaway$'
            )],
            states={
                GIVEAWAY_NAME: [MessageHandler(
                    filters.TEXT & ~filters.COMMAND,
                    self.admin_handlers.receive_giveaway_name
                )],
                GIVEAWAY_DESCRIPTION: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.admin_handlers.receive_giveaway_description
                    ),
                    CommandHandler('skip', self.admin_handlers.receive_giveaway_description)
                ]
            },
            fallbacks=[CommandHandler('cancel', self.cancel_conversation)]
        )

        # Основные обработчики
        application.add_handler(CommandHandler('start', self.start_command))
        application.add_handler(create_giveaway_conv)
        application.add_handler(CallbackQueryHandler(self.callback_query_handler))

        # Обработчик медиа файлов (только фото и видео, без DOCUMENT)
        application.add_handler(MessageHandler(
            filters.PHOTO | filters.VIDEO,
            self.media_message_handler
        ))

        # Обработчик текстовых сообщений (должен быть последним)
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.text_message_handler
        ))

        logger.info("Обработчики настроены успешно")

    async def cancel_conversation(self, update, context):
        """Отмена разговора"""
        await update.message.reply_text("❌ Операция отменена.")
        return ConversationHandler.END

    async def error_handler(self, update, context):
        """Обработка ошибок"""
        logger.error(f"Update {update} caused error {context.error}")

        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ Произошла ошибка. Попробуйте позже или обратитесь к администратору."
                )
            except:
                pass

    async def run(self):
        """Запуск бота"""
        try:
            logger.info("🚀 Запуск бота для розыгрышей...")
            logger.info(f"📊 Токен бота: {self.token[:10]}...")
            logger.info(f"👤 ID администратора: {settings.ADMIN_USER_ID}")

            logger.info("Инициализация базы данных...")
            await self.db.init_database()
            logger.info("✅ База данных инициализирована успешно")

            # Создание приложения
            application = Application.builder().token(self.token).build()

            # Проверяем подключение к боту
            bot_info = await application.bot.get_me()
            logger.info(f"🤖 Подключение к боту успешно: @{bot_info.username}")

            # Настройка обработчиков
            self.setup_handlers(application)

            # Обработчик ошибок
            application.add_error_handler(self.error_handler)

            # Запуск бота
            logger.info("🟢 Бот запущен и готов к работе!")
            await application.run_polling(drop_pending_updates=True)

        except Exception as e:
            logger.error(f"❌ Критическая ошибка при запуске: {e}")
            raise


if __name__ == '__main__':
    bot = GiveawayBot()
    asyncio.run(bot.run())
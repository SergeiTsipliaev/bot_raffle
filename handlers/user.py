import json
from typing import List, Dict
from utils.helpers import generate_referral_link
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.models import DatabaseManager
from keyboards.inline import InlineKeyboards
from keyboards.reply import ReplyKeyboards
from config.settings import settings
from utils.helpers import check_channel_subscription

logger = logging.getLogger(__name__)


class UserHandlers:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def user_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Стартовое меню для обычного пользователя"""
        user = update.effective_user

        # Добавляем пользователя в базу данных
        await self.db.add_user({
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'language_code': user.language_code
        })

        welcome_text = settings.MESSAGES['welcome_user'].format(name=user.first_name)
        keyboard = ReplyKeyboards.user_main_menu()

        await update.message.reply_text(
            welcome_text,
            reply_markup=keyboard
        )

    async def participate_in_giveaway(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Участие в розыгрыше"""
        await update.callback_query.answer()

        callback_data = update.callback_query.data
        giveaway_id = callback_data.split('_')[1]
        user = update.effective_user

        # Проверяем, существует ли розыгрыш
        giveaway = await self.db.get_giveaway(giveaway_id)
        if not giveaway:
            await update.callback_query.edit_message_text("❌ Розыгрыш не найден!")
            return

        # Проверяем статус розыгрыша
        if giveaway['status'] != 'published':
            await update.callback_query.edit_message_text("❌ Розыгрыш не активен!")
            return

        # Проверяем, не участвует ли уже пользователь
        is_participating = await self.db.is_participating(giveaway_id, user.id)
        if is_participating:
            await update.callback_query.edit_message_text(
                settings.MESSAGES['already_participating']
            )
            return

        # Проверяем подписки на каналы
        required_channels = giveaway.get('required_channels')
        if required_channels:
            channels_list = json.loads(required_channels)
            subscription_check = await self.check_subscriptions(
                user.id, channels_list, context.bot
            )

            if not subscription_check['all_subscribed']:
                unsubscribed_channels = subscription_check['unsubscribed']
                channels_text = '\n'.join([f"• @{ch}" for ch in unsubscribed_channels])

                await update.callback_query.edit_message_text(
                    f"{settings.MESSAGES['subscription_required']}\n\n{channels_text}\n\n"
                    "После подписки нажмите кнопку снова."
                )
                return

        # Проверяем капчу если включена
        if giveaway.get('captcha_enabled'):
            # Здесь будет логика капчи
            pass

        # Добавляем участника
        user_data = {
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        }

        # Проверяем реферальную ссылку
        referred_by = context.user_data.get('referred_by')

        success = await self.db.add_participant(giveaway_id, user_data, referred_by)

        if success:
            participants_count = await self.db.get_participants_count(giveaway_id)

            # Обновляем кнопку с новым количеством участников
            keyboard = InlineKeyboards.participation_button(
                giveaway_id,
                participants_count,
                giveaway.get('show_participants_count', True),
                giveaway.get('button_text', 'Участвовать')
            )

            await update.callback_query.edit_message_reply_markup(reply_markup=keyboard)

            # Отправляем подтверждение
            await context.bot.send_message(
                user.id,
                f"🎉 {settings.MESSAGES['participation_success']}\n\n"
                f"**Розыгрыш:** {giveaway['name']}\n"
                f"**Ваш номер участника:** #{participants_count}",
                parse_mode='Markdown'
            )

            # Если включена реферальная система, отправляем ссылку
            if giveaway.get('referral_enabled'):
                referral_link = generate_referral_link(context.bot.username, giveaway_id, user.id)
                await context.bot.send_message(
                    user.id,
                    f"🔗 **Пригласите друзей и увеличьте шансы на победу!**\n\n"
                    f"Ваша реферальная ссылка:\n`{referral_link}`\n\n"
                    f"За каждого приглашенного друга ваши шансы увеличиваются в {giveaway.get('referral_multiplier', 1.5)} раза!",
                    parse_mode='Markdown'
                )
        else:
            await update.callback_query.edit_message_text(
                "❌ Ошибка при регистрации участия. Попробуйте позже."
            )

    async def check_subscriptions(self, user_id: int, channels: List[str], bot) -> Dict:
        """Проверка подписок пользователя на каналы"""
        all_subscribed = True
        unsubscribed = []

        for channel in channels:
            try:
                member = await bot.get_chat_member(channel, user_id)
                if member.status in ['left', 'kicked']:
                    all_subscribed = False
                    unsubscribed.append(channel)
            except Exception as e:
                logger.error(f"Error checking subscription for {channel}: {e}")
                all_subscribed = False
                unsubscribed.append(channel)

        return {
            'all_subscribed': all_subscribed,
            'unsubscribed': unsubscribed
        }
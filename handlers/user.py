import json
from typing import List, Dict
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database.models import DatabaseManager
from keyboards.inline import InlineKeyboards
from keyboards.reply import ReplyKeyboards
from config.settings import settings

logger = logging.getLogger(__name__)

def generate_referral_link(bot_username: str, giveaway_id: str, user_id: int) -> str:
    """Генерация реферальной ссылки (локальная версия)"""
    return f"https://t.me/{bot_username}?start=ref_{giveaway_id}_{user_id}"


class UserHandlers:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    async def user_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Стартовое меню для обычного пользователя"""
        user = update.effective_user

        try:
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
        except Exception as e:
            logger.error(f"Ошибка в user_start: {e}")
            await update.message.reply_text(
                "❌ Произошла ошибка при инициализации. Попробуйте позже."
            )

    async def participate_in_giveaway(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Участие в розыгрыше"""
        try:
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

            # Проверяем лимит участников
            max_participants = giveaway.get('max_participants', 0)
            if max_participants > 0:
                current_count = await self.db.get_participants_count(giveaway_id)
                if current_count >= max_participants:
                    await update.callback_query.edit_message_text(
                        "❌ Достигнуто максимальное количество участников!"
                    )
                    return

            # Проверяем подписки на каналы
            required_channels = giveaway.get('required_channels')
            if required_channels:
                try:
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
                except (json.JSONDecodeError, TypeError):
                    logger.error(f"Ошибка парсинга каналов для розыгрыша {giveaway_id}")

            # Проверяем капчу если включена
            if giveaway.get('captcha_enabled'):
                # Показываем капчу
                from handlers.captcha import CaptchaHandler
                captcha_handler = CaptchaHandler(self.db)
                await captcha_handler.show_captcha(update, context, user.id, giveaway_id)
                return

            # Добавляем участника
            await self._add_participant_to_giveaway(update, context, giveaway_id, giveaway)
        except Exception as e:
            logger.error(f"Ошибка в participate_in_giveaway: {e}")
            try:
                await update.callback_query.edit_message_text(
                    "❌ Произошла ошибка при регистрации участия. Попробуйте позже."
                )
            except:
                pass

    async def _add_participant_to_giveaway(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                           giveaway_id: str, giveaway: Dict):
        """Добавление участника в розыгрыш"""
        user = update.effective_user

        try:
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

                try:
                    await update.callback_query.edit_message_reply_markup(reply_markup=keyboard)
                except Exception as e:
                    logger.warning(f"Не удалось обновить кнопку: {e}")

                # Отправляем подтверждение
                confirmation_text = (
                    f"🎉 {settings.MESSAGES['participation_success']}\n\n"
                    f"**Розыгрыш:** {giveaway['name']}\n"
                    f"**Ваш номер участника:** #{participants_count}"
                )

                try:
                    await context.bot.send_message(
                        user.id,
                        confirmation_text,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"Не удалось отправить подтверждение участнику {user.id}: {e}")
                    # Показываем подтверждение через edit_message_text
                    try:
                        await update.callback_query.edit_message_text(
                            f"✅ Вы участвуете! Номер: #{participants_count}\n\n"
                            f"**Розыгрыш:** {giveaway['name']}"
                        )
                    except:
                        pass

                # Если включена реферальная система, отправляем ссылку
                if giveaway.get('referral_enabled'):
                    try:
                        bot_username = (await context.bot.get_me()).username
                        referral_link = generate_referral_link(bot_username, giveaway_id, user.id)

                        referral_text = (
                            f"🔗 **Пригласите друзей и увеличьте шансы на победу!**\n\n"
                            f"Ваша реферальная ссылка:\n`{referral_link}`\n\n"
                            f"За каждого приглашенного друга ваши шансы увеличиваются в "
                            f"{giveaway.get('referral_multiplier', 1.5)} раза!"
                        )

                        await context.bot.send_message(
                            user.id,
                            referral_text,
                            parse_mode='Markdown'
                        )
                    except Exception as e:
                        logger.warning(f"Не удалось отправить реферальную ссылку: {e}")
            else:
                await update.callback_query.edit_message_text(
                    "❌ Ошибка при регистрации участия. Попробуйте позже."
                )
        except Exception as e:
            logger.error(f"Ошибка в _add_participant_to_giveaway: {e}")
            try:
                await update.callback_query.edit_message_text(
                    "❌ Произошла ошибка при добавлении участника."
                )
            except:
                pass

    async def check_subscriptions(self, user_id: int, channels: List[str], bot) -> Dict:
        """Проверка подписок пользователя на каналы"""
        all_subscribed = True
        unsubscribed = []

        for channel in channels:
            try:
                # Убираем @ если есть
                channel_clean = channel.replace('@', '')

                member = await bot.get_chat_member(f"@{channel_clean}", user_id)
                if member.status in ['left', 'kicked']:
                    all_subscribed = False
                    unsubscribed.append(channel_clean)
            except Exception as e:
                logger.error(f"Error checking subscription for {channel}: {e}")
                all_subscribed = False
                unsubscribed.append(channel.replace('@', ''))

        return {
            'all_subscribed': all_subscribed,
            'unsubscribed': unsubscribed
        }

    async def show_user_participations(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать участия пользователя"""
        user_id = update.effective_user.id

        try:
            # Получаем участия пользователя
            import aiosqlite
            async with aiosqlite.connect(self.db.db_path) as db:
                cursor = await db.execute('''
                    SELECT g.name, g.status, p.joined_at, g.id
                    FROM participants p
                    JOIN giveaways g ON p.giveaway_id = g.id
                    WHERE p.user_id = ?
                    ORDER BY p.joined_at DESC
                    LIMIT 10
                ''', (user_id,))

                participations = await cursor.fetchall()

            if not participations:
                text = "📋 **Ваши участия**\n\nВы пока не участвуете ни в одном розыгрыше."
            else:
                text = "📋 **Ваши участия** (последние 10):\n\n"

                for i, (name, status, joined_at, giveaway_id) in enumerate(participations, 1):
                    status_emoji = {
                        'created': '🔧',
                        'published': '📢',
                        'finished': '🏁'
                    }

                    text += f"{i}. **{name}**\n"
                    text += f"   Статус: {status_emoji.get(status, '❓')} {status}\n"
                    text += f"   Участвую с: {joined_at[:16]}\n\n"

            await update.message.reply_text(text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Ошибка в show_user_participations: {e}")
            await update.message.reply_text("❌ Произошла ошибка при загрузке данных.")

    async def show_user_wins(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать победы пользователя"""
        user_id = update.effective_user.id

        try:
            # Получаем победы пользователя
            import aiosqlite
            async with aiosqlite.connect(self.db.db_path) as db:
                cursor = await db.execute('''
                    SELECT g.name, w.place, w.selected_at, w.data_collected, w.prize_sent
                    FROM winners w
                    JOIN giveaways g ON w.giveaway_id = g.id
                    WHERE w.user_id = ?
                    ORDER BY w.selected_at DESC
                ''', (user_id,))

                wins = await cursor.fetchall()

            if not wins:
                text = "🏆 **Ваши победы**\n\nВы пока не выигрывали ни в одном розыгрыше."
            else:
                text = "🏆 **Ваши победы**:\n\n"

                for i, (name, place, selected_at, data_collected, prize_sent) in enumerate(wins, 1):
                    text += f"{i}. **{name}**\n"
                    text += f"   Место: {place}\n"
                    text += f"   Дата: {selected_at[:16]}\n"

                    if prize_sent:
                        text += "   ✅ Приз отправлен\n"
                    elif data_collected:
                        text += "   📝 Данные собраны\n"
                    else:
                        text += "   ⏳ Ожидает данных\n"

                    text += "\n"

            await update.message.reply_text(text, parse_mode='Markdown')
        except Exception as e:
            logger.error(f"Ошибка в show_user_wins: {e}")
            await update.message.reply_text("❌ Произошла ошибка при загрузке данных.")
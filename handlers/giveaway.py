from typing import List, Dict
from database.queries import DatabaseQueries
import logging
import random
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from database.models import DatabaseManager
from config.settings import settings
from utils.helpers import format_winners_list

logger = logging.getLogger(__name__)


class GiveawayHandlers:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.queries = DatabaseQueries(db_manager)

    async def draw_winners(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Проведение розыгрыша и выбор победителей"""
        await update.callback_query.answer()

        callback_data = update.callback_query.data
        giveaway_id = callback_data.split('_')[1]

        giveaway = await self.db.get_giveaway(giveaway_id)
        if not giveaway:
            await update.callback_query.edit_message_text("❌ Розыгрыш не найден!")
            return

        # Получаем всех участников
        participants = await self.queries.get_participants(giveaway_id)

        if not participants:
            await update.callback_query.edit_message_text(
                "❌ Нет участников для проведения розыгрыша!"
            )
            return

        prizes_count = giveaway.get('prizes_count', 1)

        if len(participants) < prizes_count:
            await update.callback_query.edit_message_text(
                f"❌ Недостаточно участников! Нужно минимум {prizes_count} участников."
            )
            return

        # Создаем взвешенный список участников (с учетом рефералов)
        weighted_participants = []
        for participant in participants:
            weight = 1.0

            if giveaway.get('referral_enabled') and participant.get('referral_count', 0) > 0:
                multiplier = giveaway.get('referral_multiplier', 1.5)
                max_multiplier = giveaway.get('max_referral_multiplier', 5.0)

                weight = min(
                    1.0 + (participant['referral_count'] * (multiplier - 1.0)),
                    max_multiplier
                )

            # Добавляем участника в список с учетом веса
            for _ in range(int(weight * 100)):  # Умножаем на 100 для точности
                weighted_participants.append(participant)

        # Выбираем победителей
        winners = []
        used_participants = set()

        for place in range(prizes_count):
            available_participants = [
                p for p in weighted_participants
                if p['user_id'] not in used_participants
            ]

            if not available_participants:
                break

            winner = random.choice(available_participants)
            winners.append({
                'user_id': winner['user_id'],
                'username': winner.get('username'),
                'first_name': winner.get('first_name'),
                'place': place + 1
            })
            used_participants.add(winner['user_id'])

        # Сохраняем победителей в базу данных
        await self.queries.save_winners(giveaway_id, winners)

        # Обновляем статус розыгрыша
        await self.queries.update_giveaway_status(giveaway_id, 'finished')

        # Формируем сообщение о победителях
        winners_text = format_winners_list(winners)

        await update.callback_query.edit_message_text(
            f"🏆 **{settings.MESSAGES['winners_selected']}**\n\n"
            f"**Розыгрыш:** {giveaway['name']}\n"
            f"**Дата:** {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
            f"{winners_text}\n\n"
            "Победители будут уведомлены автоматически.",
            parse_mode='Markdown'
        )

        # Уведомляем победителей
        await self.notify_winners(giveaway_id, winners, context.bot)

    async def notify_winners(self, giveaway_id: str, winners: List[Dict], bot):
        """Уведомление победителей"""
        giveaway = await self.db.get_giveaway(giveaway_id)

        for winner in winners:
            try:
                message = (
                    f"🎉 **Поздравляем! Вы выиграли в розыгрыше!**\n\n"
                    f"**Розыгрыш:** {giveaway['name']}\n"
                    f"**Ваше место:** {winner['place']}\n\n"
                    f"Для получения приза запустите бота командой /start и следуйте инструкциям."
                )

                await bot.send_message(
                    winner['user_id'],
                    message,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Error notifying winner {winner['user_id']}: {e}")

    async def collect_winner_data(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбор данных от победителя"""
        user_id = update.effective_user.id

        # Проверяем, является ли пользователь победителем
        winner_info = await self.queries.get_winner_info(user_id)

        if not winner_info:
            await update.message.reply_text(
                "❌ Вы не являетесь победителем ни в одном из розыгрышей."
            )
            return

        if winner_info['data_collected']:
            await update.message.reply_text(
                "✅ Ваши данные уже собраны! Приз будет отправлен в ближайшее время."
            )
            return

        # Начинаем сбор данных
        context.user_data['collecting_data_for'] = winner_info['giveaway_id']

        await update.message.reply_text(
            f"{settings.MESSAGES['data_collection']}\n\n"
            "Пожалуйста, укажите ваше **полное имя**:",
            parse_mode='Markdown'
        )
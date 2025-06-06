import json
from datetime import datetime
from typing import Dict, List, Optional


async def format_giveaway_info(giveaway: Dict, participants_count: int) -> str:
    """Форматирование информации о розыгрыше"""
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
            # Удаляем Z или другие timezone суффиксы
            created_at_str = created_at_str.replace('Z', '').replace('+00:00', '')
            if '.' in created_at_str:
                created_at_str = created_at_str.split('.')[0]
            created_at = datetime.fromisoformat(created_at_str)
            text += f"**Создан:** {created_at.strftime('%d.%m.%Y %H:%M')}\n"
    except (ValueError, KeyError):
        text += f"**Создан:** -\n"

    # Обработка published_at
    try:
        published_at_str = giveaway.get('published_at')
        if published_at_str:
            published_at_str = published_at_str.replace('Z', '').replace('+00:00', '')
            if '.' in published_at_str:
                published_at_str = published_at_str.split('.')[0]
            published_at = datetime.fromisoformat(published_at_str)
            text += f"**Опубликован:** {published_at.strftime('%d.%m.%Y %H:%M')}\n"
    except (ValueError, TypeError):
        pass

    # Обработка finished_at
    try:
        finished_at_str = giveaway.get('finished_at')
        if finished_at_str:
            finished_at_str = finished_at_str.replace('Z', '').replace('+00:00', '')
            if '.' in finished_at_str:
                finished_at_str = finished_at_str.split('.')[0]
            finished_at = datetime.fromisoformat(finished_at_str)
            text += f"**Завершен:** {finished_at.strftime('%d.%m.%Y %H:%M')}\n"
    except (ValueError, TypeError):
        pass

    return text


def generate_referral_link(bot_username: str, giveaway_id: str, user_id: int) -> str:
    """Генерация реферальной ссылки"""
    return f"https://t.me/{bot_username}?start=ref_{giveaway_id}_{user_id}"


def format_winners_list(winners: List[Dict]) -> str:
    """Форматирование списка победителей"""
    if not winners:
        return "Нет победителей"

    text = "🏆 **Победители:**\n\n"

    for winner in winners:
        name = winner.get('first_name', 'Пользователь')
        username = winner.get('username')

        if username:
            text += f"{winner['place']}. {name} (@{username})\n"
        else:
            text += f"{winner['place']}. {name} (ID: {winner['user_id']})\n"

    return text


def parse_referral_link(start_param: str) -> Optional[Dict]:
    """Парсинг реферальной ссылки"""
    if not start_param or not start_param.startswith('ref_'):
        return None

    try:
        parts = start_param.split('_')
        if len(parts) != 3:
            return None

        return {
            'giveaway_id': parts[1],
            'referrer_id': int(parts[2])
        }
    except (ValueError, IndexError):
        return None


async def check_channel_subscription(bot, user_id: int, channel_id: str) -> bool:
    """Проверка подписки на канал"""
    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return member.status not in ['left', 'kicked']
    except Exception:
        return False
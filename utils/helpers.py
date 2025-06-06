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

    created_at = datetime.fromisoformat(giveaway['created_at'].replace('Z', '+00:00'))
    text += f"**Создан:** {created_at.strftime('%d.%m.%Y %H:%M')}\n"

    if giveaway.get('published_at'):
        published_at = datetime.fromisoformat(giveaway['published_at'].replace('Z', '+00:00'))
        text += f"**Опубликован:** {published_at.strftime('%d.%m.%Y %H:%M')}\n"

    if giveaway.get('finished_at'):
        finished_at = datetime.fromisoformat(giveaway['finished_at'].replace('Z', '+00:00'))
        text += f"**Завершен:** {finished_at.strftime('%d.%m.%Y %H:%M')}\n"

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
    if not start_param.startswith('ref_'):
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
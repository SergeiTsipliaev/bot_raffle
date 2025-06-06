from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config.settings import settings


class InlineKeyboards:
    @staticmethod
    def admin_main_menu():
        """Главное меню администратора"""
        keyboard = [
            [
                InlineKeyboardButton(f"{settings.EMOJIS['create']} Создать розыгрыш", callback_data="create_giveaway"),
                InlineKeyboardButton(f"{settings.EMOJIS['list']} Мои розыгрыши", callback_data="my_giveaways")
            ],
            [
                InlineKeyboardButton(f"{settings.EMOJIS['participants']} Участники", callback_data="all_participants"),
                InlineKeyboardButton(f"{settings.EMOJIS['winners']} Победители", callback_data="all_winners")
            ],
            [
                InlineKeyboardButton(f"{settings.EMOJIS['settings']} Настройки", callback_data="settings"),
                InlineKeyboardButton(f"{settings.EMOJIS['stats']} Статистика", callback_data="statistics")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def giveaway_management(giveaway_id: str, status: str = "created"):
        """Меню управления розыгрышем"""
        keyboard = []

        if status == "created":
            keyboard.extend([
                [
                    InlineKeyboardButton(f"{settings.EMOJIS['edit']} Редактировать",
                                         callback_data=f"edit_{giveaway_id}"),
                    InlineKeyboardButton(f"{settings.EMOJIS['publish']} Публикация",
                                         callback_data=f"publish_{giveaway_id}")
                ],
                [
                    InlineKeyboardButton(f"{settings.EMOJIS['settings']} Подписки",
                                         callback_data=f"channels_{giveaway_id}"),
                    InlineKeyboardButton(f"🛡️ Защита от ботов", callback_data=f"protection_{giveaway_id}")
                ],
                [
                    InlineKeyboardButton(f"{settings.EMOJIS['participants']} Участники",
                                         callback_data=f"participants_{giveaway_id}"),
                    InlineKeyboardButton(f"⏰ Запланировать", callback_data=f"schedule_{giveaway_id}")
                ]
            ])
        elif status == "published":
            keyboard.extend([
                [
                    InlineKeyboardButton(f"{settings.EMOJIS['play']} Разыграть", callback_data=f"draw_{giveaway_id}"),
                    InlineKeyboardButton(f"{settings.EMOJIS['participants']} Участники",
                                         callback_data=f"participants_{giveaway_id}")
                ],
                [
                    InlineKeyboardButton(f"{settings.EMOJIS['edit']} Редактировать",
                                         callback_data=f"edit_{giveaway_id}"),
                    InlineKeyboardButton(f"{settings.EMOJIS['export']} Экспорт", callback_data=f"export_{giveaway_id}")
                ]
            ])
        elif status == "finished":
            keyboard.extend([
                [
                    InlineKeyboardButton(f"{settings.EMOJIS['winners']} Победители",
                                         callback_data=f"winners_{giveaway_id}"),
                    InlineKeyboardButton(f"🔄 Переиграть", callback_data=f"redraw_{giveaway_id}")
                ],
                [
                    InlineKeyboardButton(f"{settings.EMOJIS['participants']} Участники",
                                         callback_data=f"participants_{giveaway_id}"),
                    InlineKeyboardButton(f"{settings.EMOJIS['export']} Экспорт", callback_data=f"export_{giveaway_id}")
                ]
            ])

        keyboard.extend([
            [
                InlineKeyboardButton(f"⚙️ Доп. настройки", callback_data=f"advanced_{giveaway_id}"),
                InlineKeyboardButton(f"{settings.EMOJIS['delete']} Удалить", callback_data=f"delete_{giveaway_id}")
            ],
            [InlineKeyboardButton(f"{settings.EMOJIS['back']} Назад", callback_data="my_giveaways")]
        ])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def giveaway_navigation(current_index: int, total_count: int, prefix: str = "giveaway"):
        """Навигация между розыгрышами"""
        keyboard = []
        nav_buttons = []

        if current_index > 1:
            nav_buttons.append(InlineKeyboardButton("⏮️", callback_data=f"{prefix}_nav_0"))
        if current_index > 0:
            nav_buttons.append(InlineKeyboardButton("◀️", callback_data=f"{prefix}_nav_{current_index - 1}"))

        nav_buttons.append(InlineKeyboardButton(f"{current_index + 1}/{total_count}", callback_data="noop"))

        if current_index < total_count - 1:
            nav_buttons.append(InlineKeyboardButton("▶️", callback_data=f"{prefix}_nav_{current_index + 1}"))
        if current_index < total_count - 2:
            nav_buttons.append(InlineKeyboardButton("⏭️", callback_data=f"{prefix}_nav_{total_count - 1}"))

        if nav_buttons:
            keyboard.append(nav_buttons)

        keyboard.append(
            [InlineKeyboardButton(f"{settings.EMOJIS['refresh']} Обновить", callback_data=f"{prefix}_refresh")])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def participation_button(giveaway_id: str, participants_count: int = 0,
                             show_count: bool = True, button_text: str = "Участвовать"):
        """Кнопка участия в розыгрыше"""
        if show_count:
            text = f"{button_text} ({participants_count})"
        else:
            text = button_text

        keyboard = [[InlineKeyboardButton(text, callback_data=f"participate_{giveaway_id}")]]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def confirm_action(action: str, item_id: str):
        """Подтверждение действия"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Да", callback_data=f"confirm_{action}_{item_id}"),
                InlineKeyboardButton("❌ Нет", callback_data=f"cancel_{action}_{item_id}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def publish_options(giveaway_id: str):
        """Опции публикации"""
        keyboard = [
            [InlineKeyboardButton("⚡ Мгновенно", callback_data=f"publish_instant_{giveaway_id}")],
            [InlineKeyboardButton("⏰ Запланировать", callback_data=f"publish_schedule_{giveaway_id}")],
            [InlineKeyboardButton("📝 Создать из сообщения", callback_data=f"publish_from_message_{giveaway_id}")],
            [InlineKeyboardButton(f"{settings.EMOJIS['back']} Назад", callback_data=f"manage_{giveaway_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def button_attachment_type(giveaway_id: str):
        """Тип прикрепления кнопки"""
        keyboard = [
            [InlineKeyboardButton("📎 Привязанная к посту", callback_data=f"button_attached_{giveaway_id}")],
            [InlineKeyboardButton("🔗 Отдельная кнопка", callback_data=f"button_separate_{giveaway_id}")],
            [InlineKeyboardButton(f"{settings.EMOJIS['back']} Назад", callback_data=f"publish_{giveaway_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)
import csv
import json
import io
from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes
from database.queries import DatabaseQueries


class ExportHandler:
    """Обработчик экспорта данных"""

    def __init__(self, db_manager):
        self.db = db_manager
        self.queries = DatabaseQueries(db_manager)

    async def export_participants_csv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Экспорт участников в CSV"""
        callback_data = update.callback_query.data
        giveaway_id = callback_data.split('_')[1]

        # Получаем участников
        participants = await self.queries.export_participants(giveaway_id, 'csv')

        if not participants:
            await update.callback_query.answer("❌ Нет участников для экспорта!", show_alert=True)
            return

        # Создаем CSV файл в памяти
        output = io.StringIO()

        if participants:
            fieldnames = participants[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)

            writer.writeheader()
            for participant in participants:
                writer.writerow(participant)

        # Конвертируем в байты
        csv_data = output.getvalue().encode('utf-8-sig')  # BOM для корректного отображения в Excel
        output.close()

        # Получаем информацию о розыгрыше
        giveaway = await self.db.get_giveaway(giveaway_id)
        filename = f"participants_{giveaway['name'][:20]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        # Отправляем файл
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=io.BytesIO(csv_data),
            filename=filename,
            caption=f"📊 Участники розыгрыша '{giveaway['name']}'\n"
                    f"Всего участников: {len(participants)}\n"
                    f"Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )

        await update.callback_query.answer("✅ Файл отправлен!")

    async def export_statistics_json(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Экспорт статистики в JSON"""
        admin_id = update.effective_user.id

        # Получаем статистику
        stats = await self.queries.get_statistics(admin_id)

        # Получаем все розыгрыши администратора
        giveaways = await self.db.get_giveaways_by_admin(admin_id)

        # Формируем полную статистику
        full_stats = {
            'export_date': datetime.now().isoformat(),
            'admin_id': admin_id,
            'summary': stats,
            'giveaways': []
        }

        for giveaway in giveaways:
            participants_count = await self.db.get_participants_count(giveaway['id'])
            giveaway_stats = {
                'id': giveaway['id'],
                'name': giveaway['name'],
                'status': giveaway['status'],
                'participants_count': participants_count,
                'created_at': giveaway['created_at'],
                'published_at': giveaway.get('published_at'),
                'finished_at': giveaway.get('finished_at')
            }
            full_stats['giveaways'].append(giveaway_stats)

        # Создаем JSON файл
        json_data = json.dumps(full_stats, ensure_ascii=False, indent=2).encode('utf-8')
        filename = f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Отправляем файл
        await context.bot.send_document(
            chat_id=update.effective_chat.id,
            document=io.BytesIO(json_data),
            filename=filename,
            caption=f"📊 **Статистика розыгрышей**\n\n"
                    f"**Всего розыгрышей:** {stats['total_giveaways']}\n"
                    f"**Завершено:** {stats['finished_giveaways']}\n"
                    f"**Активных:** {stats['active_giveaways']}\n"
                    f"**Всего участников:** {stats['total_participants']}\n"
                    f"**Среднее участников:** {stats['avg_participants']}",
            parse_mode='Markdown'
        )
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List
import logging

logger = logging.getLogger(__name__)


class GiveawayScheduler:
    """Планировщик розыгрышей"""

    def __init__(self, db_manager, bot):
        self.db = db_manager
        self.bot = bot
        self.scheduled_tasks = {}  # giveaway_id: task
        self.running = False

    async def start(self):
        """Запуск планировщика"""
        self.running = True

        # Загружаем запланированные розыгрыши из базы данных
        await self.load_scheduled_giveaways()

        # Запускаем основной цикл
        asyncio.create_task(self.scheduler_loop())
        logger.info("Планировщик розыгрышей запущен")

    async def stop(self):
        """Остановка планировщика"""
        self.running = False

        # Отменяем все задачи
        for task in self.scheduled_tasks.values():
            task.cancel()

        self.scheduled_tasks.clear()
        logger.info("Планировщик розыгрышей остановлен")

    async def load_scheduled_giveaways(self):
        """Загрузка запланированных розыгрышей"""
        async with self.db.get_db_connection() as conn:
            cursor = await conn.execute('''
                SELECT id, scheduled_publish 
                FROM giveaways 
                WHERE status = 'scheduled' AND scheduled_publish > datetime('now')
            ''')

            rows = await cursor.fetchall()

            for row in rows:
                giveaway_id, scheduled_time_str = row
                scheduled_time = datetime.fromisoformat(scheduled_time_str)

                # Создаем задачу для публикации
                delay = (scheduled_time - datetime.now()).total_seconds()
                if delay > 0:
                    task = asyncio.create_task(
                        self.publish_giveaway_delayed(giveaway_id, delay)
                    )
                    self.scheduled_tasks[giveaway_id] = task

    async def schedule_giveaway(self, giveaway_id: str, publish_time: datetime):
        """Планирование розыгрыша"""
        # Обновляем базу данных
        async with self.db.get_db_connection() as conn:
            await conn.execute('''
                UPDATE giveaways 
                SET status = 'scheduled', scheduled_publish = ?
                WHERE id = ?
            ''', (publish_time.isoformat(), giveaway_id))
            await conn.commit()

        # Создаем задачу
        delay = (publish_time - datetime.now()).total_seconds()
        if delay > 0:
            task = asyncio.create_task(
                self.publish_giveaway_delayed(giveaway_id, delay)
            )
            self.scheduled_tasks[giveaway_id] = task

            logger.info(f"Розыгрыш {giveaway_id} запланирован на {publish_time}")

    async def publish_giveaway_delayed(self, giveaway_id: str, delay: float):
        """Отложенная публикация розыгрыша"""
        try:
            await asyncio.sleep(delay)

            # Публикуем розыгрыш
            await self.publish_giveaway(giveaway_id)

            # Удаляем из запланированных
            if giveaway_id in self.scheduled_tasks:
                del self.scheduled_tasks[giveaway_id]

        except asyncio.CancelledError:
            logger.info(f"Публикация розыгрыша {giveaway_id} отменена")
        except Exception as e:
            logger.error(f"Ошибка при публикации розыгрыша {giveaway_id}: {e}")

    async def publish_giveaway(self, giveaway_id: str):
        """Публикация розыгрыша"""
        # Обновляем статус
        async with self.db.get_db_connection() as conn:
            await conn.execute('''
                UPDATE giveaways 
                SET status = 'published', published_at = datetime('now')
                WHERE id = ?
            ''', (giveaway_id,))
            await conn.commit()

        # Уведомляем администратора
        giveaway = await self.db.get_giveaway(giveaway_id)
        if giveaway:
            try:
                await self.bot.send_message(
                    giveaway['admin_id'],
                    f"📢 **Розыгрыш опубликован автоматически!**\n\n"
                    f"**Название:** {giveaway['name']}\n"
                    f"**ID:** `{giveaway_id}`\n"
                    f"**Время:** {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"Ошибка уведомления администратора: {e}")

        logger.info(f"Розыгрыш {giveaway_id} успешно опубликован")

    async def cancel_scheduled_giveaway(self, giveaway_id: str):
        """Отмена запланированного розыгрыша"""
        if giveaway_id in self.scheduled_tasks:
            self.scheduled_tasks[giveaway_id].cancel()
            del self.scheduled_tasks[giveaway_id]

        # Обновляем статус в базе данных
        async with self.db.get_db_connection() as conn:
            await conn.execute('''
                UPDATE giveaways 
                SET status = 'created', scheduled_publish = NULL
                WHERE id = ?
            ''', (giveaway_id,))
            await conn.commit()

        logger.info(f"Планирование розыгрыша {giveaway_id} отменено")

    async def scheduler_loop(self):
        """Основной цикл планировщика"""
        while self.running:
            try:
                # Проверяем просроченные задачи каждую минуту
                await asyncio.sleep(60)

                # Удаляем завершенные задачи
                completed_tasks = [
                    gid for gid, task in self.scheduled_tasks.items()
                    if task.done()
                ]

                for gid in completed_tasks:
                    del self.scheduled_tasks[gid]

            except Exception as e:
                logger.error(f"Ошибка в планировщике: {e}")
                await asyncio.sleep(60)
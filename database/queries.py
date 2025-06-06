import aiosqlite
from typing import List, Dict, Optional


class DatabaseQueries:
    """Дополнительные запросы к базе данных"""

    def __init__(self, db_manager):
        self.db = db_manager

    async def get_participants(self, giveaway_id: str) -> List[Dict]:
        """Получение всех участников розыгрыша"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            cursor = await conn.execute('''
                SELECT * FROM participants 
                WHERE giveaway_id = ?
                ORDER BY joined_at ASC
            ''', (giveaway_id,))

            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]

            return [dict(zip(columns, row)) for row in rows]

    async def save_winners(self, giveaway_id: str, winners: List[Dict]):
        """Сохранение победителей в базу данных"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            for winner in winners:
                await conn.execute('''
                    INSERT INTO winners (giveaway_id, user_id, place)
                    VALUES (?, ?, ?)
                ''', (giveaway_id, winner['user_id'], winner['place']))
            await conn.commit()

    async def update_giveaway_status(self, giveaway_id: str, status: str):
        """Обновление статуса розыгрыша"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            await conn.execute('''
                UPDATE giveaways 
                SET status = ?, finished_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, giveaway_id))
            await conn.commit()

    async def get_winner_info(self, user_id: int) -> Optional[Dict]:
        """Получение информации о победе пользователя"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            cursor = await conn.execute('''
                SELECT w.*, g.name as giveaway_name
                FROM winners w
                JOIN giveaways g ON w.giveaway_id = g.id
                WHERE w.user_id = ? AND w.data_collected = FALSE
                ORDER BY w.selected_at DESC
                LIMIT 1
            ''', (user_id,))

            row = await cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None

    async def export_participants(self, giveaway_id: str, format_type: str = 'csv') -> List[Dict]:
        """Экспорт участников розыгрыша"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            cursor = await conn.execute('''
                SELECT 
                    user_id as ID,
                    COALESCE(first_name, '') as Name,
                    COALESCE(username, '') as Username,
                    CASE 
                        WHEN username IS NOT NULL THEN 'Active'
                        ELSE 'No Username'
                    END as Status,
                    joined_at as Date_Register,
                    referral_count as Referrals
                FROM participants 
                WHERE giveaway_id = ?
                ORDER BY joined_at ASC
            ''', (giveaway_id,))

            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]

            return [dict(zip(columns, row)) for row in rows]

    async def get_statistics(self, admin_id: int) -> Dict:
        """Получение статистики для администратора"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            # Общее количество розыгрышей
            cursor = await conn.execute('''
                SELECT COUNT(*) FROM giveaways WHERE admin_id = ?
            ''', (admin_id,))
            total_giveaways = (await cursor.fetchone())[0]

            # Завершенные розыгрыши
            cursor = await conn.execute('''
                SELECT COUNT(*) FROM giveaways 
                WHERE admin_id = ? AND status = 'finished'
            ''', (admin_id,))
            finished_giveaways = (await cursor.fetchone())[0]

            # Общее количество участников
            cursor = await conn.execute('''
                SELECT COUNT(DISTINCT p.user_id) 
                FROM participants p
                JOIN giveaways g ON p.giveaway_id = g.id
                WHERE g.admin_id = ?
            ''', (admin_id,))
            total_participants = (await cursor.fetchone())[0]

            # Среднее количество участников на розыгрыш
            cursor = await conn.execute('''
                SELECT AVG(participant_count) FROM (
                    SELECT COUNT(*) as participant_count
                    FROM participants p
                    JOIN giveaways g ON p.giveaway_id = g.id
                    WHERE g.admin_id = ?
                    GROUP BY g.id
                )
            ''', (admin_id,))
            avg_participants = (await cursor.fetchone())[0] or 0

            return {
                'total_giveaways': total_giveaways,
                'finished_giveaways': finished_giveaways,
                'active_giveaways': total_giveaways - finished_giveaways,
                'total_participants': total_participants,
                'avg_participants': round(avg_participants, 2)
            }
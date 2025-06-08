import sqlite3
import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict
from config.settings import settings


class DatabaseManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DATABASE_URL.replace('sqlite:///', '')

    async def init_database(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица пользователей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_admin BOOLEAN DEFAULT FALSE,
                    language_code TEXT DEFAULT 'ru',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица розыгрышей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS giveaways (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    admin_id INTEGER,
                    status TEXT DEFAULT 'created',
                    prizes_count INTEGER DEFAULT 1,
                    max_participants INTEGER DEFAULT 0,
                    required_channels TEXT,
                    media_files TEXT,
                    referral_enabled BOOLEAN DEFAULT FALSE,
                    referral_multiplier REAL DEFAULT 1.5,
                    max_referral_multiplier REAL DEFAULT 5.0,
                    captcha_enabled BOOLEAN DEFAULT FALSE,
                    button_text TEXT DEFAULT 'Участвовать',
                    show_participants_count BOOLEAN DEFAULT TRUE,
                    instant_publish BOOLEAN DEFAULT FALSE,
                    scheduled_publish TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    published_at TIMESTAMP,
                    finished_at TIMESTAMP,
                    FOREIGN KEY (admin_id) REFERENCES users (user_id)
                )
            ''')

            # Таблица участников
            await db.execute('''
                CREATE TABLE IF NOT EXISTS participants (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    giveaway_id TEXT,
                    user_id INTEGER,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    referred_by INTEGER,
                    referral_count INTEGER DEFAULT 0,
                    multiplier REAL DEFAULT 1.0,
                    captcha_passed BOOLEAN DEFAULT FALSE,
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (giveaway_id) REFERENCES giveaways (id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id),
                    UNIQUE(giveaway_id, user_id)
                )
            ''')

            # Таблица победителей
            await db.execute('''
                CREATE TABLE IF NOT EXISTS winners (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    giveaway_id TEXT,
                    user_id INTEGER,
                    place INTEGER,
                    data_collected BOOLEAN DEFAULT FALSE,
                    winner_data TEXT,
                    prize_sent BOOLEAN DEFAULT FALSE,
                    selected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (giveaway_id) REFERENCES giveaways (id),
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            ''')

            # Добавляем первого администратора
            await db.execute('''
                INSERT OR IGNORE INTO users (user_id, username, first_name, is_admin)
                VALUES (?, ?, ?, ?)
            ''', (settings.ADMIN_USER_ID, 'admin', 'Администратор', True))

            await db.commit()

    async def add_user(self, user_data: Dict):
        """Добавление пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT OR REPLACE INTO users 
                (user_id, username, first_name, last_name, language_code)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                user_data['user_id'],
                user_data.get('username'),
                user_data.get('first_name'),
                user_data.get('last_name'),
                user_data.get('language_code', 'ru')
            ))
            await db.commit()

    async def is_admin(self, user_id: int) -> bool:
        """Проверка администратора"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT is_admin FROM users WHERE user_id = ?',
                (user_id,)
            )
            result = await cursor.fetchone()
            return result and result[0]

    async def create_giveaway(self, giveaway_data: Dict) -> str:
        """Создание розыгрыша"""
        import uuid
        giveaway_id = str(uuid.uuid4())

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO giveaways 
                (id, name, description, admin_id, prizes_count, max_participants,
                 referral_enabled, captcha_enabled, button_text, show_participants_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                giveaway_id,
                giveaway_data['name'],
                giveaway_data.get('description', ''),
                giveaway_data['admin_id'],
                giveaway_data.get('prizes_count', 1),
                giveaway_data.get('max_participants', 0),
                giveaway_data.get('referral_enabled', False),
                giveaway_data.get('captcha_enabled', False),
                giveaway_data.get('button_text', 'Участвовать'),
                giveaway_data.get('show_participants_count', True)
            ))
            await db.commit()

        return giveaway_id

    async def get_giveaways_by_admin(self, admin_id: int) -> List[Dict]:
        """Получение розыгрышей администратора"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT * FROM giveaways 
                WHERE admin_id = ? 
                ORDER BY created_at DESC
            ''', (admin_id,))

            rows = await cursor.fetchall()
            columns = [description[0] for description in cursor.description]

            return [dict(zip(columns, row)) for row in rows]

    async def get_giveaway(self, giveaway_id: str) -> Optional[Dict]:
        """Получение информации о розыгрыше"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT * FROM giveaways WHERE id = ?',
                (giveaway_id,)
            )
            row = await cursor.fetchone()

            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None

    async def add_participant(self, giveaway_id: str, user_data: Dict,
                              referred_by: Optional[int] = None) -> bool:
        """Добавление участника"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO participants 
                    (giveaway_id, user_id, username, first_name, last_name, referred_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    giveaway_id,
                    user_data['user_id'],
                    user_data.get('username'),
                    user_data.get('first_name'),
                    user_data.get('last_name'),
                    referred_by
                ))

                # Обновляем счетчик рефералов
                if referred_by:
                    await db.execute('''
                        UPDATE participants 
                        SET referral_count = referral_count + 1
                        WHERE giveaway_id = ? AND user_id = ?
                    ''', (giveaway_id, referred_by))

                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка добавления участника: {e}")
            return False

    async def get_participants_count(self, giveaway_id: str) -> int:
        """Получение количества участников"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT COUNT(*) FROM participants WHERE giveaway_id = ?',
                (giveaway_id,)
            )
            result = await cursor.fetchone()
            return result[0] if result else 0

    async def is_participating(self, giveaway_id: str, user_id: int) -> bool:
        """Проверка участия пользователя"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                'SELECT 1 FROM participants WHERE giveaway_id = ? AND user_id = ?',
                (giveaway_id, user_id)
            )
            result = await cursor.fetchone()
            return bool(result)

    async def update_giveaway(self, giveaway_id: str, updates: Dict) -> bool:
        """Обновление данных розыгрыша"""
        if not updates:
            return False

        try:
            # Формируем SQL запрос динамически
            set_clauses = []
            values = []

            for key, value in updates.items():
                set_clauses.append(f"{key} = ?")
                values.append(value)

            values.append(giveaway_id)

            sql = f"UPDATE giveaways SET {', '.join(set_clauses)} WHERE id = ?"

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(sql, values)
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка обновления розыгрыша: {e}")
            return False

    async def delete_giveaway(self, giveaway_id: str) -> bool:
        """Удаление розыгрыша"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Удаляем связанные данные
                await db.execute('DELETE FROM participants WHERE giveaway_id = ?', (giveaway_id,))
                await db.execute('DELETE FROM winners WHERE giveaway_id = ?', (giveaway_id,))
                await db.execute('DELETE FROM giveaways WHERE id = ?', (giveaway_id,))
                await db.commit()
                return True
        except Exception as e:
            print(f"Ошибка удаления розыгрыша: {e}")
            return False
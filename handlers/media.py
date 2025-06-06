import os
import aiofiles
from typing import List, Dict
from telegram import Update, InputMediaPhoto, InputMediaVideo, InputMediaDocument
from telegram.ext import ContextTypes
from config.settings import settings


class MediaHandler:
    """Обработчик медиа файлов"""

    def __init__(self, db_manager):
        self.db = db_manager
        self.media_dir = "media"
        self.ensure_media_dir()

    def ensure_media_dir(self):
        """Создание директории для медиа файлов"""
        if not os.path.exists(self.media_dir):
            os.makedirs(self.media_dir)
            os.makedirs(os.path.join(self.media_dir, "giveaways"))
            os.makedirs(os.path.join(self.media_dir, "prizes"))

    async def save_media_file(self, file, giveaway_id: str, media_type: str) -> str:
        """Сохранение медиа файла"""
        file_extension = file.file_path.split('.')[-1] if '.' in file.file_path else 'bin'
        filename = f"{giveaway_id}_{file.file_id}.{file_extension}"
        filepath = os.path.join(self.media_dir, "giveaways", filename)

        # Скачиваем файл
        await file.download_to_drive(filepath)

        return filepath

    async def create_media_group(self, giveaway_id: str) -> List:
        """Создание группы медиа для публикации"""
        # Получаем медиа файлы из базы данных
        giveaway = await self.db.get_giveaway(giveaway_id)
        media_files = giveaway.get('media_files')

        if not media_files:
            return []

        import json
        files_data = json.loads(media_files)
        media_group = []

        for file_data in files_data:
            media_type = file_data['type']
            file_path = file_data['path']
            caption = file_data.get('caption', '')

            if media_type == 'photo':
                media_group.append(InputMediaPhoto(
                    media=open(file_path, 'rb'),
                    caption=caption
                ))
            elif media_type == 'video':
                media_group.append(InputMediaVideo(
                    media=open(file_path, 'rb'),
                    caption=caption
                ))
            elif media_type == 'document':
                media_group.append(InputMediaDocument(
                    media=open(file_path, 'rb'),
                    caption=caption
                ))

        return media_group

    async def process_forwarded_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка пересланного сообщения для создания поста"""
        message = update.message
        giveaway_id = context.user_data.get('creating_post_for')

        if not giveaway_id:
            await message.reply_text("❌ Не выбран розыгрыш для создания поста.")
            return

        # Извлекаем текст
        post_text = message.text or message.caption or ""

        # Обрабатываем медиа
        media_files = []

        if message.photo:
            # Фото
            photo = message.photo[-1]  # Берем самое большое разрешение
            file_path = await self.save_media_file(photo, giveaway_id, 'photo')
            media_files.append({
                'type': 'photo',
                'path': file_path,
                'caption': message.caption or ''
            })

        elif message.video:
            # Видео
            video = message.video
            file_path = await self.save_media_file(video, giveaway_id, 'video')
            media_files.append({
                'type': 'video',
                'path': file_path,
                'caption': message.caption or ''
            })

        elif message.document:
            # Документ
            document = message.document
            file_path = await self.save_media_file(document, giveaway_id, 'document')
            media_files.append({
                'type': 'document',
                'path': file_path,
                'caption': message.caption or ''
            })

        # Сохраняем в контекст для дальнейшего использования
        context.user_data['post_text'] = post_text
        context.user_data['post_media'] = media_files

        await message.reply_text(
            "✅ **Пост создан из сообщения!**\n\n"
            f"**Текст:** {post_text[:100]}{'...' if len(post_text) > 100 else ''}\n"
            f"**Медиа файлов:** {len(media_files)}\n\n"
            "Выберите дальнейшие действия:",
            parse_mode='Markdown'
        )
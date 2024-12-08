import os
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils import executor
import yt_dlp
import aiofiles
import re
from io import BytesIO
import requests

# Константы
API_TOKEN = "8063145361:AAHTJ3oudzyAk9zkU6-_FXWzZQkZD6Tbic8"
LOG_CHANNEL = "@anlist12412412sf"
USERS_FILE = "users.json"
STATS_FILE = "stats.json"
ANALYTICS_FILE = "analytics.txt"

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Меню бота
main_menu = ReplyKeyboardMarkup(resize_keyboard=True)
main_menu.add(KeyboardButton("📥 Скачать видео"), KeyboardButton("📸 Скачать фото"))

# Список пользователей, которым доступна команда /stat
ALLOWED_USERS = ["@Slam163f"]

# Асинхронные функции для работы с файлами
async def load_json(file_path, default):
    """Загрузка данных из JSON файла"""
    if os.path.exists(file_path):
        async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
            try:
                return json.loads(await f.read())
            except (json.JSONDecodeError, FileNotFoundError):
                return default
    return default


async def save_json(file_path, data):
    """Сохранение данных в JSON файл"""
    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(data, indent=4, ensure_ascii=False))


async def save_analytics_to_file(data):
    """Запись аналитики в файл"""
    async with aiofiles.open(ANALYTICS_FILE, 'a', encoding='utf-8') as f:
        await f.write(data + "\n")


# Очистка имени файла
def sanitize_filename(filename):
    """Удаление запрещённых символов из имени файла"""
    return re.sub(r'[<>:"/\\|?*]', '', filename).replace(' ', '_')


# Стартовая команда
@dp.message_handler(commands=["start"])
async def start_cmd(message: types.Message):
    """Обработчик команды /start"""
    users = await load_json(USERS_FILE, {})
    user_id = str(message.from_user.id)

    if user_id not in users:
        users[user_id] = {
            "username": f"@{message.from_user.username}" if message.from_user.username else "No username",
            "first_name": message.from_user.first_name,
            "date_joined": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "user_number": len(users) + 1
        }
        await save_json(USERS_FILE, users)
        log_message = f"👤 Новый пользователь: {users[user_id]['username']}, {users[user_id]['first_name']}"
        await bot.send_message(LOG_CHANNEL, log_message)

    await message.reply('''
    Этот бот создан разработчиком — @slam163f
    На данный момент бот умеет скачивать:
    📹 Видео с платформ 
    TikTok
    YouTube
    Pinterest
    Instagram

    📸 Фото пока доступны только с Pinterest и Instagram
    ❌ Фото с TikTok пока недоступны

    В будущем будет много обновлений и функций

    Версия бота Beta v1.0
    ''')


# Обработчик скачивания видео
@dp.message_handler(lambda message: message.text == "📥 Скачать видео")
async def ask_video_url(message: types.Message):
    """Попросить ссылку для скачивания видео"""
    await message.reply("Отправьте ссылку на видео для скачивания.")


@dp.message_handler(lambda message: message.text.startswith("http"))
async def download_video(message: types.Message):
    """Скачать видео по ссылке"""
    url = message.text.strip()

    await message.reply("⏳ Идет загрузка видео, пожалуйста, подождите...")

    ydl_opts = {"format": "best", "noplaylist": True}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info.get("url")
            video_title = sanitize_filename(info.get("title", "video"))
            video_size = info.get("filesize", 0)  # Размер файла в байтах

            # Проверка размера файла
            if video_size and video_size > 50 * 1024 * 1024:  # 50 МБ лимит
                await message.reply(
                    f"🎥 Видео слишком большое для отправки через Telegram.\n"
                    f"Вы можете скачать его вручную по этой ссылке:\n{video_url}"
                )
                return

            # Если размер подходит, загружаем и отправляем видео
            response = requests.get(video_url)
            video_bytes = BytesIO(response.content)
            video_bytes.seek(0)

            await message.reply_video(
                video_bytes,
                caption=f"🎥 Ваше видео: {video_title}"
            )

    except Exception as e:
        await message.reply(f"❌ Ошибка загрузки видео: {e}")


# Обработчик скачивания фото
@dp.message_handler(lambda message: message.text == "📸 Скачать фото")
async def ask_photo_url(message: types.Message):
    """Попросить ссылку для скачивания фото"""
    await message.reply("Отправьте ссылку на фото для скачивания.")


@dp.message_handler(lambda message: message.text.startswith("http"))
async def download_photo(message: types.Message):
    """Скачать фото по ссылке"""
    url = message.text.strip()

    try:
        response = requests.get(url)
        if response.status_code == 200:
            photo_bytes = BytesIO(response.content)
            await message.reply_photo(photo_bytes, caption="📸 Ваше фото.")
        else:
            await message.reply("❌ Ошибка загрузки фото. Проверьте ссылку.")
    except Exception as e:
        await message.reply(f"❌ Ошибка: {e}")


# Команда /stat
@dp.message_handler(commands=["stat"])
async def stat_cmd(message: types.Message):
    """Обработчик команды /stat"""
    if message.from_user.username not in ALLOWED_USERS:
        await message.reply("🚫 У вас нет доступа к этой команде.")
        return

    stats = await load_json(STATS_FILE, {})
    total_users = len(await load_json(USERS_FILE, {}))
    video_downloads = sum(user.get("video", 0) for user in stats.values())
    photo_downloads = sum(user.get("photo", 0) for user in stats.values())

    stats_message = (
        f"📊 Статистика:\n"
        f"Пользователей: {total_users}\n"
        f"Видео загружено: {video_downloads}\n"
        f"Фото загружено: {photo_downloads}"
    )

    await message.reply(stats_message)
    await bot.send_message(LOG_CHANNEL, stats_message)


# Основной блок для запуска бота
if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)

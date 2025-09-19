import logging
import pandas as pd
import requests
import hashlib
import os
import asyncio
import schedule
import time
import threading
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== НАСТРОЙКИ ==========
import os
TOKEN = os.environ.get('TOKEN', '8417032154:AAHtZF3wJyVHnU8QL48NpxA8oFqe8gdPGnE')
EXCEL_URL = os.environ.get('EXCEL_URL', 'https://miep.spb.ru/raspisanie/cise/%D0%A1%D0%9F%D0%9E%20%D1%81%D0%B5%D0%BD%D1%82%D1%8F%D0%B1%D1%80%D1%8C%202025.xlsx')
SHEET_NAME = "Э9-023"
CHECK_INTERVAL = 3000
# ==============================

# Файлы для хранения состояния
SCHEDULE_CACHE_FILE = "schedule_cache.xlsx"
LAST_HASH_FILE = "last_hash.txt"

def download_excel():
    """Загрузка Excel-файла по URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(EXCEL_URL, headers=headers)
        response.raise_for_status()
        
        with open(SCHEDULE_CACHE_FILE, 'wb') as f:
            f.write(response.content)
        
        logger.info("Файл успешно загружен")
        return SCHEDULE_CACHE_FILE
    except Exception as e:
        logger.error(f"Ошибка загрузки файла: {e}")
        return None

def get_file_hash(filename):
    """Вычисление хэша файла для обнаружения изменений"""
    try:
        with open(filename, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    except Exception as e:
        logger.error(f"Ошибка вычисления хэша: {e}")
        return None

def get_sheet_data(filename, sheet_name):
    """Извлечение данных с конкретного листа"""
    try:
        # Пытаемся прочитать указанный лист
        df = pd.read_excel(filename, sheet_name=sheet_name)
        logger.info(f"Данные листа '{sheet_name}' успешно прочитаны")
        return df
    except Exception as e:
        logger.error(f"Ошибка чтения листа {sheet_name}: {e}")
        return None

def save_last_hash(file_hash):
    """Сохранение последнего хэша файла"""
    try:
        with open(LAST_HASH_FILE, 'w') as f:
            f.write(file_hash)
        logger.info("Хэш успешно сохранен")
    except Exception as e:
        logger.error(f"Ошибка сохранения хэша: {e}")

def load_last_hash():
    """Загрузка последнего хэша файла"""
    try:
        if os.path.exists(LAST_HASH_FILE):
            with open(LAST_HASH_FILE, 'r') as f:
                return f.read().strip()
    except Exception as e:
        logger.error(f"Ошибка загрузки хэша: {e}")
    return None

async def check_for_updates(app):
    """Периодическая проверка обновлений"""
    try:
        # Загрузка файла
        file_path = download_excel()
        if not file_path:
            return
            
        current_hash = get_file_hash(file_path)
        if not current_hash:
            return
            
        last_hash = load_last_hash()
        
        # Если хэш изменился
        if last_hash and current_hash != last_hash:
            logger.info("Обнаружены изменения в расписании")
            
            # Извлечение данных с конкретного листа
            sheet_data = get_sheet_data(file_path, SHEET_NAME)
            
            if sheet_data is not None:
                # Формирование сообщения об изменениях
                message = "📅 Расписание обновлено!\n\n"
                message += "Используйте /schedule чтобы получить актуальное расписание."
                
                # Отправка сообщения всем пользователям
                if hasattr(app, 'bot_data') and 'users' in app.bot_data:
                    for user_id in app.bot_data['users']:
                        try:
                            await app.bot.send_message(
                                chat_id=user_id, 
                                text=message
                            )
                            # Отправка файла
                            with open(file_path, 'rb') as f:
                                await app.bot.send_document(
                                    chat_id=user_id, 
                                    document=f,
                                    filename="расписание.xlsx",
                                    caption="Актуальное расписание"
                                )
                        except Exception as e:
                            logger.error(f"Ошибка отправки пользователю {user_id}: {e}")
            
            # Сохранение нового хэша
            save_last_hash(current_hash)
        elif not last_hash:
            # Первый запуск - сохраняем хэш
            save_last_hash(current_hash)
            
    except Exception as e:
        logger.error(f"Ошибка при проверке обновлений: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    
    # Добавляем пользователя в список
    if not hasattr(context.application, 'bot_data'):
        context.application.bot_data = {}
    
    if 'users' not in context.application.bot_data:
        context.application.bot_data['users'] = []
    
    if user_id not in context.application.bot_data['users']:
        context.application.bot_data['users'].append(user_id)
        logger.info(f"Добавлен новый пользователь: {user_id}")
    
    await update.message.reply_text(
        "Привет! Я бот для отслеживания изменений в расписании. "
        "Я буду уведомлять вас о всех изменениях.\n\n"
        "Используйте /schedule чтобы получить текущее расписание."
    )

async def schedule_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /schedule"""
    try:
        # Загрузка и отправка текущего расписания
        file_path = download_excel()
        if file_path:
            with open(file_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename="расписание.xlsx",
                    caption="Текущее расписание"
                )
            logger.info("Отправлено текущее расписание")
        else:
            await update.message.reply_text("Извините, не удалось загрузить расписание.")
    except Exception as e:
        logger.error(f"Ошибка при отправке расписания: {e}")
        await update.message.reply_text("Извините, произошла ошибка при загрузке расписания.")

def run_scheduler(app):
    """Запускает планировщик в отдельном потоке"""
    while True:
        schedule.run_pending()
        time.sleep(1)

def main():
    """Основная функция"""
    # Создаем Application с использованием современного API
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("schedule", schedule_command))
    
    # Настраиваем периодическую проверку обновлений с помощью schedule
    schedule.every(CHECK_INTERVAL).seconds.do(
        lambda: asyncio.create_task(check_for_updates(application))
    )
    
    # Запускаем планировщик в отдельном потоке
    scheduler_thread = threading.Thread(target=run_scheduler, args=(application,), daemon=True)
    scheduler_thread.start()
    
    # Запускаем бота
    logger.info("Бот запущен")
    application.run_polling()

if __name__ == '__main__':
    main()
    application.add_handler(CommandHandler("help", help_command))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = """
🤖 Бот для отслеживания изменений в расписании

Доступные команды:
/start - Подписаться на уведомления
/schedule - Получить текущее расписание
/help - Показать эту справку

Бот автоматически проверяет расписание каждые 5 минут и присылает уведомления об изменениях.
    """
    await update.message.reply_text(help_text)

"""
Telegram-бот для консультанта по кирпичу Vandersanden
"""
import logging
import asyncio
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import DATA_DIR
from src.ai.consultant import BrickConsultant
from src.ai.image_search import ImageSearch
from src.ai.facade_generator import FacadeGenerator
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler

# Логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Глобальные объекты (инициализируются один раз)
consultant = None
image_searcher = None
facade_generator = None
user_house_photos = {}  # user_id -> photo_bytes


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🧱 *Привет! Я консультант по кирпичу Vandersanden.*\n\n"
        "*Режимы работы:*\n\n"
        "💬 *Консультация* — просто напишите вопрос, и я помогу с выбором, объясню характеристики, сравню варианты.\n\n"
        "🔍 `/search запрос` — строгий поиск. Выведу подходящие продукты без лишних слов.\n\n"
        "📸 `/photo` — поиск по фото. Просто отправьте изображение кирпича.\n\n"
        "🏠 `/tryon <название>` — примерка кирпича на фото вашего дома. Сначала отправьте фото!\n\n"
        "/help — справка",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        "*Как пользоваться ботом:*\n\n"
        "1️⃣ Просто напишите вопрос, например:\n"
        "_«Какой кирпич подойдет для холодного климата?»_\n\n"
        "2️⃣ Для поиска используйте /search:\n"
        "`/search белый кирпич`\n\n"
        "3️⃣ Можете спрашивать о конкретных характеристиках:\n"
        "_«Что значит морозостойкость F2?»_",
        parse_mode="Markdown"
    )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /search — строгий минимальный поиск"""
    global consultant
    
    if not context.args:
        await update.message.reply_text("Укажите запрос: `/search белый кирпич`", parse_mode="Markdown")
        return
    
    query = " ".join(context.args)
    
    try:
        results = consultant.search_products(query, n_results=5)
        
        if not results:
            await update.message.reply_text("Ничего не найдено.")
            return
        
        # Строгий формат: только продукты
        lines = []
        for i, r in enumerate(results, 1):
            d = r['details']
            name = d.get('name', r['slug'])
            article = d.get('article', '')
            color = d.get('color', {}).get('base_color', '')
            lines.append(f"{i}. {name} ({article}) — {color}")
        
        response = "\n".join(lines)
        
        # Короткий комментарий только если релевантность низкая
        top_relevance = 1 - results[0]['distance']
        if top_relevance < 0.6:
            response += "\n\n_Точного совпадения нет, показаны ближайшие._"
        
        try:
            await update.message.reply_text(response, parse_mode="Markdown")
        except:
            await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        await update.message.reply_text(f"Ошибка: {e}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик обычных сообщений (вопросов)"""
    global consultant
    
    query = update.message.text
    
    # Эвристика: если запрос короткий (<= 5 слов) и похож на поиск, предлагаем или делаем поиск
    is_short = len(query.split()) <= 5
    is_search_like = any(w in query.lower() for w in ["кирпич", "цвет", "красный", "белый", "серый", "черный", "коричневый", "желтый", "бежевый"])
    is_article = query.replace(" ", "").isalnum() and any(c.isdigit() for c in query)
    
    if (is_short and is_search_like) or (len(query) < 10 and is_article):
        # Автоматически переключаем в режим поиска
        context.args = query.split()
        await search(update, context)
        return

    await update.message.reply_text("🤔 Думаю...")
    
    user_id = str(update.effective_user.id)
    try:
        response = consultant.answer(query, user_id=user_id)
        
        # Telegram имеет лимит 4096 символов
        if len(response) > 4000:
            # Разбиваем на части
            parts = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for part in parts:
                try:
                    await update.message.reply_text(part, parse_mode="Markdown")
                except Exception:
                    # Если Markdown не парсится, отправляем как plain text
                    await update.message.reply_text(part)
        else:
            try:
                await update.message.reply_text(response, parse_mode="Markdown")
            except Exception:
                # Если Markdown не парсится, отправляем как plain text
                await update.message.reply_text(response)
            
    except Exception as e:
        logger.error(f"Answer error: {e}")
        await update.message.reply_text(f"Ошибка: {e}")


async def tryon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /tryon"""
    global facade_generator, user_house_photos
    
    user_id = update.effective_user.id
    
    if not context.args:
        await update.message.reply_text(
            "Укажите название или артикул кирпича:\n`/tryon Aalborg`", 
            parse_mode="Markdown"
        )
        return
        
    brick_slug = context.args[0].lower()
    
    # 1. Если сообщение содержит фото (через Caption или прямой вызов из handle_photo)
    image_bytes = None
    if update.message.photo:
         # Загружаем фото из текущего сообщения
         try:
            photo_file = await update.message.photo[-1].get_file()
            from io import BytesIO
            out = BytesIO()
            await photo_file.download_to_memory(out)
            out.seek(0)
            image_bytes = out.read()
            # Обновляем контекст
            user_house_photos[user_id] = image_bytes
         except Exception as e:
             logger.error(f"Error loading photo for tryon: {e}")
             
    # 2. Если нет, берем из контекста
    if not image_bytes:
        if user_id in user_house_photos:
            image_bytes = user_house_photos[user_id]
        else:
            await update.message.reply_text(
                "Сначала отправьте фотографию вашего дома! 📸\n"
                "Или отправьте фото сразу с подписью `/tryon название`"
            )
            return
        
    await update.message.reply_text(f"🎨 Генерирую фасад с кирпичом *{brick_slug}*...\nЭто может занять 10-20 секунд.", parse_mode="Markdown")
    
    try:
        # Запускаем генерацию (в отдельном потоке, чтобы не блочить бота)
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            facade_generator.generate_facade, 
            image_bytes, 
            brick_slug, 
            None
        )
        
        if result:
            await update.message.reply_photo(result, caption=f"Ваш дом с кирпичом {brick_slug}")
        else:
            await update.message.reply_text("😔 Не удалось сгенерировать изображение. Попробуйте другое фото или кирпич.")
            
    except Exception as e:
        logger.error(f"Tryon error: {e}")
        await update.message.reply_text(f"Ошибка генерации: {e}")


async def photo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Инструкция по поиску по фото"""
    await update.message.reply_text(
        "📸 *Поиск по фото*\n\n"
        "Просто отправьте мне фотографию кирпича (без сжатия или обычным фото), "
        "и я найду похожие варианты в каталоге.\n\n"
        "Я анализирую цвет, текстуру и стиль.",
        parse_mode="Markdown"
    )


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик фотографий"""
    global image_searcher, user_house_photos
    
    user_id = update.effective_user.id
    photo_file = await update.message.photo[-1].get_file()
    
    # Проверяем наличие подписи-команды
    caption = update.message.caption or ""
    if caption.strip().startswith("/"):
        command = caption.split()[0].lower()
        args = caption.split()[1:]
        
        if command == "/tryon":
            context.args = args
            await tryon(update, context)
            return
        elif command == "/search":
            context.args = args
            await search(update, context)
            return
            
    await update.message.reply_text("🔎 Анализирую изображение...")
    
    try:
        from io import BytesIO
        out = BytesIO()
        await photo_file.download_to_memory(out)
        out.seek(0)
        image_bytes = out.read()
        
        # !!! Сохраняем фото в контекст пользователя !!!
        user_house_photos[user_id] = image_bytes
        
        # Ищем похожие
        results = image_searcher.search_by_image(image_bytes, n_results=5)
        response = image_searcher.format_results(results)
        
        await update.message.reply_text(
            response + "\n\n💡 *Совет:* Если это фото дома, используйте `/tryon <кирпич>`, чтобы примерить новый фасад!",
            parse_mode="Markdown"
        )
            
    except Exception as e:
        logger.error(f"Image search error: {e}")
        await update.message.reply_text(f"Ошибка: {e}")


async def post_init(application: Application):
    """Действия после инициализации приложения"""
    await application.bot.set_my_commands([
        ("start", "👋 Приветствие и режимы"),
        ("help", "ℹ️ Справка и примеры"),
        ("search", "🔍 Строгий поиск кирпича"),
        ("photo", "📸 Поиск по фото"),
        ("tryon", "🏠 Примерка фасада"),
    ])


def main():
    """Запуск бота"""
    global consultant, image_searcher, facade_generator
    
    # Загружаем токен из settings
    from config.settings import TELEGRAM_BOT_TOKEN
    token = TELEGRAM_BOT_TOKEN
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не найден!")
        return
    
    print("🚀 Инициализация консультанта...")
    consultant = BrickConsultant()
    
    print("👁️ Инициализация визуального поиска...")
    image_searcher = ImageSearch()
    
    print("🏠 Инициализация генератора фасадов...")
    facade_generator = FacadeGenerator()
    
    print("🤖 Запуск Telegram бота...")
    
    # Создаем приложение
    app = Application.builder().token(token).post_init(post_init).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("tryon", tryon))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("photo", photo_command))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем
    print("✅ Бот запущен! Нажмите Ctrl+C для остановки.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

import os
import json
import logging
import asyncio
import time
from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
    ContextTypes,
)
from utils.userbot_engine import UserbotEngine
from utils.queue_manager import QueueManager
from utils.language import get_text
from utils.user_config import UserConfig
from utils.ad_manager import AdManager

logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='%(asctime)s — %(levelname)s — %(message)s'
)

BOT_TOKEN = os.environ.get('BOT_TOKEN')
CREATOR_ID = int(os.environ.get('CREATOR_ID'))
HYDRAX_API_ID = os.environ.get('HYDRAX_API_ID')

queue_manager = QueueManager()
userbot_engine = UserbotEngine()
user_config = UserConfig()
ad_manager = AdManager()
LANG_PATH = "lang"

def update_user_list(user_id):
    users_file = "users.json"
    try:
        if not os.path.exists(users_file):
            users = []
        else:
            with open(users_file, "r") as f:
                users = json.load(f)
        if user_id not in users:
            users.append(user_id)
            with open(users_file, "w") as f:
                json.dump(users, f)
    except Exception as e:
        logging.error(f"Error updating user list: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_config.init_user(user_id)
    update_user_list(user_id)
    await update.message.reply_text(get_text(user_id, "welcome"))

async def setlang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    keyboard = [
        [
            InlineKeyboardButton("🇪🇸 Español", callback_data="lang_es"),
            InlineKeyboardButton("🇺🇸 English", callback_data="lang_en"),
        ]
    ]
    await update.message.reply_text(
        get_text(user_id, "choose_lang"),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if query.data == "lang_es":
        user_config.set_lang(user_id, "es")
        await query.edit_message_text(get_text(user_id, "lang_set_es"))
    elif query.data == "lang_en":
        user_config.set_lang(user_id, "en")
        await query.edit_message_text(get_text(user_id, "lang_set_en"))
    elif query.data.startswith("ad_yes") or query.data.startswith("ad_no"):
        await ad_manager.handle_callback(query, user_id, context)
    elif query.data == "hapi_yes":
        # Confirmar el cambio de la API de Hydrax para el usuario
        pending_api = user_config.get_pending_hydrax_api(user_id)
        if pending_api:
            user_config.set_hydrax_api(user_id, pending_api)
            await query.edit_message_text(get_text(user_id, "hapi_set").format(pending_api))
        else:
            await query.edit_message_text(get_text(user_id, "hapi_error"))
    elif query.data == "hapi_no":
        user_config.clear_pending_hydrax_api(user_id)
        await query.edit_message_text(get_text(user_id, "hapi_cancel"))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, "help"))

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    queue = queue_manager.get_queue(user_id)
    if not queue:
        await update.message.reply_text(get_text(user_id, "queue_empty"))
    else:
        msg = get_text(user_id, "queue_list") + "\n" + "\n".join([str(i+1)+". "+item['name'] for i, item in enumerate(queue)])
        await update.message.reply_text(msg)

async def cancel_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    queue_manager.cancel_queue(user_id)
    await update.message.reply_text(get_text(user_id, "queue_cancelled"))

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    queue_manager.cancel_queue(user_id)
    await update.message.reply_text(get_text(user_id, "cancelled"))

async def add_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != CREATOR_ID:
        await update.message.reply_text(get_text(user_id, "not_admin"))
        return
    try:
        target_id = int(context.args[0])
        result = user_config.set_authorized(target_id, True)
        if result:
            await update.message.reply_text(get_text(user_id, "user_added").format(target_id))
        else:
            await update.message.reply_text(get_text(user_id, "user_already"))
    except Exception:
        await update.message.reply_text(get_text(user_id, "add_usage"))

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != CREATOR_ID:
        await update.message.reply_text(get_text(user_id, "not_admin"))
        return
    try:
        target_id = int(context.args[0])
        result = user_config.set_authorized(target_id, False)
        if result:
            await update.message.reply_text(get_text(user_id, "user_removed").format(target_id))
        else:
            await update.message.reply_text(get_text(user_id, "user_notfound"))
    except Exception:
        await update.message.reply_text(get_text(user_id, "remove_usage"))

async def log_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != CREATOR_ID:
        await update.message.reply_text(get_text(user_id, "not_admin"))
        return
    if os.path.exists("bot.log"):
        await update.message.reply_document(document=InputFile("bot.log"), caption=get_text(user_id, "log_sent"))
    else:
        await update.message.reply_text(get_text(user_id, "log_notfound"))

async def ads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != CREATOR_ID:
        await update.message.reply_text(get_text(user_id, "not_admin"))
        return
    await ad_manager.start_ads_process(update, context)

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    start_time = time.time()
    msg = await update.message.reply_text(get_text(user_id, "ping_wait"))
    end_time = time.time()
    latency = int((end_time - start_time) * 1000)
    await msg.edit_text(get_text(user_id, "ping_result").format(latency))

async def server_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(get_text(user_id, "server_info"))

async def hapi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_config.is_authorized(user_id):
        await update.message.reply_text(get_text(user_id, "not_authorized"))
        return
    await update.message.reply_text(get_text(user_id, "hapi_prompt"))

async def hapi_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_config.is_authorized(user_id):
        return
    api = update.message.text.strip()
    user_config.set_pending_hydrax_api(user_id, api)
    keyboard = [
        [InlineKeyboardButton("✅ Sí", callback_data="hapi_yes"),
         InlineKeyboardButton("🚫 No", callback_data="hapi_no")]
    ]
    await update.message.reply_text(get_text(user_id, "hapi_confirm").format(api), reply_markup=InlineKeyboardMarkup(keyboard))

async def video_or_link_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    update_user_list(user_id)
    if not user_config.is_authorized(user_id):
        await update.message.reply_text(get_text(user_id, "not_authorized"))
        return
    # Obtener la API Hydrax del usuario (o la default)
    hydrax_api = user_config.get_hydrax_api(user_id) or HYDRAX_API_ID
    if update.message.video:
        video = update.message.video
        file_id = video.file_id
        name = video.file_name or f"video_{file_id}.mp4"
        queue_manager.add_to_queue(user_id, {"type": "tg_video", "file_id": file_id, "name": name})
        await update.message.reply_text(get_text(user_id, "added_queue").format(name))
        asyncio.create_task(queue_manager.process_queue(user_id, context.bot, userbot_engine, hydrax_api))
    elif update.message.text and update.message.text.startswith("http"):
        url = update.message.text.strip()
        name = url.split("/")[-1]
        queue_manager.add_to_queue(user_id, {"type": "url", "url": url, "name": name})
        await update.message.reply_text(get_text(user_id, "added_queue").format(name))
        asyncio.create_task(queue_manager.process_queue(user_id, context.bot, userbot_engine, hydrax_api))
    # Mensaje de Hydrax API para /hapi
    elif update.message.text and user_config.is_waiting_hapi(user_id):
        await hapi_message_handler(update, context)
    # Mensaje de ad_manager proceso de anuncios
    elif user_id in ad_manager.states and ad_manager.states[user_id]["step"] == "collect":
        await ad_manager.process_ad_message(update)

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("setlang", setlang))
    application.add_handler(CommandHandler("ayuda", help_command))
    application.add_handler(CommandHandler("list", list_command))
    application.add_handler(CommandHandler("cancel_list", cancel_list_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("add", add_command))
    application.add_handler(CommandHandler("remove", remove_command))
    application.add_handler(CommandHandler("log", log_command))
    application.add_handler(CommandHandler("ads", ads_command))
    application.add_handler(CommandHandler("ping", ping_command))
    application.add_handler(CommandHandler("server", server_command))
    application.add_handler(CommandHandler("hapi", hapi_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(
        filters.Video | filters.Regex(r'^https?:\/\/') | filters.TEXT,
        video_or_link_handler
    ))
    application.run_polling()

if __name__ == '__main__':
    main()
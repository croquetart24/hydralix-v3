import os
import json
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

class AdManager:
    def __init__(self):
        # Para guardar el estado por usuario de anuncios
        self.states = {}

    async def start_ads_process(self, update, context):
        user_id = update.effective_user.id
        self.states[user_id] = {"msgs": [], "step": "collect"}
        await update.message.reply_text(
            "Envia el texto del anuncio (puedes enviar varios mensajes). Cuando termines, haz clic en 'Sí' abajo.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ Sí", callback_data="ad_yes_step1"),
                 InlineKeyboardButton("🚫 No", callback_data="ad_no_cancel")]]))

    async def handle_callback(self, query, user_id, context):
        state = self.states.get(user_id)
        if not state:
            await query.edit_message_text("No hay proceso de anuncio en curso.")
            return
        # Recibe confirmación para terminar de añadir mensajes
        if query.data == "ad_yes_step1":
            # Mostrar preview y pedir confirmación de envío
            ad_preview = "\n".join(state["msgs"])
            await query.edit_message_text(
                f"Previsualización del anuncio:\n\n{ad_preview}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Sí, enviar", callback_data="ad_yes_send"),
                     InlineKeyboardButton("🚫 No, cancelar", callback_data="ad_no_cancel")]]))
            state["step"] = "confirm"
        elif query.data == "ad_yes_send":
            # Enviar anuncio a todos los usuarios
            await self.send_ad_to_all(user_id, context, "\n".join(state["msgs"]), query)
            del self.states[user_id]
        elif query.data.startswith("ad_no"):
            await query.edit_message_text("Operación cancelada.")
            del self.states[user_id]

    async def send_ad_to_all(self, user_id, context, ad_text, query):
        users_file = "users.json"
        blocked = 0
        sent = 0
        total = 0
        if not os.path.exists(users_file):
            await query.edit_message_text("No hay usuarios registrados.")
            return
        with open(users_file, "r") as f:
            users = json.load(f)
        total = len(users)
        status_msg = await query.edit_message_text(f"Enviando anuncio... (0/{total})")
        for idx, uid in enumerate(users):
            try:
                await context.bot.send_message(chat_id=uid, text=ad_text)
                sent += 1
            except Exception:
                blocked += 1
            await status_msg.edit_text(f"Enviando anuncio... ({idx+1}/{total})\nEnviados: {sent} | Bloqueados: {blocked}")
            await asyncio.sleep(0.5)
        await status_msg.edit_text(f"Anuncio enviado.\nTotal: {total}\nEnviados: {sent}\nBloqueados: {blocked}")

    async def process_ad_message(self, update):
        user_id = update.effective_user.id
        if user_id not in self.states:
            return
        state = self.states[user_id]
        if state["step"] == "collect":
            state["msgs"].append(update.message.text)
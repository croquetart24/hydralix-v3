import os
import json
import time
import requests
import asyncio

class QueueManager:
    def __init__(self):
        self.queues = {}
        self.processing = {}
        self.load_queues()

    def queue_file(self, user_id):
        return f"user_{user_id}_queue.json"

    def load_queues(self):
        # Cargar todas las colas existentes
        for fname in os.listdir():
            if fname.startswith("user_") and fname.endswith("_queue.json"):
                user_id = int(fname.split("_")[1])
                with open(fname, "r") as f:
                    self.queues[user_id] = json.load(f)

    def save_queue(self, user_id):
        with open(self.queue_file(user_id), "w") as f:
            json.dump(self.queues.get(user_id, []), f)

    def get_queue(self, user_id):
        return self.queues.get(user_id, [])

    def add_to_queue(self, user_id, item):
        self.queues.setdefault(user_id, []).append(item)
        self.save_queue(user_id)

    def cancel_queue(self, user_id):
        self.queues[user_id] = []
        self.save_queue(user_id)
        self.processing[user_id] = False

    async def process_queue(self, user_id, bot, userbot_engine, hydrax_api):
        if self.processing.get(user_id, False):
            return  # Ya está procesando la cola
        queue = self.get_queue(user_id)
        if not queue:
            return
        self.processing[user_id] = True
        for idx, item in enumerate(list(queue)):
            name = item["name"]
            msg = await bot.send_message(chat_id=user_id, text=f"Procesando: {name}\n[{idx+1}/{len(queue)}]")
            temp_path = f"temp/{name}"
            if not os.path.exists("temp"):
                os.makedirs("temp")
            # Descargar el archivo
            download_ok = False
            try:
                if item["type"] == "tg_video":
                    await self.progress_bar(bot, msg, 0, 100, get_text(user_id, "progress_down").format(name))
                    await userbot_engine.download_video(item["file_id"], temp_path, lambda prog: asyncio.run(self.progress_bar(bot, msg, prog, 100, get_text(user_id, "progress_down").format(name))))
                    download_ok = True
                elif item["type"] == "url":
                    await self.progress_bar(bot, msg, 0, 100, get_text(user_id, "progress_down").format(name))
                    await userbot_engine.download_url(item["url"], temp_path, lambda prog: asyncio.run(self.progress_bar(bot, msg, prog, 100, get_text(user_id, "progress_down").format(name))))
                    download_ok = True
            except Exception as e:
                await msg.edit_text(get_text(user_id, "download_error").format(name, str(e)))
            if not download_ok:
                continue
            # Subir a Hydrax
            try:
                await self.progress_bar(bot, msg, 0, 100, get_text(user_id, "progress_up").format(name))
                with open(temp_path, "rb") as f:
                    files = {'file': (name, f, 'video/mp4')}
                    r = requests.post(f"http://up.hydrax.net/{hydrax_api}", files=files)
                    await self.progress_bar(bot, msg, 100, 100, get_text(user_id, "progress_up").format(name))
                    await msg.edit_text(get_text(user_id, "upload_done").format(name, r.text))
            except Exception as e:
                await msg.edit_text(get_text(user_id, "upload_error").format(name, str(e)))
            try:
                os.remove(temp_path)
            except Exception:
                pass
            # Eliminar de la cola y guardar
            self.queues[user_id] = self.queues.get(user_id, [])[1:]
            self.save_queue(user_id)
            # Mostrar próximo elemento
            next_item = self.queues.get(user_id, [])
            if next_item:
                await bot.send_message(chat_id=user_id, text=get_text(user_id, "next_in_queue").format(next_item[0]["name"]))
            if not self.processing.get(user_id, True):
                await bot.send_message(chat_id=user_id, text=get_text(user_id, "cancelled"))
                break
        self.processing[user_id] = False

    async def progress_bar(self, bot, msg, current, total, action_text=""):
        # Barra de progreso visual en mensaje editado
        percentage = int((current / total) * 100) if total else 0
        bar_len = 20
        filled_len = int(bar_len * percentage // 100)
        bar = "█" * filled_len + "░" * (bar_len - filled_len)
        await msg.edit_text(f"{action_text}\n[{bar}] {percentage}%")
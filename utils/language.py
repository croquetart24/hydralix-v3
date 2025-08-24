import json
import os

class Language:
    def __init__(self):
        self.languages = {}
        self.load_languages()

    def load_languages(self):
        for lang_code in ["es", "en"]:
            with open(f"lang/{lang_code}.json", "r", encoding="utf-8") as f:
                self.languages[lang_code] = json.load(f)

lang_obj = Language()

def get_text(user_id, key):
    # Leer idioma del usuario
    try:
        with open(f"user_{user_id}_config.json", "r") as f:
            config = json.load(f)
            lang = config.get("lang", "en")
    except:
        lang = "en"
    return lang_obj.languages.get(lang, {}).get(key, f"[{key}]")
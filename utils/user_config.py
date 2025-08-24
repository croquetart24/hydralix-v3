import os
import json

class UserConfig:
    def __init__(self):
        pass

    def config_file(self, user_id):
        return f"user_{user_id}_config.json"

    def init_user(self, user_id):
        if not os.path.exists(self.config_file(user_id)):
            config = {"lang": "en", "authorized": False, "hydrax_api": "", "pending_hapi": ""}
            if user_id == int(os.environ.get("CREATOR_ID")):
                config["authorized"] = True
            with open(self.config_file(user_id), "w") as f:
                json.dump(config, f)

    def set_lang(self, user_id, lang_code):
        with open(self.config_file(user_id), "r") as f:
            config = json.load(f)
        config["lang"] = lang_code
        with open(self.config_file(user_id), "w") as f:
            json.dump(config, f)

    def is_authorized(self, user_id):
        try:
            with open(self.config_file(user_id), "r") as f:
                config = json.load(f)
            return config.get("authorized", False)
        except Exception:
            return False

    def set_authorized(self, user_id, authorized):
        config_path = self.config_file(user_id)
        if not os.path.exists(config_path) and not authorized:
            return False
        if not os.path.exists(config_path):
            config = {"lang": "en", "authorized": False, "hydrax_api": "", "pending_hapi": ""}
        else:
            with open(config_path, "r") as f:
                config = json.load(f)
        prev = config.get("authorized", False)
        config["authorized"] = authorized
        with open(config_path, "w") as f:
            json.dump(config, f)
        if prev == authorized:
            return False
        return True

    def set_hydrax_api(self, user_id, api):
        with open(self.config_file(user_id), "r") as f:
            config = json.load(f)
        config["hydrax_api"] = api
        config["pending_hapi"] = ""
        with open(self.config_file(user_id), "w") as f:
            json.dump(config, f)

    def get_hydrax_api(self, user_id):
        try:
            with open(self.config_file(user_id), "r") as f:
                config = json.load(f)
            return config.get("hydrax_api", "")
        except Exception:
            return ""

    def set_pending_hydrax_api(self, user_id, api):
        with open(self.config_file(user_id), "r") as f:
            config = json.load(f)
        config["pending_hapi"] = api
        with open(self.config_file(user_id), "w") as f:
            json.dump(config, f)

    def get_pending_hydrax_api(self, user_id):
        try:
            with open(self.config_file(user_id), "r") as f:
                config = json.load(f)
            return config.get("pending_hapi", "")
        except Exception:
            return ""

    def clear_pending_hydrax_api(self, user_id):
        with open(self.config_file(user_id), "r") as f:
            config = json.load(f)
        config["pending_hapi"] = ""
        with open(self.config_file(user_id), "w") as f:
            json.dump(config, f)

    def is_waiting_hapi(self, user_id):
        try:
            with open(self.config_file(user_id), "r") as f:
                config = json.load(f)
            return bool(config.get("pending_hapi", ""))
        except Exception:
            return False
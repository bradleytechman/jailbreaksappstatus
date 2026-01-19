import json

class ConfigManager:
    CONFIG_FILE = "config.json"

    @staticmethod
    def load_config():
        try:
            with open(ConfigManager.CONFIG_FILE, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    @staticmethod
    def save_config(config):
        with open(ConfigManager.CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=4)

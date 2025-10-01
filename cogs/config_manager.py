import json

class ConfigManager:
    @staticmethod
    def load_config():
        try:
            with open("config.json", "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    @staticmethod
    def save_config(config):
        with open("config.json", "w") as f:
            json.dump(config, f, indent=4)

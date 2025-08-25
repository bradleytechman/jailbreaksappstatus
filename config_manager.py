import json
import os

CONFIG_FILE = "guild_config.json"

class GuildConfigManager:
    def __init__(self):
        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w") as f:
                json.dump({}, f)
        self._load()

    def _load(self):
        with open(CONFIG_FILE, "r") as f:
            try:
                self.data = json.load(f)
            except json.JSONDecodeError:
                self.data = {}

    def _save(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.data, f, indent=4)

    def get_guild_config(self, guild_id: int):
        return self.data.get(str(guild_id), {})

    def set_guild_config(self, guild_id: int, channel_id=None, ping_role_id=None, access_role_id=None):
        gid = str(guild_id)
        if gid not in self.data:
            self.data[gid] = {}
        if channel_id is not None:
            self.data[gid]["channel_id"] = channel_id
        if ping_role_id is not None:
            self.data[gid]["ping_role_id"] = ping_role_id
        if access_role_id is not None:
            self.data[gid]["access_role_id"] = access_role_id
        self._save()
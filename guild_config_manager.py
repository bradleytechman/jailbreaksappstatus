import json, os

CONFIG_FILE = "guild_config.json"

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_guild_config(guild_id):
    return load_config().get(str(guild_id), {})

def set_guild_config(guild_id, channel_id=None, role_id=None):
    data = load_config()
    gid = str(guild_id)
    if gid not in data:
        data[gid] = {}
    if channel_id is not None:
        data[gid]["channel_id"] = channel_id
    if role_id is not None:
        data[gid]["role_id"] = role_id
    save_config(data)%

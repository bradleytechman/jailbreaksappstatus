#!/bin/bash
set -e

echo "=== JailbreaksAppStatus Bot Setup ==="

read -rp "Enter your Discord bot token: " BOT_TOKEN
read -rp "Enter the Discord channel ID for status updates (optional, press enter to skip): " STATUS_CHANNEL
read -rp "Enter the role ID to ping when signed (optional, press enter to skip): " PING_ROLE
read -rp "Enter a note to include in status messages (optional, press enter to skip): " STATUS_NOTE
echo "If you wish to set change anything later like the status note, you may do so using a text editor like nano"

ENV_FILE=".env"
cat > "$ENV_FILE" <<EOF
DISCORD_BOT_TOKEN=$BOT_TOKEN
STATUS_CHANNEL_ID=$STATUS_CHANNEL
PING_ROLE_ID=$PING_ROLE
STATUS_NOTE=$STATUS_NOTE
EOF
echo ".env created"

echo "downloading bot.py from GitHub..."
curl -sSL https://raw.githubusercontent.com/bradleytechman/jailbreaksappstatus/main/bot.py -o bot.py
echo "bot.py downloaded"

echo "installing Python dependencies..."
if ! command -v pip &>/dev/null; then
    echo "pip not found, installing..."
    python3 -m ensurepip --upgrade
fi
pip install -r <(echo -e "discord.py\naiohttp\ndotenv")

echo "setup complete! you can now run the bot with:"
echo "python3 bot.py"

#!/usr/bin/env bash
set -e

# check for git
if ! command -v git &>/dev/null; then
    echo "git not found, please install it first"
    exit 1
fi

# check for python3
if ! command -v python3 &>/dev/null; then
    echo "python3 not found, please install it first"
    exit 1
fi

# clone repo
if [ ! -d "jailbreaksappstatus" ]; then
    git clone https://github.com/bradleytechman/jailbreaksappstatus.git
fi

cd jailbreaksappstatus

# create virtual environment
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi

# activate venv
source venv/bin/activate

# upgrade pip
pip install --upgrade pip

# install dependencies
pip install -r requirements.txt

# create .env
echo "setting up .env file..."
read -p "Enter DISCORD_TOKEN: " token
read -p "Enter default STATUS_NOTE (optional, press enter to skip): " note
read -p "Enter webhook URL for logging (optional, press enter to skip):" webhook

cat > .env <<EOL
DISCORD_TOKEN=$token
STATUS_NOTE=$note
WEBHOOK_URL="$webhook"
EOL

echo "setup complete!"
echo "run the bot with: source venv/bin/activate && python bot.py"
#!/bin/bash
# Wuchang AI VM Setup Script
# Run this on the Google Cloud VM (Debian/Ubuntu)

echo '============================================'
echo '   Wuchang AI - Cloud Node Initialization   '
echo '============================================'

# 1. System Update
echo '[1/5] Updating System Packages...'
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv -qq

# 2. Workspace Setup
echo '[2/5] Creating Workspace...'
mkdir -p ~/wuchang_ai
cp knowledge_sync_agent.py ~/wuchang_ai/
cp vm_requirements.txt ~/wuchang_ai/
cd ~/wuchang_ai

# 3. Environment Setup
echo '[3/5] Setting up Virtual Environment...'
python3 -m venv venv
source venv/bin/activate

# 4. Dependency Installation
echo '[4/5] Installing Python Dependencies...'
pip install -r vm_requirements.txt

# 5. Service Registration
echo '[5/5] Registering System Service...'
USER_NAME=$(whoami)
SERVICE_FILE=/etc/systemd/system/wuchang-sync.service

# Create service file
sudo bash -c "cat > $SERVICE_FILE << EOL
[Unit]
Description=Wuchang AI Knowledge Sync Agent
After=network.target

[Service]
User=$USER_NAME
WorkingDirectory=/home/$USER_NAME/wuchang_ai
ExecStart=/home/$USER_NAME/wuchang_ai/venv/bin/python /home/$USER_NAME/wuchang_ai/knowledge_sync_agent.py
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
EOL"

# Reload Daemon
sudo systemctl daemon-reload
echo '============================================'
echo '   Setup Complete!                          '
echo '   To start the agent: sudo systemctl start wuchang-sync'
echo '   To check status:    sudo systemctl status wuchang-sync'
echo '============================================'

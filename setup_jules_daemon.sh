#!/bin/bash
WORK_DIR=$(pwd)
CURRENT_USER=$(whoami)
SERVICE_FILE="/etc/systemd/system/wuchang-jules.service"

echo "🛡️ 正在向 Linux 核心註冊 Wuchang OS 守護進程..."
sudo bash -c "cat << 'INNER_EOF' > $SERVICE_FILE
[Unit]
Description=Wuchang OS - Jules Grand Unified Core (V21.4)
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$WORK_DIR
ExecStart=$WORK_DIR/jules_env/bin/python3 $WORK_DIR/jules_core_v21_4.py
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=wuchang-jules

[Install]
WantedBy=multi-user.target
INNER_EOF"

sudo systemctl daemon-reload
sudo systemctl enable wuchang-jules.service
sudo systemctl start wuchang-jules.service

echo "✅ Wuchang OS 守護進程已啟動！"

#!/bin/bash

SERVICE=/etc/systemd/system/taiji.service

sudo bash -c "cat > $SERVICE" <<EOF
[Unit]
Description=Taiji Distributed Queue System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/full_system.sh
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable taiji
sudo systemctl restart taiji

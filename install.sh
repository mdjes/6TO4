#!/bin/bash

# Ensure script is run as root
if [ "$EUID" -ne 0 ]; then
  echo -e "\e[31mPlease run as root (sudo -i)\e[0m"
  exit 1
fi

echo -e "\e[34m[1/4] Installing required packages...\e[0m"
apt-get update -q
apt-get install -y -q python3 python3-pip git curl python3-flask

echo -e "\e[34m[2/4] Downloading project from GitHub...\e[0m"
rm -rf /opt/6TO4
git clone https://github.com/mdjes/6TO4.git /opt/6TO4
cd /opt/6TO4

echo -e "\e[34m[3/4] Configuring Web Panel...\e[0m"
# Attempt to install flask via pip just in case apt failed
pip3 install flask --break-system-packages >/dev/null 2>&1 || pip3 install flask >/dev/null 2>&1

# Generate random password and secret key
PASSWORD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 10 | head -n 1)
SECRET_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)

# Apply settings to app.py
sed -i "s/PASSWORD = 'admin'/PASSWORD = '${PASSWORD}'/g" app.py
sed -i "s/super_secret_key_change_in_production/${SECRET_KEY}/g" app.py
sed -i "s/port=5000/port=8820/g" app.py

echo -e "\e[34m[4/4] Setting up background service...\e[0m"
cat <<EOF > /etc/systemd/system/6to4web.service
[Unit]
Description=6To4 Web Panel Dashboard
After=network.target

[Service]
User=root
WorkingDirectory=/opt/6TO4
ExecStart=/usr/bin/python3 /opt/6TO4/app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable 6to4web
systemctl restart 6to4web

# Allow port 8820 in ufw if it's active
if command -v ufw >/dev/null 2>&1; then
    ufw allow 8820/tcp >/dev/null 2>&1
fi

# Get Public IPv4 (Guaranteed IPv4 only APIs)
PUBLIC_IP=$(curl -s -4 api.ipify.org)
if [ -z "$PUBLIC_IP" ]; then
    PUBLIC_IP=$(curl -s -4 ipv4.icanhazip.com)
fi
if [ -z "$PUBLIC_IP" ]; then
    # Fallback to fetching primary local IPv4 address
    PUBLIC_IP=$(ip -4 route get 8.8.8.8 | awk '{print $7}' | head -n 1)
fi

echo -e "\e[32m====================================================\e[0m"
echo -e "\e[32m✅ نصب با موفقیت انجام شد (Installation Successful)\e[0m"
echo -e ""
echo -e "\e[36m🌐 URL  : \e[0mhttp://${PUBLIC_IP}:8820"
echo -e "\e[36m🔑 Password : \e[0m${PASSWORD}"
echo -e "\e[32m====================================================\e[0m"

#!/bin/bash

# Clear screen
clear
echo -e "\e[36m====================================================\e[0m"
echo -e "\e[36m                 6TO4 TUNNEL PANEL                  \e[0m"
echo -e "\e[36m====================================================\e[0m"

# Check root
if [ "$EUID" -ne 0 ]; then
  echo -e "\e[31mPlease run as root!\e[0m"
  exit 1
fi

EXISTING_PASSWORD=""
EXISTING_SECRET=""

# Check if already installed
if [ -d "/opt/6TO4/web" ] && [ -f "/opt/6TO4/web/app.py" ]; then
    EXISTING_PASSWORD=$(grep -oP "(?<=PASSWORD = ')[^']*" /opt/6TO4/web/app.py | head -n 1)
    EXISTING_SECRET=$(grep -oP "(?<=secret_key = ')[^']*" /opt/6TO4/web/app.py | head -n 1)
    
    echo -e "\e[32m[+] 6TO4 Panel is already installed!\e[0m"
    echo -e "\e[33m1) Update Panel (Keep current password & settings)\e[0m"
    echo -e "\e[33m2) View Login Info\e[0m"
    echo -e "\e[33m3) Uninstall\e[0m"
    echo -e "\e[33m4) Exit\e[0m"
    echo ""
    read -p "Select an option [1-4]: " OPTION
    
    if [ "$OPTION" == "2" ]; then
        IP=$(curl -s4 api.ipify.org || ip -4 route get 8.8.8.8 | awk '{print $7}' | head -n 1)
        echo -e "\n\e[32m🌐 URL  : http://${IP}:8820\e[0m"
        echo -e "\e[32m🔑 Password : ${EXISTING_PASSWORD}\e[0m\n"
        exit 0
    elif [ "$OPTION" == "3" ]; then
        systemctl stop 6to4web >/dev/null 2>&1
        systemctl disable 6to4web >/dev/null 2>&1
        rm -rf /opt/6TO4
        rm -f /etc/systemd/system/6to4web.service
        systemctl daemon-reload
        echo -e "\e[31m[-] Panel completely uninstalled.\e[0m\n"
        exit 0
    elif [ "$OPTION" == "4" ]; then
        exit 0
    fi
fi

echo -e "\e[34m[1/4] Installing required packages...\e[0m"
apt-get update -q >/dev/null 2>&1
apt-get install -y -q python3 python3-pip git curl python3-flask >/dev/null 2>&1

echo -e "\e[34m[2/4] Downloading project from GitHub...\e[0m"
rm -rf /tmp/6TO4_update
git clone https://github.com/mdjes/6TO4.git /tmp/6TO4_update >/dev/null 2>&1

# Move files (preserving logic)
mkdir -p /opt/6TO4
rm -rf /opt/6TO4/web
mv /tmp/6TO4_update/web /opt/6TO4/
rm -rf /tmp/6TO4_update

echo -e "\e[34m[3/4] Configuring Web Panel...\e[0m"
# Install flask via pip fallback if apt failed
pip3 install flask --break-system-packages >/dev/null 2>&1 || pip3 install flask >/dev/null 2>&1

if [ -n "$EXISTING_PASSWORD" ]; then
    PASSWORD=$EXISTING_PASSWORD
    SECRET_KEY=$EXISTING_SECRET
else
    PASSWORD=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 10 | head -n 1)
    SECRET_KEY=$(cat /dev/urandom | tr -dc 'a-zA-Z0-9' | fold -w 32 | head -n 1)
fi

# Apply settings to web/app.py
sed -i "s/PASSWORD = 'admin'/PASSWORD = '${PASSWORD}'/g" /opt/6TO4/web/app.py
sed -i "s/super_secret_key_change_in_production/${SECRET_KEY}/g" /opt/6TO4/web/app.py
sed -i "s/port=5000/port=8820/g" /opt/6TO4/web/app.py

echo -e "\e[34m[4/4] Setting up background service...\e[0m"
cat <<EOF > /etc/systemd/system/6to4web.service
[Unit]
Description=6To4 Web Panel Dashboard
After=network.target

[Service]
User=root
WorkingDirectory=/opt/6TO4/web
ExecStart=/usr/bin/python3 /opt/6TO4/web/app.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload >/dev/null 2>&1
systemctl enable 6to4web >/dev/null 2>&1
systemctl restart 6to4web >/dev/null 2>&1

# Allow port 8820 in UFW
if command -v ufw >/dev/null 2>&1; then
    ufw allow 8820/tcp >/dev/null 2>&1
fi

IP=$(curl -s4 api.ipify.org || ip -4 route get 8.8.8.8 | awk '{print $7}' | head -n 1)

echo -e "\e[32m====================================================\e[0m"
echo -e "\e[32m✅ نصب/آپدیت با موفقیت انجام شد (Installation Successful)\e[0m"
echo -e ""
echo -e "\e[32m🌐 URL  : http://${IP}:8820\e[0m"
echo -e "\e[32m🔑 Password : ${PASSWORD}\e[0m"
echo -e "\e[32m====================================================\e[0m"

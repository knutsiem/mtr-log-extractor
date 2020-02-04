#!/bin/sh

script_dir=`dirname $0`

echo "MTR connected. Running pre-start operations..."

echo "Cancelling any scheduled shutdown to allow re-running if reconnected..."
python3 "$script_dir/pijuice-poweroff.py" --cancel
sudo shutdown -c

echo "Restarting timesyncd service to trigger time update..."
sudo systemctl restart systemd-timesyncd

echo "Connect to mobile network via PPP..."
if sudo pon; then
    echo "Connect succeeded, adding default route for ppp0..."
    sudo route add default ppp0
else
    echo "Connect failed"
fi

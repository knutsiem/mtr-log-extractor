#!/bin/sh

script_dir=`dirname $0`

shutdown_delay_mins=1
pijuice_poweroff_delay_secs=90  # must be greater than the shutdown delay + time needed for shutdown 

echo "MTR log extract ended (SERVICE_RESULT=$SERVICE_RESULT, EXIT_CODE=$EXIT_CODE, EXIT_STATUS=$EXIT_STATUS). Running post-stop operations..."

echo "Disconnecting from mobile network..."
if sudo poff; then
    echo "Disconnect succeeded"
else
    echo "Disconnect failed"
fi

echo "Scheduling shutdown in $shutdown_delay_mins minute(s) and power-off in $pijuice_poweroff_delay_secs second(s) to conserve battery power..."
python3 "$script_dir/pijuice-poweroff.py" --delay $pijuice_poweroff_delay_secs
sudo shutdown "+$shutdown_delay_mins"

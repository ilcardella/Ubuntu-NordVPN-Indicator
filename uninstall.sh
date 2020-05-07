#!/bin/bash

echo "Removing Ubuntu NordVPN Indicator"
rm ~/.config/autostart/ubuntu-nordvpn-indicator.desktop
sudo rm -rf /opt/ubuntu-nordvpn-indicator

read -p "Do you want to uninstall AppIndicator? [Y/n]" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Uninstalling AppIndicator"
    sudo apt-get remove -y gir1.2-appindicator
fi

read -p "Do you want to uninstall Python-GI? [Y/n]" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Uninstalling Python3-GI"
    sudo apt-get remove -y python3-gi
fi


read -p "Do you want to uninstall NordVPN? [Y/n]" -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "Disconnecting NordVPN"
    nordvpn disconnect

    echo "Uninstalling NordVPN"
    sudo apt-get remove -y nordvpn
fi

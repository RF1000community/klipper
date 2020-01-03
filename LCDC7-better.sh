#!/bin/bash
#
# Originally this was used, but replacement is direly needed:
# https://github.com/goodtft/LCD-show
#
# Credit for most of the script goes to fschlaef. His script for a
# slightly different screen can be found at
# https://github.com/fschlaef/raspi-lcd
# distributed under the MIT license:
#
# MIT License
# 
# Copyright (c) 2019 François Schlaefli
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root" 
   exit 1
fi

usage() {
    echo "usage: $0 [-ufh] [-r <DEG>]"
    echo "  -u | --uninstall              uninstall driver"
    echo "  -f | --force                  force"
    echo "  -h | --help                   display help"
    echo "  -r | --rotate <0|90|180|270>  rotate DEG degrees. Assumes 0"
    exit 1
}


FORCE=0
UNINSTALL=0
ROTATE=0

# Parsing arguments
while [ "$1" != "" ]; do
    case $1 in
        -f | --force)
		FORCE=1
		;;
	-u | --uninstall)
    		UNINSTALL=1
                ;;
        -h | --help )
                usage
	        exit
	        ;;
        -r | --rotate)
                ROTATE=$2
                shift
                ;;     
        * )     
	    	echo "Invalid parameter $1"
    		usage
	    	exit 1
    esac
    shift
done

# Testing if machine is a Raspberry Pi or not
machine_is_raspi=$(grep -c "Raspberry Pi" /proc/device-tree/model)
if (( ! machine_is_raspi )) && (( $FORCE == 0 ))
then
	echo "This script is only compatible with Raspberry Pi."
        echo "Use -f to ignore this warning and proceed anyway."
	exit 1
fi

old='#OLD_CONFIG_'
new='#LCD_CUSTOM_CONFIG'
bootconfig=/boot/config.txt

restore_boot_config() {
	echo "Restoring $bootconfig values ..."
	
	# Remove our config
	sed -i "/$new$/d" $bootconfig

	# Restore old config
	sed -i "s/$old//" $bootconfig

        echo "Restoring 40-libinput.conf..."
        # Restore old libinput.conf
        mv -f /etc/X11/xorg.conf.d/40-libinput.conf.OLD_CONFIG /etc/X11/xorg.conf.d/40-libinput.conf
}

if (( $UNINSTALL == 1 )); then
	echo "Uninstalling ..."
	restore_boot_config
	echo "Uninstall done. A reboot is needed."
	exit 0
fi

# New boot config for LCD display
declare -A boot_config
boot_config=(
        [dtparam=i2c_arm]="on"
        [dtparam=spi]="on"
        [enable_uart]="1"
        [max_usb_current]="1"
	[hdmi_force_hotplug]="1"
	[config_hdmi_boost]="7"
	[hdmi_drive]="1"
	[hdmi_group]="2"
	[hdmi_mode]="87"
	[hdmi_cvt]="1024 600 60 6 0 0 0"
	[display_hdmi_rotate]="0"
        [hdmi_blanking]="1"
)

case $ROTATE in
        0)
                MATRIX="1 0 0 0 1 0 0 0 1"
                ;;
        90)
                boot_config[display_hdmi_rotate]="1"
                MATRIX="0 1 0 -1 0 1 0 0 1"
                ;;
        180)
                boot_config[display_hdmi_rotate]="2"
                MATRIX="-1 0 1 0 -1 1 0 0 1"
                ;;
        270)
                boot_config[display_hdmi_rotate]="3"
                MATRIX="0 -1 1 1 0 0 0 0 1"
                ;;
        *)
                echo "Invalid rotation value $ROTATE"
                usage
                exit 1
esac

# Create xorg.conf.d folder if not already existing
if [ ! -d /etc/X11/xorg.conf.d ]
then
        mkdir -p /etc/X11/xorg.conf.d
fi

# Backup 40-libinput.conf
if [ -e /etc/X11/xorg.conf.d/40-libinput.conf ] && [ ! -e /etc/X11/xorg.conf.d/40-libinput.conf.OLD_CONFIG ]
then
        echo "/etc/X11/xorg.conf.d/40-libinput.conf already exists. Creating backup.."
        cp /etc/X11/xorg.conf.d/40-libinput.conf /etc/X11/xorg.conf.d/40-libinput.conf.OLD_CONFIG
fi

# Write new config, dependent on touchpad transformation Matrix
cat > /etc/X11/xorg.conf.d/40-libinput.conf <<EOF
Section "InputClass"
        Identifier "libinput pointer catchall"
        MatchIsPointer "on"
        MatchDevicePath "/dev/input/event*"
        Driver "libinput"
EndSection

Section "InputClass"
        Identifier "libinput keyboard catchall"
        MatchIsKeyboard "on"
        MatchDevicePath "/dev/input/event*"
        Driver "libinput"
EndSection

Section "InputClass"
        Identifier "libinput touchpad catchall"
        MatchIsTouchpad "on"
        MatchDevicePath "/dev/input/event*"
        Driver "libinput"
EndSection

Section "InputClass"
        Identifier "libinput touchscreen catchall"
        MatchIsTouchscreen "on"
	Option "CalibrationMatrix" "$MATRIX"
        MatchDevicePath "/dev/input/event*"
        Driver "libinput"
EndSection

Section "InputClass"
        Identifier "libinput tablet catchall"
        MatchIsTablet "on"
        MatchDevicePath "/dev/input/event*"
        Driver "libinput"
EndSection
EOF


if grep -q $new $bootconfig; then
        echo "LCD configuration found in $bootconfig. Rewriting config..."
        # Remove our new config, so it won't get saved as old
        sed -i "/$new$/d" $bootconfig
fi

write_boot_config() {
	echo "Saving $bootconfig current values and writing new config ..."

	# Backup old config and write new one
	for i in "${!boot_config[@]}"
	do
		key=$i
		value=${boot_config[$i]}
		sed -i -r "s/^($key)/$old\1/" $bootconfig
		echo "$key=$value $new" >> "$bootconfig"
	done
}

write_boot_config

echo "Installation done. A reboot is needed to start using your touchscreen"

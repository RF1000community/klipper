#!/bin/bash
# This script installs Klipperui on a Raspberry Pi machine running Octopi, with git installed

# Find SRCDIR from the pathname of this script
SRCDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/.. && pwd )"
PYTHONDIR="${SRCDIR}/klippy-environment"



# Must be called before install_packages
setup_port_redirection()
{
    sudo iptables -A PREROUTING -t nat -p tcp --dport 80 -j REDIRECT --to-ports 8080
    echo iptables-persistent iptables-persistent/autosave_v4 boolean true | sudo debconf-set-selections
    echo iptables-persistent iptables-persistent/autosave_v6 boolean false | sudo debconf-set-selections
}



install_packages()
{
    # Packages for python cffi
    PKGLIST="python-virtualenv virtualenv python-dev libffi-dev build-essential"
    # kconfig requirements
    PKGLIST="${PKGLIST} libncurses-dev"
    # hub-ctrl
    PKGLIST="${PKGLIST} libusb-dev"
    # AVR chip installation and building
    PKGLIST="${PKGLIST} avrdude gcc-avr binutils-avr avr-libc"
    # ARM chip installation and building
    PKGLIST="${PKGLIST} stm32flash dfu-util libnewlib-arm-none-eabi"
    PKGLIST="${PKGLIST} gcc-arm-none-eabi binutils-arm-none-eabi"

    # KGUI
    PKGLIST="${PKGLIST} libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev \
    libsdl2-ttf-dev pkg-config libgl1-mesa-dev libgles2-mesa-dev \
    python-setuptools libgstreamer1.0-dev \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-omx \
    gstreamer1.0-alsa \
    python-dev libmtdev-dev \
    xclip xsel libjpeg-dev mtdev-tools xorg python-pil \
    xserver-xorg-video-fbturbo git python-pip"
    #Wifi
    PKGLIST="${PKGLIST} network-manager"
    #Usb Stick Automounting
    PKGLIST="${PKGLIST} usbmount"
    #Cura connection
    PKGLIST="${PKGLIST} iptables-persistent"

    # Update system package info
    report_status "Running apt-get update..."
    sudo apt update
    # Install desired packages
    report_status "Installing packages..."
    sudo apt install --yes ${PKGLIST}

    # Wifi 
    sudo apt purge dhcpcd5 --yes
    # change line in Xwrapper.config so xorg feels inclined to start when asked by systemd
    report_status "Xwrapper config mod..."
    sudo sed -i 's/allowed_users=console/allowed_users=anybody/' /etc/X11/Xwrapper.config
    # -i for in place (just modify file), s for substitute (this line)
}



# Step 2: Create python virtual environment
create_virtualenv()
{
    report_status "Updating python virtual environment..."
    # Create virtualenv if it doesn't already exist
    [ ! -d ${PYTHONDIR} ] && virtualenv ${PYTHONDIR}
    report_status "install pip packages..."
    # Install/update dependencies                             v  custom KGUI list of pip packages
    ${PYTHONDIR}/bin/pip install -r ${SRCDIR}/scripts/klippy-kgui-requirements.txt
}



install_klipper_service()
{
    report_status "Install klipper systemd service..."
    sudo /bin/sh -c "cat > /etc/systemd/system/klipper.service" <<EOF
[Unit]
Description="Klipper with GUI running in Xorg"
Requires=multi-user.target

[Service]
Type=simple
User=$USER
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/bin/bash -c "/usr/bin/startx ${PYTHONDIR}/bin/python ${SRCDIR}/klippy/klippy.py ${HOME}/printer.cfg -v -l /tmp/klippy.log"
Nice=-4
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF
    # -v option in ExecStart is for debugging information
    sudo chmod +x /etc/systemd/system/klipper.service
    sudo systemctl daemon-reload
    sudo systemctl enable klipper.service
}



install_usb_automounting()
{
    report_status "Install usbmount.conf..."
    mkdir -p ~/sdcard/USB-Device
    sudo cp ${SRCDIR}/klippy/extras/kgui/usbmount.conf /etc/usbmount/usbmount.conf
    #https://raspberrypi.stackexchange.com/questions/100312/raspberry-4-usbmount-not-working
    #https://www.oguska.com/blog.php?p=Using_usbmount_with_ntfs_and_exfat_filesystems
    
    #maybe needed TODO test this
    sudo sed -i 's/PrivateMounts=yes/PrivateMounts=no/' /lib/systemd/system/systemd-udevd.service
}



# Display Driver installation for kgui, 7 inch 1024*600 touchscreen
# Use custom install script in kgui directory
install_lcd_driver()
{
    report_status "Installing LCD Driver..."
    sudo ${SRCDIR}/klippy/extras/kgui/LCDC7-better.sh -r 90
    # Copy the dpms configuration
    sudo cp ${SRCDIR}/klippy/extras/kgui/10-dpms.conf /etc/X11/xorg.conf.d/
}



# Helper functions
report_status()
{
    echo -e "\n\n###### $1"
}
verify_ready()
{
    if [ "$EUID" -eq 0 ]; then
        echo "This script must not run as root"
        exit -1
    fi
}
# Force script to exit if an error occurs
set -e



# Run installation steps defined above
verify_ready
setup_port_redirection
install_packages
create_virtualenv
install_klipper_service
install_usb_automounting
install_lcd_driver

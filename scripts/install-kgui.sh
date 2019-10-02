#!/bin/bash
# This script installs Klipper on a Raspberry Pi machine running Octopi.

PYTHONDIR="${HOME}/klippy-env"

# Step 1: Install system packages
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

    # Update system package info
    report_status "Running apt-get update..."
    sudo apt-get update

    # Install desired packages
    report_status "Installing packages..."
    sudo apt-get install --yes ${PKGLIST}
}


# Git currently needs to be installed befofehand
# KGUI ######################
install_kgui()
{
    # KGUI and WIFI deps
    PKGLIST="libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev \
    pkg-config libgl1-mesa-dev libgles2-mesa-dev \
    python-setuptools libgstreamer1.0-dev \
    python-dev libmtdev-dev \
    xclip xsel libjpeg-dev mtdev-tools xorg python-pil xserver-xorg-video-fbturbo network-manager git python-pip"

    sudo apt install --yes ${PKGLIST}
    # Display Driver installation for kgui, 7 inch 1024*600 touchscreen
    sudo apt purge dhcpcd5 --yes

}
# KGUI #####################

# Step 2: Create python virtual environment
create_virtualenv()
{
    report_status "Updating python virtual environment..."

    # Create virtualenv if it doesn't already exist
    [ ! -d ${PYTHONDIR} ] && virtualenv ${PYTHONDIR}

    # Install/update dependencies                             v  custom KGUI list of pip packages
    ${PYTHONDIR}/bin/pip install -r ${SRCDIR}/scripts/klippy-kgui-requirements.txt
}

# Step 3: Install custom KGUI start script
install_script()
{
    report_status "Installing system start script..."
    # KGUI ##########
    sudo cp "${SRCDIR}/scripts/klipper-kgui-start.sh" /etc/init.d/klipper
    # KGUI ##########
    sudo update-rc.d klipper defaults
}

# Step 4: Install startup script config
install_config()
{
    DEFAULTS_FILE=/etc/default/klipper
    [ -f $DEFAULTS_FILE ] && return

    report_status "Installing system start configuration..."
    sudo /bin/sh -c "cat > $DEFAULTS_FILE" <<EOF
# Configuration for /etc/init.d/klipper

KLIPPY_USER=$USER

KLIPPY_EXEC=${PYTHONDIR}/bin/python

KLIPPY_ARGS="${SRCDIR}/klippy/klippy.py ${HOME}/printer.cfg -l /tmp/klippy.log"

EOF
}

install_lcd_driver()
{
    cd ~
    sudo rm -rf LCD-show #to allow rerunning the script without errors
    sudo git clone https://github.com/goodtft/LCD-show.git
    sudo chmod -R 755 LCD-show
    cd LCD-show/
    sudo ./LCD7C-show 90
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

# Find SRCDIR from the pathname of this script
SRCDIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/.. && pwd )"

# Run installation steps defined above
verify_ready
install_packages
install_kgui
create_virtualenv
install_script
install_config
install_lcd_driver
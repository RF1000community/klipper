#!/bin/bash
sudo systemctl stop klipper
make clean KCONFIG_CONFIG=mcu-build-config-skipr
make -j5 KCONFIG_CONFIG=mcu-build-config-skipr
./scripts/flash-sdcard.sh /dev/ttyS0 mks-skipr
make clean KCONFIG_CONFIG=mcu-build-config-rf1000
make -j5 KCONFIG_CONFIG=mcu-build-config-rf1000
make flash FLASH_DEVICE=/dev/ttyUSB0 KCONFIG_CONFIG=mcu-build-config-rf1000
sudo systemctl start klipper

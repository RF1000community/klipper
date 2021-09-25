# Support for DRV8711 stepper driver
#
# Copyright (C) 2020-2022 Martin Hierholzer <martin@hierholzer.info>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

from . import bus

ISGAIN_OPTIONS = {5: 0, 10: 1, 20: 2, 40: 3}
MODE_OPTIONS = {1: 0, 2: 1, 4: 2, 8: 3, 16: 4, 32: 5, 64: 6, 128: 7, 256: 8}
DTIME_OPTIONS = {400: 0, 450: 1, 650: 2, 850: 3}
OCPTH_OPTIONS = {250: 0, 500: 1, 750: 2, 1000: 3}
OCPDEG_OPTIONS = {1: 0, 2: 1, 4: 2, 8: 3}
TDRIVEN_OPTIONS = {250: 0, 500: 1, 1000: 2, 2000: 3}
TDRIVEP_OPTIONS = {250: 0, 500: 1, 1000: 2, 2000: 3}
IDRIVEN_OPTIONS = {100: 0, 200: 1, 300: 2, 400: 3}
IDRIVEP_OPTIONS = {50: 0, 100: 1, 150: 2, 200: 3}


class DRV8711:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name()
        self.spi = bus.MCU_SPI_from_config(config, 0, default_speed=1000000,
                                           cs_active_high=True)
        self.printer.register_event_handler(
            "klippy:connect", self.handle_connect)

        self.regs = {}

        self.regs['MODE'] = config.getchoice(
            'microsteps', MODE_OPTIONS, default=32)

        self.regs['ISGAIN'] = config.getchoice(
            'gain', ISGAIN_OPTIONS, default=20)
        gain = [k for k, v in ISGAIN_OPTIONS.items() if v ==
                self.regs['ISGAIN']][0]

        shunt = config.getfloat('shunt', 0.033)
        self.regs['TORQUE'] = \
            int(config.getfloat('current', 1.75)/2.75 * 256 * gain * shunt)

        # low-level register configuration, see datasheet for details
        self.regs['DTIME'] = config.getchoice(
            'DTIME', DTIME_OPTIONS, default=850)
        self.regs['TOFF'] = \
            int(config.getfloat('TOFF_USECS', default=76,
                minval=0.5, maxval=128.)*2) - 1
        self.regs['TBLANK'] = \
            int(config.getfloat('TBLANK_USECS',
                default=4.3, minval=1., maxval=5.12)/0.020)
        self.regs['ABT'] = config.getboolean('ABT', True)
        self.regs['TDECAY'] = \
            int(config.getfloat('TDECAY_USECS', minval=0., maxval=127.5, \
            default=24)*2)
        self.regs['DECMOD'] = config.getint(
            'DECMOD', minval=0, maxval=5, default=4)

        self.regs['OCPTH'] = config.getchoice(
            'OCPTH', OCPTH_OPTIONS, default=250)
        self.regs['OCPDEG'] = config.getchoice(
            'OCPDEG', OCPDEG_OPTIONS, default=1)
        self.regs['TDRIVEN'] = config.getchoice(
            'TDRIVEN', TDRIVEN_OPTIONS, default=2000)
        self.regs['TDRIVEP'] = config.getchoice(
            'TDRIVEP', TDRIVEP_OPTIONS, default=2000)
        self.regs['IDRIVEN'] = config.getchoice(
            'IDRIVEN', IDRIVEN_OPTIONS, default=100)
        self.regs['IDRIVEP'] = config.getchoice(
            'IDRIVEP', IDRIVEP_OPTIONS, default=50)

    def handle_connect(self):
        # Note: Some registers are kept at fixed values, since changing them
        # does not make sense for our use cases. Also stall detection is not
        # supported (yet).
        ENBL = 1
        reg0 = ENBL | (self.regs['MODE'] << 3) | (self.regs['ISGAIN'] << 8) | \
            (self.regs['DTIME'] << 10)
        self.writeRegister(0, reg0)

        reg1 = max(min(self.regs['TORQUE'], 255), 0)
        self.writeRegister(1, reg1)

        reg2 = self.regs['TOFF']
        self.writeRegister(2, reg2)

        reg3 = self.regs['TBLANK'] | self.regs['ABT'] << 8
        self.writeRegister(3, reg3)

        reg4 = self.regs['TDECAY'] | self.regs['DECMOD'] << 8
        self.writeRegister(4, reg4)

        reg5 = 0
        self.writeRegister(5, reg5)

        reg6 = self.regs['OCPTH'] | self.regs['OCPDEG'] << 2 |      \
            self.regs['TDRIVEN'] << 4 | self.regs['TDRIVEP'] << 6 |   \
            self.regs['IDRIVEN'] << 8 | self.regs['IDRIVEP'] << 10
        self.writeRegister(6, reg6)

        reg7 = 0
        self.writeRegister(7, reg7)

    def writeRegister(self, register, data):
        hi = (register << 4) | ((data & 0x0F00) >> 8)
        lo = data & 0x00FF
        self.spi.spi_send([hi, lo])


def load_config_prefix(config):
    return DRV8711(config)

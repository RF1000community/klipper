# Support for DRV8711 stepper driver
#
# Copyright (C) 2020  Martin Hierholzer <martin@hierholzer.info>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import math, logging
from . import bus

GAIN_OPTIONS = { 5:0, 10:1, 20:2, 40:3 }
USTEP_OPTIONS = { 1:0, 2:1, 4:2, 8:3, 16:4, 32:5, 64:6, 128:7, 256:8 }

class DRV8711:
  def __init__(self, config):
    self.printer = config.get_printer()
    self.name = config.get_name()
    self.spi = bus.MCU_SPI_from_config(config, 0, default_speed=1000000)
    self.printer.register_event_handler("klippy:connect", self.handle_connect)

    self.microsteps = USTEP_OPTIONS[config.getint('microsteps', 32)]
    gain = config.getint('isgain', 20)
    self.isgain = GAIN_OPTIONS[gain]
    shunt = config.getfloat('shunt', 0.033)
    self.current = int( config.getfloat('current', 1.75)/2.75 * 256 * gain * shunt )

    #ppins = self.printer.lookup_object('pins')
    #self.pin_reset = ppins.setup_pin('digital_out', config.get('reset_pin', ''))
                                          
  def handle_connect(self):
    #print_time = self.printer.lookup_object('toolhead').get_last_move_time()
    #self.pin_reset.set_digital(print_time, 0)
    logging.info("DRV8711 init "+str(self.name)+ " usteps:"+str(self.microsteps)+" current:"+str(self.current)+ " isgain:"+str(self.isgain))
      
    # See: http://www.ti.com/product/DRV8711/datasheet/detailed-description#SLVSC405764
    reg0 = 0xC01;  # 11YY 0XXX X001: ENBL = 1, RDIR = 0, RSTEP = 0, MODE = XXXX, EXSTALL = 0, ISGAIN = YY, DTIME = 11
    reg0 = reg0 | (self.microsteps << 3) | (self.isgain << 8)

    reg1 = 0x100 + max(min(self.current, 255), 0);
    
    reg2 = 0x097 # 0000 1001 0111: TOFF = 10010111, PWMMODE = 0
    reg3 = 0x1D7 # 0001 1101 0111: TBLANK = 11010111, ABT = 1
    reg4 = 0x430 # 0100 0011 0000: TDECAY = 00110000, DECMOD = 100
    reg5 = 0x83C # 1000 0011 1100: SDTHR = 00111100, SDCNT = 00, VDIV = 10
    reg6 = 0x0F0 # 0000 1111 0000: OCPTH = 00, OCPDEG = 00, TDRIVEN = 11, TDRIVEP = 11, IDRIVEN = 00, IDRIVEP = 00
    reg7 = 0x000 # 0000 0000 0000: OTS = 0, AOCP = 0, BOCP = 0, UVLO = 0, APDF = 0, BPDF = 0, STD = 0, STDLAT = 0
    
    self.writeRegister(0, reg0)
    self.writeRegister(1, reg1)
    self.writeRegister(2, reg2)
    self.writeRegister(3, reg3)
    self.writeRegister(4, reg4)
    self.writeRegister(5, reg5)
    self.writeRegister(6, reg6)
    self.writeRegister(7, reg7)
      
  def writeRegister(self, register, data):
    hi = ( register << 4 ) | ( (data & 0x0F00) >> 8 )
    lo = data & 0x00FF
    logging.info("writeRegister: "+hex(hi)+hex(lo))
    self.spi.spi_send([hi, lo])

def load_config_prefix(config):
  return DRV8711(config)

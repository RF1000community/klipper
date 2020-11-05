# Support for ADS1100 ADC chip connected via I2C
#
# Copyright (C) 2020  Martin Hierholzer <martin@hierholzer.info>
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging, struct, time, datetime
from . import bus

ADS1100_CHIP_ADDR=0x49
ADS1100_I2C_SPEED=3000000
ADS1100_REPORT_TIME=0.125
ADS1100_MIN_REPORT_TIME=0.125

class MCU_ADS1100:

    def __init__(self, main):
        self._main = main
        self.reactor = main.printer.get_reactor()
        self.i2c = main.i2c
        self.mcu = main.mcu
        self.report_time = main.report_time
        self._last_value = 0.
        self._last_time = datetime.datetime.now()
        self.sample_timer = self.reactor.register_timer(self._sample_ads1100)
        main.printer.add_object("ads1100 " + main.name, self)
        main.printer.register_event_handler("klippy:ready", self._handle_ready)

        query_adc = main.printer.lookup_object('query_adc')
        qname = main.name
        query_adc.register_adc(qname, self)
        self._callback = None

    def setup_adc_callback(self, report_time, callback):
        self.reactor.update_timer(self.sample_timer, self.reactor.NOW)
        self._callback = callback

    def setup_minmax(self, sample_time, sample_count, minval, maxval, range_check_count):
        pass

    def get_last_value(self):
        return self._last_value, self.measured_time

    def read_current_value(self):
        # wait until sample is ready, in case the last this is called more frequently than the sampling rate
        dT = (datetime.datetime.now() - self._last_time).total_seconds()
        if dT < self.report_time :
          time.sleep(self.report_time - dT)
        self._last_time = datetime.datetime.now()
        # obtain sample and return value
        self._last_value = self._read_result()
        return self._last_value

    def _handle_ready(self):
        # ADS1100 configuration: continuous conversion, 8 SPS, gain = 1
        logging.info("ads1100: _handle_ready")
        self._write_configuration(0x8C)

    def _sample_ads1100(self, eventtime):
        try:
            self._last_value = self._read_result()
            logging.info("ads1100: _sample_ads1100: %d" % self._last_value)
        except Exception:
            logging.exception("ads1100: Error reading data")
            self._last_value = 0
            return self.reactor.NEVER

        self.measured_time = self.reactor.monotonic()
        if self._callback != None :
          self._callback(self.mcu.estimated_print_time(measured_time), self._last_value)
        return self.measured_time + self.report_time

    def _read_result(self):
        # read two bytes containing the conversion result
        result = self.i2c.i2c_read([], 2)
        response = bytearray(result['response'])
        return struct.unpack('>h', response)[0]
        

    def _write_configuration(self, data):
        # write the 8 bit configuration register
        self.i2c.i2c_write([data])


class PrinterADS1100:

    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[1]
        self.i2c = bus.MCU_I2C_from_config(
            config,
            default_addr=ADS1100_CHIP_ADDR,
            default_speed=ADS1100_I2C_SPEED
        )
        self.mcu = self.i2c.get_mcu()
        self.report_time = config.getint(
            'ads1100_report_time',
            ADS1100_REPORT_TIME,
            minval=ADS1100_MIN_REPORT_TIME
        )
        # Register setup_pin
        ppins = self.printer.lookup_object('pins')
        ppins.register_chip(self.name, self)

    def setup_pin(self, pin_type, pin_params):
        if pin_type != 'adc':
            raise self.printer.config_error("ADS1100 only supports adc pins")
        return MCU_ADS1100(self)



def load_config_prefix(config):
    return PrinterADS1100(config)

# Support for HX711 load cell frontend chip
#
# Copyright (C) 2022 Martin Hierholzer <martin@hierholzer.info>
#
# This file may be distributed under the terms of the GNU GPLv3 license.
#
# !!! ATTENTION !!!
#
# This module is work in progress! It currently interfaces with the HX711
# outside its specifications! Expect any form of misbehaviour. The author is
# not responsible for any damage caused by using this module!
#

import logging, struct
from . import bus

class HX711Error(Exception):
    pass

class MCU_HX711:

    def __init__(self, main):
        self._main = main
        self.reactor = main.printer.get_reactor()
        self.spi = main.spi
        self.mcu = main.mcu
        self.report_time = 1.01/10. # 1% slower than 10Hz
        self._last_value = 0.
        self._last_time = 0
        self.sample_timer = None

        query_adc = main.printer.lookup_object('query_adc')
        qname = main.name
        query_adc.register_adc(qname, self)
        self._callback = None

        main.printer.register_event_handler("klippy:ready", self._handle_ready)


    def _handle_ready(self):
        self.sample_timer = self.reactor.register_timer(self._sample_timer,
            self.reactor.NOW)


    def setup_adc_callback(self, report_time, callback):
        if self._callback is not None:
          logging.exception("HX711: ADC callback already configured")
          raise HX711Error
        if report_time is not None:
          self.report_time = report_time
        self._callback = callback


    def setup_minmax(self, sample_time, sample_count, minval, maxval,
                     range_check_count):
        pass


    def get_last_value(self):
        return self._last_value, self._last_time


    def read_single_value(self):

        # wait until conversion is ready and the timer callback has been called
        self._wait_conversion_ready()

        # extract and return result
        return self._last_value


    def _wait_conversion_ready(self):
        # wait shortly after the timer has called _sample_timer
        self._last_time = self.reactor.pause(self._last_time + self.report_time
            + 0.0001)


    def _read_response(self):
        while True :
          # read with error handling, spurious errors are possible
          result = self.spi.spi_transfer([0,0,0,0])
          response = bytearray(result['response'])

          # retry if response too short
          if len(response) < 4:
            logging.info("HX711: conversion failed, trying again...")
            continue

          # return response
          self._conversion_started = False
          return response


    def _sample_timer(self, eventtime):
        response = self._read_response()
        self._last_value = struct.unpack('>i', response[0:4])[0] / 256
        self._last_time = eventtime
        self._call_callback()
        return self._last_time + self.report_time


    def _call_callback(self):
        if self._callback is not None :
          self._callback(self.mcu.estimated_print_time(self._last_time),
              self._last_value)


class PrinterHX711:

    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[1]
        self.spi = bus.MCU_SPI_from_config(config, 0, default_speed=1000000)
        self.mcu = self.spi.get_mcu()
        # Register setup_pin
        ppins = self.printer.lookup_object('pins')
        ppins.register_chip(self.name, self)

    def setup_pin(self, pin_type, pin_params):
        if pin_type != 'adc':
            raise self.printer.config_error("HX711 only supports adc pins")
        return MCU_HX711(self)


def load_config_prefix(config):
    return PrinterHX711(config)

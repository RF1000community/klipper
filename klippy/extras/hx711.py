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
# This will only work with in 10 SPS configuration!
#

import logging, struct
from . import bus

class HX711Error(Exception):
    pass

class MCU_HX711:

    def __init__(self, main):
        self._main = main
        self._printer = main.printer
        self._reactor = main.printer.get_reactor()
        self._spi = main._spi
        self._mcu = main._mcu

        self._scan_time = 1./100.
        self._scan_iterations = 0
        self._scan_factor = 2;

        self._avg_sample_time = 1./10.
        self._avg_sample_time_cnt = 0

        self._last_value = 0.
        self._last_time = 0
        self._last_callback = 0
        self._value = 0.
        self._state = 0
        self._error_count = 0

        self._sample_time = 0
        self._sample_count = 0
        self._minval = 0
        self._maxval = 0
        self._range_check_count = 0

        self._sample_timer = None
        self._callback = None
        self._report_time = 0
        self._last_callback_time = 0

        query_adc = main.printer.lookup_object('query_adc')
        query_adc.register_adc(main.name, self)

        main.printer.register_event_handler("klippy:ready", self._handle_ready)


    def get_mcu(self):
        return self._mcu


    def setup_minmax(self, sample_time, sample_count,
                     minval=-1., maxval=1., range_check_count=0):
        self._sample_time = sample_time
        self._sample_count = sample_count
        self._minval = minval
        self._maxval = maxval
        self._range_check_count = range_check_count
        if self._range_check_count < 2 :
          self._range_check_count = 2


    def setup_adc_callback(self, report_time, callback):
        self._report_time = report_time
        self._callback = callback


    def get_last_value(self):
        return self._last_value, self._last_time


    def _handle_ready(self):
        self._sample_timer = self._reactor.register_timer(self._handle_timer,
            self._reactor.NOW)


    def _read_response(self):
        while True :
          # read with error handling, spurious errors are possible
          result = self._spi.spi_transfer([0,0,0,0])
          response = bytearray(result['response'])

          # retry if response too short
          if len(response) < 4:
            logging.info("HX711: conversion failed, trying again...")
            continue

          # return response
          return response


    def _handle_timer(self, eventtime):
        if self._last_callback == 0 :
          response = self._read_response()
          self._last_callback = eventtime
          return eventtime + self._scan_time

        response = self._read_response()
        val = struct.unpack('>i', response[0:4])[0] / 256
        if val == -1:
          self._scan_iterations += 1
          return eventtime + self._scan_time

        if self._scan_iterations == 0 :
          logging.info("HX711: scan_iterations = 0")

        if self._scan_iterations < 2 :
          self._scan_factor += 1
        elif self._scan_iterations > 3 :
          self._scan_factor -= 1
        if self._scan_factor < 1 :
          self._scan_factor = 1
        if self._scan_factor > 10 :
          self._scan_factor = 10
        self._scan_iterations = 0

        # use EMA filter to remove the timing jitter from the reported time
        interval = eventtime - self._last_callback
        alpha = 0.01
        if self._avg_sample_time_cnt < 100 :
          self._avg_sample_time_cnt += 1
          alpha = 0.1
        self._avg_sample_time += alpha*( interval - self._avg_sample_time )
        while self._last_callback < eventtime - self._avg_sample_time/2 :
          self._last_callback += self._avg_sample_time
        next_time = self._last_callback + self._avg_sample_time -              \
            self._scan_factor * self._scan_time

        self._value += val
        self._state += 1
        if self._state < self._sample_count :
          return next_time

        self._last_value = self._value / self._sample_count / pow(2., 23)
        self._last_time = self._last_callback

        self._state = 0
        self._value = 0.

        if self._last_value < self._minval or self._last_value > self._maxval :
          self._error_count += 1
          if self._error_count >= self._range_check_count :
            self._printer.invoke_shutdown("ADC out of range: %f < %f < %f" %   \
                (self._minval, self._last_value, self._maxval))
        else :
          self._error_count = 0

        if self._callback is not None :
          if eventtime >= self._last_callback_time + self._report_time :
            self._last_callback_time = eventtime
            self._callback(self._mcu.estimated_print_time(self._last_time),
                self._last_value)

        return next_time


class PrinterHX711:

    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[1]
        self._spi = bus.MCU_SPI_from_config(config, 0, default_speed=1000000)
        self._mcu = self._spi.get_mcu()
        # Register setup_pin
        ppins = self.printer.lookup_object('pins')
        ppins.register_chip(self.name, self)

    def setup_pin(self, pin_type, pin_params):
        if pin_type != 'adc':
            raise self.printer.config_error("HX711 only supports adc pins")
        return MCU_HX711(self)


def load_config_prefix(config):
    return PrinterHX711(config)

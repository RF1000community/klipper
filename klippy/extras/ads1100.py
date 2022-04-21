# Support for ADS1100 ADC chip connected via I2C
#
# Copyright (C) 2022 Martin Hierholzer <martin@hierholzer.info>
# Copyright (C) 2026  Klipper contributors
#
# This file may be distributed under the terms of the GNU GPLv3 license.

import logging, struct
from . import bulk_sensor, bus

ADS1100_CHIP_ADDR = 0x49
ADS1100_I2C_SPEED = 3000000

ADS1100_SAMPLE_RATE_TABLE = {8: 3, 16: 2, 32: 1, 128: 0}
ADS1100_MAXVALUE_BY_RATE_TABLE = {8: 32768, 16: 16384, 32: 8192, 128: 2048}
ADS1100_GAIN_TABLE = {1: 0, 2: 1, 4: 2, 8: 3}

UPDATE_INTERVAL = 0.10


class ADS1100Error(Exception):
  pass


# HX71x-compatible bulk sensor interface used by load_cell and load_cell_probe.
class ADS1100:
  def __init__(self, config):
    self.printer = config.get_printer()
    self.name = config.get_name().split()[-1]
    self.last_error_count = 0
    self.consecutive_fails = 0

    self.gain = config.getchoice('gain', ADS1100_GAIN_TABLE, default=1)
    sps_options = {8: 8, 16: 16, 32: 32, 128: 128}
    self.sps = config.getchoice('sample_rate', sps_options, default=128)
    self.norm = float(ADS1100_MAXVALUE_BY_RATE_TABLE[self.sps])
    self.config = (ADS1100_SAMPLE_RATE_TABLE[self.sps] << 2) | self.gain

    self.i2c = bus.MCU_I2C_from_config(
      config, default_addr=ADS1100_CHIP_ADDR,
      default_speed=ADS1100_I2C_SPEED)
    self.mcu = mcu = self.i2c.get_mcu()
    self.oid = mcu.create_oid()

    chip_smooth = self.sps * UPDATE_INTERVAL * 2
    self.ffreader = bulk_sensor.FixedFreqReader(mcu, chip_smooth, "<i")
    self.batch_bulk = bulk_sensor.BatchBulkHelper(
      self.printer, self._process_batch, self._start_measurements,
      self._finish_measurements, UPDATE_INTERVAL)

    mcu.add_config_cmd("config_ads1100 oid=%d i2c_oid=%d config=%d"
               % (self.oid, self.i2c.get_oid(), self.config))
    mcu.add_config_cmd("query_ads1100 oid=%d rest_ticks=0"
               % (self.oid,), on_restart=True)
    mcu.register_config_callback(self._build_config)
    self.query_ads1100_cmd = None

  def setup_trigger_analog(self, trigger_analog_oid):
    self.mcu.add_config_cmd(
      "ads1100_attach_trigger_analog oid=%d trigger_analog_oid=%d"
      % (self.oid, trigger_analog_oid), is_init=True)

  def _build_config(self):
    cmd_queue = self.i2c.get_command_queue()
    self.query_ads1100_cmd = self.mcu.lookup_command(
      "query_ads1100 oid=%c rest_ticks=%u", cq=cmd_queue)
    self.ffreader.setup_query_command("query_ads1100_status oid=%c",
                      oid=self.oid, cq=cmd_queue)

  def get_mcu(self):
    return self.mcu

  def get_samples_per_second(self):
    return self.sps

  def get_status(self, eventtime):
    return {
        'errors': self.last_error_count,
        'overflows': self.ffreader.get_last_overflows(),
        'sample_rate': self.get_samples_per_second(),
    }

  def lookup_sensor_error(self, error_code):
    return "Unknown ads1100 error %d" % (error_code,)

  # returns a tuple of the minimum and maximum value of the sensor, used to
  # detect if a data value is saturated
  def get_range(self):
    return -int(self.norm), int(self.norm - 1)

  # add_client interface, direct pass through to bulk_sensor API
  def add_client(self, callback):
    self.batch_bulk.add_client(callback)

  # Measurement decoding
  def _convert_samples(self, samples):
    adc_factor = 1. / self.norm
    count = 0
    for ptime, val in samples:
      samples[count] = (round(ptime, 6), val, round(val * adc_factor, 9))
      count += 1
    del samples[count:]

  # Start, stop, and process message batches
  def _start_measurements(self):
    self.last_error_count = 0
    self.consecutive_fails = 0
    rest_ticks = self.mcu.seconds_to_clock(1. / self.sps)
    self.query_ads1100_cmd.send([self.oid, rest_ticks])
    logging.info("ADS1100 starting '%s' measurements", self.name)
    self.ffreader.note_start()

  def _finish_measurements(self):
    if self.printer.is_shutdown():
      return
    self.query_ads1100_cmd.send_wait_ack([self.oid, 0])
    self.ffreader.note_end()
    logging.info("ADS1100 finished '%s' measurements", self.name)

  def _process_batch(self, eventtime):
    samples = self.ffreader.pull_samples()
    self._convert_samples(samples)
    return {'data': samples, 'errors': self.last_error_count,
        'overflows': self.ffreader.get_last_overflows()}


ADS1100_SENSOR_TYPE = {"ads1100": ADS1100}

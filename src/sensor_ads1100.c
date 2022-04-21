// Support for ADS1100 ADC chip
//
// Copyright (C) 2026  Klipper contributors
//
// This file may be distributed under the terms of the GNU GPLv3 license.

#include <stdint.h>
#include "basecmd.h" // oid_alloc
#include "board/irq.h" // irq_disable
#include "board/misc.h" // timer_read_time
#include "command.h" // DECL_COMMAND
#include "i2ccmds.h" // i2cdev_s
#include "sched.h" // sched_add_timer
#include "sensor_bulk.h" // sensor_bulk_report
#include "trigger_analog.h" // trigger_analog_update

struct ads1100_adc {
    struct timer timer;
    uint8_t flags;
    uint8_t config;
    uint32_t rest_ticks;
    struct i2cdev_s *i2c;
    struct sensor_bulk sb;
    struct trigger_analog *ta;
};

enum {
    ADS1100_PENDING = 1 << 0,
    ADS1100_OVERFLOW = 1 << 1,
};

#define BYTES_PER_SAMPLE 4

static struct task_wake wake_ads1100;

/****************************************************************
 * ADS1100 Sensor Support
 ****************************************************************/

// Event handler that wakes ads1100_capture_task() periodically.
// The ADS1100 is a continuous-conversion ADC - the latest conversion
// result is always available to read via I2C. No "data ready" signal
// needs to be polled.  The timer simply fires at the desired sampling
// interval (rest_ticks) to collect the latest sample.
static uint_fast8_t
ads1100_event(struct timer *timer)
{
    struct ads1100_adc *ads1100 = container_of(timer, struct ads1100_adc,
                                                timer);
    uint8_t flags = ads1100->flags;
    if (flags & ADS1100_PENDING) {
        // Previous sample was not consumed by the background task yet
        ads1100->sb.possible_overflows++;
        ads1100->flags = ADS1100_PENDING | ADS1100_OVERFLOW;
    } else {
        ads1100->flags = ADS1100_PENDING;
        sched_wake_task(&wake_ads1100);
    }
    ads1100->timer.waketime += ads1100->rest_ticks;
    return SF_RESCHEDULE;
}

// Add a measurement to the buffer
static void
add_sample(struct ads1100_adc *ads1100, uint8_t oid, int32_t counts)
{
    uint32_t raw = counts;
    ads1100->sb.data[ads1100->sb.data_count] = raw;
    ads1100->sb.data[ads1100->sb.data_count + 1] = raw >> 8;
    ads1100->sb.data[ads1100->sb.data_count + 2] = raw >> 16;
    ads1100->sb.data[ads1100->sb.data_count + 3] = raw >> 24;
    ads1100->sb.data_count += BYTES_PER_SAMPLE;

    if ((ads1100->sb.data_count + BYTES_PER_SAMPLE)
        > ARRAY_SIZE(ads1100->sb.data)) {
        sensor_bulk_report(&ads1100->sb, oid);
    }
}

// Read one ADS1100 sample
static void
ads1100_read_adc(struct ads1100_adc *ads1100, uint8_t oid)
{
    uint8_t data[3] = {0, 0, 0};
    int ret = i2c_dev_read(ads1100->i2c, 0, NULL, sizeof(data), data);
    i2c_shutdown_on_err(ret);

    irq_disable();
    uint8_t flags = ads1100->flags;
    ads1100->flags = 0;
    irq_enable();

    int16_t raw16 = ((uint16_t)data[0] << 8) | data[1];
    int32_t counts = raw16;

    trigger_analog_update(ads1100->ta, counts);

    add_sample(ads1100, oid, counts);
}

// Create an ads1100 sensor
void
command_config_ads1100(uint32_t *args)
{
    struct ads1100_adc *ads1100 = oid_alloc(args[0]
                , command_config_ads1100, sizeof(*ads1100));
    ads1100->timer.func = ads1100_event;
    ads1100->flags = 0;
    ads1100->i2c = i2cdev_oid_lookup(args[1]);
    ads1100->config = args[2];
}
DECL_COMMAND(command_config_ads1100, "config_ads1100 oid=%c"
    " i2c_oid=%c config=%c");

void
ads1100_attach_trigger_analog(uint32_t *args)
{
    uint8_t oid = args[0];
    struct ads1100_adc *ads1100 = oid_lookup(oid, command_config_ads1100);
    ads1100->ta = trigger_analog_oid_lookup(args[1]);
}
#if CONFIG_WANT_TRIGGER_ANALOG
DECL_COMMAND(ads1100_attach_trigger_analog,
    "ads1100_attach_trigger_analog oid=%c trigger_analog_oid=%c");
#endif

// Start/stop capturing ADC data
void
command_query_ads1100(uint32_t *args)
{
    uint8_t oid = args[0];
    struct ads1100_adc *ads1100 = oid_lookup(oid, command_config_ads1100);
    sched_del_timer(&ads1100->timer);
    ads1100->flags = 0;
    ads1100->rest_ticks = args[1];
    if (!ads1100->rest_ticks)
        // End measurements
        return;

    // Start new measurements: configure gain and conversion rate.
    uint8_t cfg[1] = {ads1100->config};
    int ret = i2c_dev_write(ads1100->i2c, sizeof(cfg), cfg);
    i2c_shutdown_on_err(ret);
    sensor_bulk_reset(&ads1100->sb);
    irq_disable();
    ads1100->timer.waketime = timer_read_time() + ads1100->rest_ticks;
    sched_add_timer(&ads1100->timer);
    irq_enable();
}
DECL_COMMAND(command_query_ads1100, "query_ads1100 oid=%c rest_ticks=%u");

void
command_query_ads1100_status(const uint32_t *args)
{
    uint8_t oid = args[0];
    struct ads1100_adc *ads1100 = oid_lookup(oid, command_config_ads1100);
    irq_disable();
    const uint32_t start_t = timer_read_time();
    uint8_t pending_bytes = (ads1100->flags & ADS1100_PENDING)
        ? BYTES_PER_SAMPLE : 0;
    irq_enable();
    sensor_bulk_status(&ads1100->sb, oid, start_t, 0, pending_bytes);
}
DECL_COMMAND(command_query_ads1100_status, "query_ads1100_status oid=%c");

// Background task that performs measurements
void
ads1100_capture_task(void)
{
    if (!sched_check_wake(&wake_ads1100))
        return;
    uint8_t oid;
    struct ads1100_adc *ads1100;
    foreach_oid(oid, ads1100, command_config_ads1100) {
        if (ads1100->flags)
            ads1100_read_adc(ads1100, oid);
    }
}
DECL_TASK(ads1100_capture_task);
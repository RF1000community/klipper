// ADC functions on STM32
//
// Copyright (C) 2020 Konstantin Vogel <konstantin.vogel@gmx.net>
//
// This file may be distributed under the terms of the GNU GPLv3 license.

#include "board/irq.h" // irq_save
#include "board/misc.h" // timer_from_us
#include "command.h" // shutdown
#include "compiler.h" // ARRAY_SIZE
#include "generic/armcm_timer.h" // udelay
#include "gpio.h" // gpio_adc_setup
#include "internal.h" // GPIO
#include "sched.h" // sched_shutdown

DECL_CONSTANT("ADC_MAX", 65.535);


static const uint8_t adc_pins[] = {
    // GPIOs like A0_C are not covered!
    // all ADCs
    GPIO('C', 0), GPIO('C', 1), GPIO('C', 2), //GPIO('A_C', 0), 
    // only 1/2
    GPIO('A', 2), GPIO('A', 3), GPIO('A', 4), //GPIO('A_C',1),
    GPIO('A', 5), GPIO('A', 6), GPIO('A', 7),
    GPIO('B', 0), GPIO('B', 1), 
    GPIO('C', 3), GPIO('C', 4), GPIO('C', 5), //GPIO('C_C',3),
    // only 1
    GPIO('A', 0), GPIO('A', 1), 
    GPIO('F',11), GPIO('F', 12),
    // only 2
    GPIO('F', 13), GPIO('F', 14),
    // only 3
    GPIO('C', 0), GPIO('C', 1), //GPIO('C_C', 2),
    GPIO('F', 3), GPIO('F', 4), GPIO('F', 5), GPIO('F', 6),
    GPIO('F', 7), GPIO('F', 8), GPIO('F', 9), GPIO('F', 10),
    GPIO('H', 2), GPIO('H', 3), GPIO('H', 4), GPIO('H', 5),
};


// ADC timing:
// ADC clock=       , Tconv=7.5x, Tsamp=, total=

struct gpio_adc
gpio_adc_setup(uint32_t pin)
{
    // Find pin in adc_pins table
    int chan;
    for (chan=0; ; chan++) {
        if (chan >= ARRAY_SIZE(adc_pins))
            shutdown("Not a valid ADC pin");
        if (adc_pins[chan] == pin)
            break;
    }

    // Determine which ADC block to use
    ADC_TypeDef *adc = ADC1;
    uint32_t adc_base = ADC1_BASE;

    // Enable the ADC
    if (!is_enabled_pclock(adc_base)) {
        // Enable clock source for ADC
        enable_pclock(adc_base);
        // Calibrate the ADC
        MODIFY_REG(adc->CR, ADC_CR_DEEPPWD, 0); // Ensure that we are not in Deep-power-down
        MODIFY_REG(adc->CR, ADC_CR_ADVREGEN, ADC_CR_ADVREGEN); // Ensure that ADC Voltage regulator is on
        // while(!(adc->CR & ADC_CR_ADRDY)) // maybe wait until ADC is ready this should check LDORDY (doesn't exist) pg.932
        //     ;
        MODIFY_REG(adc->CR, ADC_CR_ADCALDIF, 0); // Set calibration mode to Single ended (not differential)
        MODIFY_REG(adc->CR, ADC_CR_ADCALLIN, ADC_CR_ADCALLIN); // Enable linearity calibration
        MODIFY_REG(adc->CR, ADC_CR_ADCAL, ADC_CR_ADCAL); // Start the calibration
        while(adc->CR & ADC_CR_ADCAL) // wait for the calibration
            ;
        uint32_t aticks = 0b010; // Set 8.5 ADC clock cycles sample time for every channel (Reference manual pg.940)
        adc->SMPR1 = (aticks        | (aticks << 3)  | (aticks << 6) // channel 0-9
                   | (aticks << 9)  | (aticks << 12) | (aticks << 15)
                   | (aticks << 18) | (aticks << 21) | (aticks << 24)
                   | (aticks << 27));
        adc->SMPR2 = (aticks        | (aticks << 3)  | (aticks << 6) // channel 10-19
                   | (aticks << 9)  | (aticks << 12) | (aticks << 15)
                   | (aticks << 18) | (aticks << 21) | (aticks << 24)
                   | (aticks << 27));

        MODIFY_REG(adc->CFGR, ADC_CFGR_CONT, 0); // Disable Continuous Mode
        adc->CR |= ADC_CR_ADEN; // Enable ADC
    }

    gpio_peripheral(pin, GPIO_ANALOG, 0);

    return (struct gpio_adc){ .adc = adc, .chan = chan };
}

// Try to sample a value. Returns zero if sample ready, otherwise
// returns the number of clock ticks the caller should wait before
// retrying this function.
uint32_t
gpio_adc_sample(struct gpio_adc g)
{
    ADC_TypeDef *adc = g.adc;
    if (adc->ISR & ADC_ISR_EOC) // Conversion ready, EOC set
        return 0;
    if ((adc->CR & ADC_CR_ADSTART) || adc->SQR1 != g.chan) // the channel condition only works if this ist the only channel on the sequence and length set to 1 (ADC_SQR1_L = 0000)
        // Conversion already started (still in progress) or busy on another channel or not started yet (EOC flag is cleared by hardware when reading DR)
        return timer_from_us(20);
    // Start sample
    adc->SQR1 = g.chan;
    adc->CR = ADC_CR_ADSTART | ADC_CR_ADEN; //start the conversion
    return timer_from_us(20);
    
}

// Read a value; use only after gpio_adc_sample() returns zero
uint16_t
gpio_adc_read(struct gpio_adc g)
{
    ADC_TypeDef *adc = g.adc;
    return adc->DR;
}

// Cancel a sample that may have been started with gpio_adc_sample()
void
gpio_adc_cancel_sample(struct gpio_adc g)
{
    ADC_TypeDef *adc = g.adc;
    irqstatus_t flag = irq_save();
    if (adc->CR & ADC_CR_ADSTART && adc->SQR1 == g.chan)// what is this used for the ADSTART is not as long true as SR_STRT on stm32f4
        gpio_adc_read(g);
    irq_restore(flag);
}

// Code to setup clocks and gpio on stm32h7
//
// Copyright (C) 2020 Konstantin Vogel <konstantin.vogel@gmx.net>
//
// This file may be distributed under the terms of the GNU GPLv3 license.


#include "autoconf.h" // CONFIG_CLOCK_REF_FREQ
#include "board/armcm_boot.h" // VectorTable
#include "board/irq.h" // irq_disable
#include "board/usb_cdc.h" // usb_request_bootloader
#include "command.h" // DECL_CONSTANT_STR
#include "internal.h" // enable_pclock
#include "sched.h" // sched_main

#define FREQ_PERIPH (CONFIG_CLOCK_FREQ / 4)
#define FREQ_USB 48000000

// Enable a peripheral clock
void
enable_pclock(uint32_t periph_base)
{
    // periph_base determines in which bitfield at wich position to set a bit
    // E.g. D2_AHB1PERIPH_BASE is the adress offset of the given bitfield
    // the naming makes 0% sense
    if (periph_base < D2_APB2PERIPH_BASE) {
        uint32_t pos = (periph_base - D2_APB1PERIPH_BASE) / 0x400;
        RCC->APB1LENR |= (1<<pos);// we assume it is not in APB1HENR
        RCC->APB1LENR;
    } else if (periph_base < D2_AHB1PERIPH_BASE) {
        uint32_t pos = (periph_base - D2_APB2PERIPH_BASE) / 0x400;
        RCC->APB2ENR |= (1<<pos);
        RCC->APB2ENR;
    } else if (periph_base < D2_AHB2PERIPH_BASE) {
        uint32_t pos = (periph_base - D2_AHB1PERIPH_BASE) / 0x400;
        RCC->AHB1ENR |= (1<<pos);
        RCC->AHB1ENR;
    } else if (periph_base < D1_APB1PERIPH_BASE) {
        uint32_t pos = (periph_base - D2_AHB2PERIPH_BASE) / 0x400;
        RCC->AHB2ENR |= (1<<pos);
        RCC->AHB2ENR;
    } else if (periph_base < D1_AHB1PERIPH_BASE) {
        uint32_t pos = (periph_base - D1_APB1PERIPH_BASE) / 0x400;
        RCC->APB3ENR |= (1<<pos);
        RCC->APB3ENR;
    } else if (periph_base < D3_APB1PERIPH_BASE) {
        uint32_t pos = (periph_base - D1_AHB1PERIPH_BASE) / 0x400;
        RCC->AHB3ENR |= (1<<pos);
        RCC->AHB3ENR;
    } else if (periph_base < D3_AHB1PERIPH_BASE) {
        uint32_t pos = (periph_base - D3_APB1PERIPH_BASE) / 0x400;
        RCC->APB4ENR |= (1<<pos);
        RCC->APB4ENR;
    } else {
        uint32_t pos = (periph_base - D3_AHB1PERIPH_BASE) / 0x400;
        RCC->AHB4ENR |= (1<<pos);
        RCC->AHB4ENR;
    }
}

// Check if a peripheral clock has been enabled
int
is_enabled_pclock(uint32_t periph_base)
{
    if (periph_base < D2_APB2PERIPH_BASE) {
        uint32_t pos = (periph_base - D2_APB1PERIPH_BASE) / 0x400;
        return RCC->APB1LENR & (1<<pos);// we assume it is not in APB1HENR
    } else if (periph_base < D2_AHB1PERIPH_BASE) {
        uint32_t pos = (periph_base - D2_APB2PERIPH_BASE) / 0x400;
        return RCC->APB2ENR & (1<<pos);
    } else if (periph_base < D2_AHB2PERIPH_BASE) {
        uint32_t pos = (periph_base - D2_AHB1PERIPH_BASE) / 0x400;
        return RCC->AHB1ENR & (1<<pos);
    } else if (periph_base < D1_APB1PERIPH_BASE) {
        uint32_t pos = (periph_base - D2_AHB2PERIPH_BASE) / 0x400;
        return RCC->AHB2ENR & (1<<pos);
    } else if (periph_base < D1_AHB1PERIPH_BASE) {
        uint32_t pos = (periph_base - D1_APB1PERIPH_BASE) / 0x400;
        return RCC->APB3ENR & (1<<pos);
    } else if (periph_base < D3_APB1PERIPH_BASE) {
        uint32_t pos = (periph_base - D1_AHB1PERIPH_BASE) / 0x400;
        return RCC->AHB3ENR & (1<<pos);
    } else if (periph_base < D3_AHB1PERIPH_BASE) {
        uint32_t pos = (periph_base - D3_APB1PERIPH_BASE) / 0x400;
        return RCC->APB4ENR & (1<<pos);
    } else {
        uint32_t pos = (periph_base - D3_AHB1PERIPH_BASE) / 0x400;
        return RCC->AHB4ENR & (1<<pos);
    }
}

// Return the frequency of the given peripheral clock
uint32_t
get_pclock_frequency(uint32_t periph_base)
{
    return FREQ_PERIPH;
}

// Enable a GPIO peripheral clock
// TODO test this
void
gpio_clock_enable(GPIO_TypeDef *regs)
{
    enable_pclock((uint32_t)regs);
}

// Set the mode and extended function of a pin TODO verify
void
gpio_peripheral(uint32_t gpio, uint32_t mode, int pullup)
{
    GPIO_TypeDef *regs = digital_regs[GPIO2PORT(gpio)];

    // Enable GPIO clock
    gpio_clock_enable(regs);

    // Configure GPIO
    uint32_t mode_bits = mode & 0xf, func = (mode >> 4) & 0xf, od = mode >> 8;
    uint32_t pup = pullup ? (pullup > 0 ? 1 : 2) : 0;
    uint32_t pos = gpio % 16, af_reg = pos / 8;
    uint32_t af_shift = (pos % 8) * 4, af_msk = 0x0f << af_shift;
    uint32_t m_shift = pos * 2, m_msk = 0x03 << m_shift;

    regs->AFR[af_reg] = (regs->AFR[af_reg] & ~af_msk) | (func << af_shift);
    regs->MODER = (regs->MODER & ~m_msk) | (mode_bits << m_shift);
    regs->PUPDR = (regs->PUPDR & ~m_msk) | (pup << m_shift);
    regs->OTYPER = (regs->OTYPER & ~(1 << pos)) | (od << pos);
    regs->OSPEEDR = (regs->OSPEEDR & ~m_msk) | (0x02 << m_shift);
}

#define USB_BOOT_FLAG_ADDR (CONFIG_RAM_START + CONFIG_RAM_SIZE - 4096)
#define USB_BOOT_FLAG 0x55534220424f4f54 // "USB BOOT"

// Handle USB reboot requests
void
usb_request_bootloader(void)
{
    irq_disable();
    *(uint64_t*)USB_BOOT_FLAG_ADDR = USB_BOOT_FLAG;
    NVIC_SystemReset();
}

#if !CONFIG_STM32_CLOCK_REF_INTERNAL
DECL_CONSTANT_STR("RESERVE_PINS_crystal", "PH0,PH1");
#endif

// Main clock setup called at chip startup
static void
clock_setup(void)
{
    uint32_t pll_base = 2000000;//TODO
    uint32_t pll_freq = CONFIG_CLOCK_FREQ * 2;
    if (!CONFIG_STM32_CLOCK_REF_INTERNAL) {
        // Configure PLL from external crystal (HSE)
        RCC->CR |= RCC_CR_HSEON; // enable HSE input
        MODIFY_REG(RCC->PLLCKSELR, RCC_PLLCKSELR_PLLSRC_NONE, RCC_PLLCKSELR_PLLSRC_HSE); // choose HSE as clock source
        MODIFY_REG(RCC->PLLCKSELR, RCC_PLLCKSELR_DIVM1, (CONFIG_CLOCK_REF_FREQ / pll_base) << RCC_PLLCKSELR_DIVM1_Pos);// set pre divider DIVM1
    } else {
        // Configure PLL from internal 64Mhz oscillator (HSI)
        MODIFY_REG(RCC->PLLCKSELR, RCC_PLLCKSELR_PLLSRC_NONE, RCC_PLLCKSELR_PLLSRC_HSI); // choose HSI as clock source
        MODIFY_REG(RCC->PLLCKSELR, RCC_PLLCKSELR_DIVM1, (64000000 / pll_base) << RCC_PLLCKSELR_DIVM1_Pos);// set pre divider DIVM1
    }
    RCC->PLL1DIVR = (((pll_freq/pll_base) << RCC_PLL1DIVR_N1_Pos)
                    | (0 << RCC_PLL1DIVR_P1_Pos)
                    | ((pll_freq/FREQ_USB) << RCC_PLL1DIVR_Q1_Pos));
    RCC->CR |= RCC_CR_PLLON; //when configuration is done turn on the PLL


    // Set flash latency
    MODIFY_REG(FLASH->ACR, FLASH_ACR_LATENCY, (uint32_t)(FLASH_ACR_LATENCY_7WS)); // 5 should also work
    // Wait for PLL lock
    while (!(RCC->CR & RCC_CR_PLLRDY))
        ;

    // Switch system clock source (SYSCLK) to PLL1
    MODIFY_REG(RCC->CFGR, RCC_CFGR_SW, RCC_CFGR_SW_PLL1);
    // Set D1PPRE, D2PPRE, D2PPRE2, D3PPRE 
    MODIFY_REG(RCC->D1CFGR, RCC_D1CFGR_D1PPRE, RCC_D1CFGR_D1PPRE_DIV2);
    MODIFY_REG(RCC->D2CFGR, RCC_D2CFGR_D2PPRE1, RCC_D2CFGR_D2PPRE1_DIV2);
    MODIFY_REG(RCC->D2CFGR, RCC_D2CFGR_D2PPRE2, RCC_D2CFGR_D2PPRE2_DIV2);
    MODIFY_REG(RCC->D3CFGR, RCC_D3CFGR_D3PPRE, RCC_D3CFGR_D3PPRE_DIV2);

    // Wait for PLL1 to be selected
    while ((RCC->CFGR & RCC_CFGR_SWS_Msk) != RCC_CFGR_SWS_PLL1)
        ;
}

// Main entry point - called from armcm_boot.c:ResetHandler()
void
armcm_main(void)
{
    if (CONFIG_USBSERIAL && *(uint64_t*)USB_BOOT_FLAG_ADDR == USB_BOOT_FLAG) {
        *(uint64_t*)USB_BOOT_FLAG_ADDR = 0;
        uint32_t *sysbase = (uint32_t*)0x1fff0000;
        asm volatile("mov sp, %0\n bx %1"
                     : : "r"(sysbase[0]), "r"(sysbase[1]));
    }

    // Run SystemInit() and then restore VTOR
    SystemInit();
    SCB->VTOR = (uint32_t)VectorTable;

    clock_setup();

    sched_main();
}

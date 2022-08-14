"""Use GPIO edges to drive recording and posting to various chats"""
from asyncio import sleep
from typing import Optional

from pyrogram import Client

from intercompy.audio import play_impromptu_text
from intercompy.config import Config, Rolodex
from intercompy.convo import record_and_send

# pylint: disable=import-error
LOADED_GPIO = False
try:
    import RPi.GPIO as gpio

    LOADED_GPIO = True
except ModuleNotFoundError as e:
    print(e)


# pylint: disable=no-member
def init_pins(cfg: Rolodex):
    """Setup GPIO pins"""
    if not LOADED_GPIO:
        print("No GPIO available. Skipping")
        return

    print(f"Detected Raspberry Pi {gpio.RPI_INFO['P1_REVISION']}.")

    gpio.setwarnings(True)
    gpio.setmode(gpio.BCM)
    for pin in cfg.get_pins():
        print(f"Setting up PIN #{pin} for button input")
        gpio.setup(pin, gpio.IN, pull_up_down=gpio.PUD_UP)


async def button_pushed(pin: int, cfg: Config, client: Optional[Client]):
    """
        When a rolodex button is pushed, respond appropriately based on whether Telegram is
        available.
    """
    target = cfg.rolodex.get_pin_target(pin)
    print(f"PIN: {pin}, Target: {target} ({cfg.rolodex.get_pin_alias(pin)})")
    if client and client.is_connected:
        await record_and_send(target, client, cfg)
    else:
        print("Cannot send to Telegram, client is disconnected!")
        await play_impromptu_text("Sorry. Telegram is disconnected.", cfg.audio)


async def scan_buttons(cfg: Config, client: Optional[Client]):
    """Setup a scanning loop for all buttons listed in the rolodex config."""
    while True:
        for pin in cfg.rolodex.get_pins():
            if gpio.input(pin) == 0:
                await button_pushed(pin, cfg, client)

        await sleep(0.1)


async def listen_for_pins(client: Optional[Client], cfg: Config, loop):
    """Watch for GPIO edges, then record / send"""
    if not LOADED_GPIO:
        return

    loop.create_task(scan_buttons(cfg, client))
    print("Listening for button input...")

    # def gpio_event(arg: int):
    #     print(f"GPIO event had arg: {arg}")
    #     loop.create_task(button_pushed(arg, cfg, client))
    #
    #
    # for pin in cfg.rolodex.get_pins():
    #     gpio.add_event_detect(
    #         pin,
    #         gpio.FALLING,
    #         callback=gpio_event,
    #         bouncetime=500
    #     )

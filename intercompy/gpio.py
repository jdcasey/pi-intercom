"""Use GPIO edges to drive recording and posting to various chats"""

from asyncio import sleep

from pyrogram import Client

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

    gpio.setmode(gpio.BOARD)
    for pin in cfg.rolodex.get_pins():
        gpio.setup(pin, gpio.IN, pull_up_down=gpio.PUD_UP)


async def has_edge(pin: int) -> bool:
    """Detect a GPIO edge (high/low) to trigger recording and sending voice messages"""
    return not gpio.input(pin)


async def listen_for_pins(client: Client, cfg: Config):
    """Watch for GPIO edges, then record / send"""
    if not LOADED_GPIO:
        return

    while True:
        if client.is_connected:
            for pin in cfg.rolodex.get_pins():
                if await has_edge(pin):
                    target = cfg.rolodex.get_pin_target(pin)
                    print(f"PIN: {pin}, Target: {target}")
                    await record_and_send(target, client, cfg)

            await sleep(0.01)
        else:
            await sleep(1)

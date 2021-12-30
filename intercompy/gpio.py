"""Use GPIO edges to drive recording and posting to various chats"""

from asyncio import sleep

from pyrogram import Client

# pylint: disable=import-error
import RPi.GPIO as gpio

from intercompy.config import Config, GPIO
from intercompy.convo import record_and_send


def init_pins(cfg: GPIO):
    """Setup GPIO pins"""
    gpio.setmode(gpio.BOARD)
    for pin in cfg.pins.keys():
        gpio.setup(pin, gpio.IN, pull_up_down=gpio.PUD_UP)


async def has_edge(pin: int) -> bool:
    """Detect a GPIO edge (high/low) to trigger recording and sending voice messages"""
    return not gpio.input(pin)


async def listen_for_pins(client: Client, cfg: Config):
    """Watch for GPIO edges, then record / send"""
    while True:
        if client.is_connected:
            for pin, target in cfg.gpio.pins.items():
                if await has_edge(pin):
                    await record_and_send(target, client, cfg, has_edge)

            await sleep(0.01)
        else:
            await sleep(1)

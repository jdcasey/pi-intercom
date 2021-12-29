"""Use GPIO edges to drive recording and posting to various chats"""

from asyncio import sleep
from tempfile import NamedTemporaryFile

from pyrogram import Client
import RPi.GPIO as gpio

from intercompy.audio import record_ogg
from intercompy.config import Config, GPIO
from intercompy.convo import send_voice


def init(cfg: GPIO):
    """Setup GPIO pins"""
    gpio.setmode(gpio.BOARD)
    for pin in cfg.pins.keys():
        gpio.setup(pin, gpio.IN, pull_up_down=gpio.PUD_UP)


async def has_edge(pin: int) -> bool:
    """Detect a GPIO edge (high/low) to trigger recording and sending voice messages"""
    return not gpio.input(pin)


async def listen_for_buttons(client: Client, cfg: Config):
    """Watch for GPIO edges, then record / send"""
    while True:
        if client.is_connected:
            for pin, target in cfg.gpio.pins.items():
                if await has_edge(pin):
                    with NamedTemporaryFile(
                            "wb", prefix="intercom.voice-out.", suffix=".ogg", delete=False
                    ) as oggfile:
                        print("Recording voice.")
                        await record_ogg(oggfile, cfg.audio, has_edge)

                    print("Sending voice")
                    await send_voice(oggfile, client, target)

            await sleep(0.01)
        else:
            await sleep(1)



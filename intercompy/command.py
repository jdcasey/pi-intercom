"""Command-line interface for intercompy"""
import logging
from asyncio import gather, get_event_loop, sleep

import click
import pygame
from pyrogram import Client

from intercompy.config import load, Config
from intercompy.convo import start_telegram, setup_telegram, record_and_send
from intercompy.gpio import init_pins, listen_for_pins


async def has_edge():
    """Detect a keyboard edge (down / up) to simulate triggering of record via hardware buttons"""
    for event in pygame.event.get():
        # No idea what 772 is, but it shows up when I press or release the shift key.
        if event.type == 772:
            print("Detected edge!")
            return True

    # print("No edge detected")
    return False


async def listen_for_keyboard(client: Client, cfg: Config):
    """Simulate hardware button press, then record / send"""
    # pylint: disable=no-member
    pygame.init()
    print("pygame initialized, waiting for keyboard events...")

    while True:
        if client.is_connected:
            if await has_edge():
                await record_and_send(cfg.telegram.chat, client, cfg, has_edge)

            await sleep(0.01)
        else:
            await sleep(1)


@click.command()
@click.option("--config-file", "-f", help="Alternative config YAML")
@click.option("--debug", "-d", is_flag=True, help="Turn on debug logging")
def run(config_file: str = None, debug: bool = False):
    """Start the bot listening for intercom messages"""
    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=log_level
    )

    cfg = load(config_file)

    app = setup_telegram(cfg)
    init_pins(cfg.gpio)

    gather(
        start_telegram(app, cfg),
        listen_for_keyboard(app, cfg),
        listen_for_pins(app, cfg)
    )
    get_event_loop().run_forever()

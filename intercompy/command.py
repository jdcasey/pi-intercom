"""Command-line interface for intercompy"""
import logging
from asyncio import gather, get_event_loop, sleep

import click
from pyrogram import Client

import sys
import select
import tty
import termios

from intercompy.config import load_config, Config
from intercompy.convo import start_telegram, setup_telegram, record_and_send

from intercompy.gpio import init_pins, listen_for_pins


async def has_edge():
    """Detect a keyboard edge (down / up) to simulate triggering of record via hardware buttons"""
    return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])


async def listen_for_keyboard(client: Client, cfg: Config, use_keyboard: bool):
    """Simulate hardware button press, then record / send"""
    # pylint: disable=no-member
    if not use_keyboard:
        print("Keyboard recording triggers disabled.")
    else:
        print("Waiting for keyboard events...")

        while True:
            if client.is_connected:
                if await has_edge():
                    await record_and_send(cfg.telegram.chat, client, cfg)

                await sleep(0.01)
            else:
                await sleep(1)


@click.command()
@click.option("--config-file", "-f", help="Alternative config YAML")
@click.option("--debug", "-d", is_flag=True, help="Turn on debug logging")
@click.option("--keyboard", "-k", is_flag=True, help="Turn on keyboard recording trigger")
def run(config_file: str = None, keyboard: bool = False, debug: bool = False):
    """Start the bot listening for intercom messages"""
    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=log_level
    )

    cfg = load_config(config_file)

    app = setup_telegram(cfg)
    init_pins(cfg.gpio)

    old_term_settings = termios.tcgetattr(sys.stdin)
    try:
        if keyboard:
            tty.setcbreak(sys.stdin.fileno())

        gather(
            start_telegram(app, cfg),
            listen_for_keyboard(app, cfg, keyboard),
            listen_for_pins(app, cfg)
        )
        get_event_loop().run_forever()
    finally:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_term_settings)


"""Command-line interface for intercompy"""
import logging
from asyncio import gather, new_event_loop, set_event_loop, sleep

import click
from pyrogram import Client

import sys
import select
import tty
import termios

from intercompy import selftest
from intercompy.util import setup_session
from intercompy.config import load_config, Config
from intercompy.convo import start_telegram, setup_telegram, record_and_send

from intercompy.gpio import init_pins, listen_for_pins


def boot(config_file: str = None, debug: bool = False) -> Config:
    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=log_level
    )

    print("Loading intercom configuration")
    return load_config(config_file)


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
def session_setup(config_file: str = None):
    """Interactively setup a new Telegram session for storage in config.yaml"""
    cfg = boot(config_file, True)
    setup_session(cfg)


@click.command()
@click.option("--config-file", "-f", help="Alternative config YAML")
def selftest_gpio(config_file: str = None):
    """Self-test the GPIO functions, including a text-to-audio prompting test"""
    cfg = boot(config_file, True)
    selftest.test_gpio(cfg)


@click.command()
@click.option("--config-file", "-f", help="Alternative config YAML")
@click.option("--debug", "-d", is_flag=True, help="Turn on debug logging")
@click.option("--keyboard", "-k", is_flag=True, help="Turn on keyboard recording trigger")
def run(config_file: str = None, keyboard: bool = False, debug: bool = False):
    """Start the bot listening for intercom messages"""
    loop = new_event_loop()
    set_event_loop(loop)

    cfg = boot(config_file, debug)

    print("Setting up Telegram client")
    app = setup_telegram(cfg)

    print("Setting up hardware buttons")
    init_pins(cfg.rolodex)

    # old_term_settings = termios.tcgetattr(sys.stdin)
    # try:
    # if keyboard:
    #     print("Setting up keyboard input")
    #     tty.setcbreak(sys.stdin.fileno())

    gather(
        start_telegram(app, cfg),
        # listen_for_keyboard(app, cfg, keyboard),
        listen_for_pins(app, cfg, loop)
    )
    loop.run_forever()
    # finally:
    #     termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_term_settings)


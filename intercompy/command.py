"""Command-line interface for intercompy"""
import logging
from asyncio import gather, new_event_loop, set_event_loop
import opentelemetry

import click

from intercompy import selftest
from intercompy.audio import setup_audio
from intercompy.config import load_config, Config
from intercompy.convo import start_telegram, setup_telegram
from intercompy.gpio import init_pins, listen_for_pins
from intercompy.util import setup_session
from intercompy.tracing import setup_tracing, trace, get_tracer


def _boot(config_file: str = None, debug: bool = False) -> Config:
    """Read configuration, setup debug/normal logging. Part of all commands."""

    log_level = logging.INFO
    if debug:
        log_level = logging.DEBUG

    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=log_level
    )

    print("Loading intercom configuration")
    cfg = load_config(config_file)

    print("Setting up Opentelemetry tracing")
    setup_tracing(cfg.tracing)

    print("Intercompy boot-up complete. Application will now start...")
    return cfg


@click.command()
@click.option("--config-file", "-f", help="Alternative config YAML")
@trace
def session_setup(config_file: str = None):
    """Interactively setup a new Telegram session for storage in config.yaml"""
    cfg = _boot(config_file, True)
    new_event_loop().run_until_complete(setup_session(cfg))


@click.command()
@click.option("--config-file", "-f", help="Alternative config YAML")
def selftest_gpio(config_file: str = None):
    """Self-test the GPIO functions, including a text-to-audio prompting test"""
    cfg = _boot(config_file, True)
    selftest.test_gpio(cfg)


@click.command()
@click.option("--config-file", "-f", help="Alternative config YAML")
@click.option("--debug", "-d", is_flag=True, help="Turn on debug logging")
def run(config_file: str = None, debug: bool = False):
    """Start the bot listening for intercom messages"""
    loop = new_event_loop()
    set_event_loop(loop)

    cfg = _boot(config_file, debug)

    with get_tracer().start_as_current_span("intercom-start"):
        print("Setting up Telegram client")
        app = setup_telegram(cfg)

        print("Setting up hardware buttons")
        init_pins(cfg.rolodex)

        print("Setting up audio prompts")
        setup_audio(cfg.audio)

    gather(start_telegram(app, cfg), listen_for_pins(app, cfg, loop))

    loop.run_forever()

"""Command-line interface for intercompy"""
import logging
from asyncio import gather, get_event_loop

import click

from intercompy.config import load
from intercompy.convo import start_telegram, setup_telegram


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
    # app.run(start_telegram(app, cfg))
    gather(start_telegram(app, cfg))
    get_event_loop().run_forever()

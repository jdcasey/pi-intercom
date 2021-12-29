"""Command-line interface for intercompy"""
import logging

import click

from intercompy.config import load
from intercompy.convo import print_help, start


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
    print_help()
    start(cfg)

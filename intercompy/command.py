"""Command-line interface for intercompy"""
import click

from intercompy.config import load
from intercompy.convo import print_help, start


@click.command()
@click.option("--config-file", "-c", help="Alternative config YAML")
def run(config_file: str = None):
    """Start the bot listening for intercom messages"""
    cfg = load(config_file)
    print_help()
    start(cfg)

import click
import intercompy.config as config
import intercompy.convo as convo


@click.command()
@click.option("--config-file", "-c", help="Alternative config YAML")
def run(config_file: str = None):
    cfg = config.load(config_file)
    convo.print_help()
    convo.start(cfg)

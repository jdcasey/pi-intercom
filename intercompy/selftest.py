"""
Run various kinds of self-test on an installation environment.
"""
from asyncio import gather, new_event_loop, set_event_loop

from intercompy.config import Config


def test_gpio(cfg: Config):
    """ Test whether GPIO is working correctly, including a test of voice prompt / feedback."""
    # pylint: disable=import-outside-toplevel
    from intercompy.gpio import init_pins, listen_for_pins

    print("Setting up hardware buttons")
    init_pins(cfg.rolodex)

    loop = new_event_loop()
    set_event_loop(loop)
    gather(
        listen_for_pins(None, cfg, loop)
    )
    loop.run_forever()

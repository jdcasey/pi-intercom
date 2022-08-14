from asyncio import gather, new_event_loop, set_event_loop

from intercompy.config import load_config, Config
from intercompy.gpio import init_pins, listen_for_pins


def test_gpio(cfg: Config):
    print("Setting up hardware buttons")
    init_pins(cfg.rolodex)

    loop = new_event_loop()
    set_event_loop(loop)
    gather(
        listen_for_pins(None, cfg, loop)
    )
    loop.run_forever()

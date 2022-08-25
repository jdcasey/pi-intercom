"""
Module for running an intercom, with send/recv of audio via Telegram.
"""
from .command import run, selftest_gpio, session_setup

__version__ = "0.0.1"

__all__ = ["run", "selftest_gpio", "session_setup"]

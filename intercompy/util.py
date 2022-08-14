import os

from pyrogram import Client

from intercompy.config import Config


def setup_session(cfg: Config):
    """Interactive means of establishing a Telegram session, for use in the config.yaml file"""
    api_id = os.getenv("API_ID") or cfg.telegram.api_id
    api_hash = os.getenv("API_HASH") or cfg.telegram.api_hash

    with Client(":memory:", api_id=api_id, api_hash=api_hash) as app:
        print("Paste this into your config.yaml file:\n\n"
              f"telegram:\n\n  session: \"{app.export_session_string()}\"\n\n\n")

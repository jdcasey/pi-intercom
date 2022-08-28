"""
Run various kinds utilities associated with the intercom, but not part of main operation.
For example, setting up a Telegram session string.
"""
from os import getenv

from pyrogram import Client

from intercompy.config import Config


async def setup_session(cfg: Config):
    """Interactive means of establishing a Telegram session, for use in the config.yaml file"""

    tel = cfg.telegram
    api_id = getenv("API_ID") or tel.api_id
    api_hash = getenv("API_HASH") or tel.api_hash

    app = Client(":memory:", api_id=api_id, api_hash=api_hash)
    await app.start()
    try:
        with open(tel.session_file, "w", encoding="utf-8") as fhandle:
            session = await app.export_session_string()
            fhandle.write(session)
    finally:
        await app.stop()

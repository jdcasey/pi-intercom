#!/usr/bin/env python3
"""Interactive means of establishing a Telegram session, for use in the config.yaml file"""
import os
import sys

from pyrogram import Client

from intercompy.config import load_config, Config, Telegram

if len(sys.argv) > 1:
    config_file = sys.argv[2]
else:
    config_file = None

cfg = load_config(config_file)

API_ID = os.getenv("API_ID") or cfg.telegram.api_id
API_HASH = os.getenv("API_HASH") or cfg.telegram.api_hash

with Client(":memory:", api_id=API_ID, api_hash=API_HASH) as app:
    print(f"telegram-session: \"{app.export_session_string()}\"")

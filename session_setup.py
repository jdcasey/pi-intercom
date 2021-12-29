#!/usr/bin/env python3
"""Interactive means of establishing a Telegram session, for use in the config.yaml file"""
import os

from pyrogram import Client

API_ID = os.getenv("API_ID")
API_HASH = os.getenv("API_HASH")

with Client(":memory:", api_id=API_ID, api_hash=API_HASH) as app:
    print(f"telegram-session: \"{app.export_session_string()}\"")

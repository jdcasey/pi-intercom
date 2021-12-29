#!/usr/bin/env python3

from pyrogram import Client

api_id="1708241"
api_hash="62bfd294c9326446cdee2ef74c0910a2"

with Client(":memory:", api_id=api_id, api_hash=api_hash) as app:
	print(app.export_session_string())

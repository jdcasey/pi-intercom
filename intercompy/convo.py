"""Handle Telegram conversations started by others, or responses from others"""
import logging
import os
from asyncio import sleep
from tempfile import NamedTemporaryFile
from typing import Union

from pyrogram import Client
from pyrogram import filters
from pyrogram.types import Message

from .audio import (
    record_ogg,
    playback_ogg,
    play_impromptu_text,
    play_prompt_text,
    speech_to_text,
    SND_RECORD_YOUR_MESSAGE,
    SND_INTERCOM_ONLINE,
    SND_SNOOPING_AUDIO_START,
    SND_SENDING_MESSAGE,
)
from .config import Config, Telegram
from .text import setup_text_analysis, format_inbound_message_for_speech

COMMAND_PREFIXES = ["!", "/"]

logger = logging.getLogger(__name__)


async def record_and_send(
    target: Union[str, int], app: Client, cfg: Config, stop_fn=None
):
    """Record and send a voice recording to the chat channel"""
    await play_prompt_text(SND_RECORD_YOUR_MESSAGE, cfg.audio)

    print("Recording voice.")
    oggfile = await record_ogg(cfg.audio, stop_fn)

    print("Sending voice")
    await play_prompt_text(SND_SENDING_MESSAGE, cfg.audio)

    txt = await speech_to_text(oggfile)
    with open(oggfile.name, "rb") as _f:
        logging.debug("Sending voice message to: %s", target)
        await app.send_voice(target, _f, caption=txt)

    os.remove(oggfile.name)


async def goodbye(app: Client, cfg: Telegram, sig, frame):
    """Send a sign-off message to Telegram"""
    _me = await app.get_me()
    logger.debug("Sending goodbye to %s in frame: %s", cfg.chat, frame)
    await app.send_message(cfg.chat, f"{_me.username} is offline 😴 (SIG={sig})")


def setup_telegram(cfg: Config) -> Client:
    """Setup the telegram client. This is just a convenience to provide a bit of encapsulation."""
    # , cfg.telegram.api_id, cfg.telegram.api_hash)
    logger.debug("Setting up Telegram client...")
    setup_text_analysis()
    return Client(cfg.telegram.account_name, session_string=cfg.telegram.session)


# pylint: disable=too-many-statements
def format_sender_name(message: Message, cfg: Config) -> str:
    """
    Lookup the configured rolodex alias for a sender's first and last name, or default to that
    given first and last name. This will format the name for text-to-speech.
    """
    name = f"{message.from_user.first_name} {message.from_user.last_name}"
    return cfg.rolodex.get_alias(name)


# pylint: disable=too-many-statements
def get_sender_volume(message: Message, cfg: Config) -> int:
    """
    Lookup the configured rolodex volume for a sender's first and last name, or default to 100.
    """
    name = f"{message.from_user.first_name} {message.from_user.last_name}"
    return cfg.rolodex.get_volume(name)


async def start_telegram(app: Client, cfg: Config):
    """Setup / start the Telegram bot"""

    @app.on_message(
        filters=filters.command(commands="audiograb", prefixes=COMMAND_PREFIXES)
    )
    async def audiograb(_client: Client, message: Message):
        """Record and send voice over Telegram"""
        await play_prompt_text(SND_SNOOPING_AUDIO_START, cfg.audio)
        await sleep(3)
        # print("Grabbing current audio sample...")
        oggfile = await record_ogg(cfg.audio)

        await play_prompt_text(SND_SENDING_MESSAGE, cfg.audio)
        with open(oggfile.name, "rb") as _f:
            logger.debug("Sending voice response to: %s", message.from_user.username)
            await message.reply_voice(voice=_f)

        txt = await speech_to_text(oggfile)
        await message.reply_text(f"Text translation: {txt}")
        os.remove(oggfile.name)

    @app.on_message(
        filters=filters.command(commands="chatinfo", prefixes=COMMAND_PREFIXES)
    )
    async def chatinfo(_client: Client, message: Message):
        """Send the metadata about the current chat to Telegram"""
        msg = (
            f"User: {message.from_user.first_name} {message.from_user.last_name} "
            f"(@{message.from_user.username}, id: {message.from_user.id}) "
            f"is in chat: {message.chat.id}"
        )
        logger.info(
            'Sending chatinfo message: "%s" to: %s in chat: %s',
            msg,
            message.from_user.username,
            message.chat.id,
        )
        await message.reply_text(msg)

    @app.on_message(
        filters=filters.command(commands="contacts", prefixes=COMMAND_PREFIXES)
    )
    async def contacts(client: Client, message: Message):
        """Send the list of registered contacts to Telegram"""
        entries = []
        for contact in await client.get_contacts():
            entries.append(
                f"{contact.first_name} {contact.last_name} (@{contact.username}, id: {contact.id})"
            )

        msg = "Available contacts:\n  * " + "\n  * ".join(entries)
        logger.info(
            'Sending contacts message: "%s" to: %s in chat: %s',
            msg,
            message.from_user.username,
            message.chat.id,
        )
        await message.reply_text(msg)

    @app.on_message(filters=filters.command(commands="help", prefixes=COMMAND_PREFIXES))
    async def show_help(_client: Client, message: Message):
        """Print command help to Telegram"""
        logger.debug(
            "sending help message to: %s in chat: %s",
            message.from_user.username,
            message.chat.id,
        )

        msg = (
            "/audiograb  - Record audio on the device and send it as a voice recording"
            "\n/chatinfo - Display details about the current chat location"
            "\n/contacts - Display known contacts"
            "\n/help     - Show this help message"
        )

        await message.reply_text(msg)

    # @app.on_message(group=-1)
    # async def debug_channel(_client: Client, message: Message):
    #     """Play a received channel message"""
    #     print(message)

    @app.on_message(filters=filters.voice)
    async def play_voice_message(_client: Client, message: Message):
        """Play a received voice message"""
        if message.voice is not None:
            await play_impromptu_text(
                f"New voice message from: {format_sender_name(message, cfg)}", cfg.audio
            )

            fext = message.voice.mime_type.split("/")[-1]

            with NamedTemporaryFile(
                "wb",
                prefix="intercom." + message.voice.file_unique_id + ".",
                suffix="." + fext,
                delete=False,
            ) as temp:
                await message.download(file_name=temp.name)

                await playback_ogg(
                    temp.name, cfg.audio, get_sender_volume(message, cfg)
                )

                os.remove(temp.name)

    @app.on_message(filters=filters.text)
    async def play_prompt_text_message(_client: Client, message: Message):
        """Play a received voice message"""
        if message.text is not None:
            formatted_txt = await format_inbound_message_for_speech(message.text, cfg)
            await play_impromptu_text(
                f"Text from: {format_sender_name(message, cfg)}. "
                f"Message reads: {formatted_txt}",
                cfg.audio,
            )

    logger.debug("Starting Telegram client")
    await app.start()
    _me = await app.get_me()
    logger.debug("Playing online sound")
    await play_prompt_text(SND_INTERCOM_ONLINE, cfg.audio)
    logger.debug("Sending hello to %s", cfg.telegram.chat)
    await app.send_message(cfg.telegram.chat, f"{_me.username} is online 🎉")

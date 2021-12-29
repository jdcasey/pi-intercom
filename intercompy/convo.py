"""Handle Telegram conversations started by others, or responses from others"""
import logging
from tempfile import NamedTemporaryFile

from pyaudio import PyAudio
from pyrogram import Client
from pyrogram.types import Message
from pyrogram import filters

from intercompy.audio import record_ogg, get_input_devices  #, playback_ogg
from intercompy.config import Config


COMMAND_PREFIXES = ["!", "/"]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


async def goodbye(app: Client, cfg: Config, sig, frame):
    """Send a sign-off message to Telegram"""
    _me = await app.get_me()
    logger.debug("Sending goodbye to %s in frame: %s", cfg.chat, frame)
    await app.send_message(cfg.chat, f"{_me.username} is offline 😴 (SIG={sig})")


# def converse(update: Update, context: CallbackContext, cfg: Config):
#     """Handle a complex user interaction involving multiple send/recv exchanges"""
#     print(
#         f"RECV: {update.message}"
#         f"\n\nfrom: {context.user_data}"
#         f"\n\ndocument: {update.message.document}"
#         f"\n\nvoice: {update.message.voice}"
#         f"\n\nlocation: {update.message.location}"
#     )
#     if (
#         update.message.text is not None
#         and "who's online?" in update.message.text.lower()
#     ):
#         update.message.reply_text("I'm online")
#     elif update.message.voice is not None:
#         fid = update.message.voice.get_file()
#         fext = update.message.voice.mime_type.split("/")[-1]
#
#         with NamedTemporaryFile(
#             "wb", prefix="intercom.", suffix="." + fext, delete=False
#         ) as temp:
#             temp.write(fid.download_as_bytearray())
#             temp.flush()
#             infile = temp.name
#             print(f"Wrote: {infile}")
#
#             playback_ogg(temp.name, cfg)
#
#         sleep(1)
#
#         print("RECORD YOUR RESPONSE....")
#         with NamedTemporaryFile(
#                 "wb", prefix="intercom.voice-out.", suffix=".ogg", delete=False
#         ) as oggfile:
#
#             record_ogg(oggfile, cfg)
#             with open(oggfile.name, "rb") as _f:
#                 update.message.reply_voice(voice=_f)
#
#         # update.message.reply_text(f"Saved voice note as: {fname}")
#
#     else:
#         update.message.reply_text("Got it. Thanks")


def setup_telegram(cfg: Config) -> Client:
    return Client(cfg.session, cfg.api_id, cfg.api_hash)


async def start_telegram(app: Client, cfg: Config):
    """Setup / start the Telegram bot"""

    @app.on_message(filters=filters.command(commands="audiograb", prefixes=COMMAND_PREFIXES))
    async def audiograb(_client: Client, message: Message):
        """Record and send voice over Telegram"""
        # print("Grabbing current audio sample...")
        with NamedTemporaryFile(
                "wb", prefix="intercom.voice-out.", suffix=".ogg", delete=False
        ) as oggfile:
            record_ogg(oggfile, cfg)
            with open(oggfile.name, "rb") as _f:
                logger.debug("Sending voice response to: %s", message.from_user.username)
                await message.reply_voice(voice=_f)

    @app.on_message(filters=filters.command(commands="chatinfo", prefixes=COMMAND_PREFIXES))
    async def chatinfo(_client: Client, message: Message):
        """Send the metadata about the current chat to Telegram"""
        msg = (
            f"User: {message.from_user.first_name} {message.from_user.last_name} "
            f"is in chat: {message.chat.id}"
        )
        logger.info(
            "Sending chatinfo message: \"%s\" to: %s in chat: %s",
            msg, message.from_user.username, message.chat.id
        )
        await message.reply_text(msg)

    @app.on_message(filters=filters.command(commands="help", prefixes=COMMAND_PREFIXES))
    async def show_help(_client: Client, message: Message):
        """Print command help to Telegram"""
        logger.debug(
            "sending help message to: %s in chat: %s",
            message.from_user.username, message.chat.id
        )

        msg = "/audiograb  - Record audio on the device and send it as a voice recording" \
              "\n/chatinfo - Display details about the current chat location" \
              "\n/help     - Show this help message" \
              "\n/lsaudio [<index>|default] - List available audio devices. " \
              "If 'default' or an index is given, give more detail about that device"

        await message.reply_text(msg)

    @app.on_message(filters=filters.command(commands="lsaudio", prefixes=COMMAND_PREFIXES))
    async def lsaudio(_client: Client, message: Message):
        """List the available audio devices to Telegram"""
        # print(f"RECV params: {update.message.text} and args: {str(context.args)}")
        pyaudio = PyAudio()
        try:
            if message.command is not None and len(message.command) > 1:
                idxarg = message.command[1]
                print(f"Retrieving specific audio device: {idxarg}")

                info = None
                if "default" == idxarg:
                    info = pyaudio.get_default_input_device_info()
                else:
                    idx = int(idxarg)
                    info = pyaudio.get_device_info_by_index(idx)

                if info is None:
                    msg = f"No audio device found for: {idxarg}"
                else:
                    msg = "\n".join([f"{k}={v}" for (k, v) in info.items()])

            else:
                devices = get_input_devices(pyaudio)
                if len(devices) > 0:
                    lines = []
                    for dev in devices:
                        lines.append(
                            f"{dev.get('index')}. {dev.get('name')} "
                            f"(input channels: {dev.get('maxInputChannels')})"
                        )

                    msg = "\n".join(lines)

                else:
                    msg = "No valid audio input devices found!"

                # definfo = "\n".join(
                #   [f"{k}={v}" for (k,v) in pyaudio.get_default_input_device_info().items()]
                # )
                # msg = "\n".join(lines) + "\n\nDefault input device:\n" + definfo

            logger.debug(
                "Sending message: \"%s\" to: %s in chat: %s",
                msg, message.from_user.username, message.chat.id
            )
            await message.reply_text(msg)
        finally:
            pyaudio.terminate()

    await app.start()
    _me = await app.get_me()
    logger.debug("Sending hello to %s", cfg.chat)
    await app.send_message(cfg.chat, f"{_me.username} is online 🎉")

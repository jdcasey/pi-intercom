"""Handle Telegram conversations started by others, or responses from others"""
import logging
from tempfile import NamedTemporaryFile
from time import sleep

from pyaudio import PyAudio
from telegram import Bot, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    Filters, Dispatcher,
)

from intercompy.audio import record_ogg, playback_ogg, get_input_devices
from intercompy.config import Config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


def set_commands(bot: Bot):
    """Setup the standard Telegram command handlers for this bot"""
    my_commands = [(k, helptxt) for (k, _, helptxt) in COMMANDS]
    bot.set_my_commands(my_commands)


def hello(cfg: Config) -> Bot:
    """Start the Telegram bot and send a hello message"""
    bot = Bot(cfg.token)
    _me = bot.get_me()
    logger.debug("Sending hello to %s", cfg.chat)
    bot.send_message(cfg.chat, f"{_me.full_name} is online 🎉")

    return bot


def goodbye(cfg: Config, sig, frame):
    """Send a sign-off message to Telegram"""
    bot = Bot(cfg.token)
    _me = bot.get_me()
    logger.debug("Sending goodbye to %s in frame: %s", cfg.chat, frame)
    bot.send_message(cfg.chat, f"{_me.full_name} is offline 😴 (SIG={sig})")


def show_help(update: Update, context: CallbackContext, cfg: Config):
    """Print command help to Telegram"""
    logger.debug("sending help message to: %s in chat: %s", context.user_data, cfg.chat)
    my_commands = [f"/{k} - {helptxt}" for (k, _, helptxt) in COMMANDS]
    update.message.reply_text("\n".join(my_commands))


def chatinfo(update: Update, context: CallbackContext, cfg: Config):
    """Send the metadata about the current chat to Telegram"""
    msg = (
        f"User: {update.effective_user.full_name} is in chat: {update.message.chat_id}"
    )
    logger.info(
        "Sending chatinfo message: \"%s\" to: %s in chat: %s",
        msg, context.user_data, cfg.chat
    )
    update.message.reply_text(msg)


def lsaudio(update: Update, context: CallbackContext, cfg: Config):
    """List the available audio devices to Telegram"""
    # print(f"RECV params: {update.message.text} and args: {str(context.args)}")
    pyaudio = PyAudio()
    if context.args is not None and len(context.args) > 0:
        idxarg = context.args[0]
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

        lines = []
        for dev in get_input_devices():
            lines.append(
                f"{dev.get('index')}. {dev.get('name')} "
                f"(input channels: {dev.get('maxInputChannels')})"
            )

        msg = "\n".join(lines)
        # definfo = "\n".join(
        #   [f"{k}={v}" for (k,v) in pyaudio.get_default_input_device_info().items()]
        # )
        # msg = "\n".join(lines) + "\n\nDefault input device:\n" + definfo

    logger.debug("Sending message: \"%s\" to: %s in chat: %s", msg, context.user_data, cfg.chat)
    update.message.reply_text(msg)


def audiograb(update: Update, context: CallbackContext, cfg: Config):
    """Record and send voice over Telegram"""
    # print("Grabbing current audio sample...")
    with NamedTemporaryFile(
        "wb", prefix="intercom.voice-out.", suffix=".ogg", delete=False
    ) as oggfile:

        record_ogg(oggfile, cfg)
        with open(oggfile.name, "rb") as _f:
            logger.debug("Sending voice response to: %s", context.user_data)
            update.message.reply_voice(voice=_f)


def converse(update: Update, context: CallbackContext, cfg: Config):
    """Handle a complex user interaction involving multiple send/recv exchanges"""
    print(
        f"RECV: {update.message}"
        f"\n\nfrom: {context.user_data}"
        f"\n\ndocument: {update.message.document}"
        f"\n\nvoice: {update.message.voice}"
        f"\n\nlocation: {update.message.location}"
    )
    if (
        update.message.text is not None
        and "who's online?" in update.message.text.lower()
    ):
        update.message.reply_text("I'm online")
    elif update.message.voice is not None:
        fid = update.message.voice.get_file()
        fext = update.message.voice.mime_type.split("/")[-1]

        with NamedTemporaryFile(
            "wb", prefix="intercom.", suffix="." + fext, delete=False
        ) as temp:
            temp.write(fid.download_as_bytearray())
            temp.flush()
            infile = temp.name
            print(f"Wrote: {infile}")

            playback_ogg(temp.name, cfg)

        sleep(1)

        print("RECORD YOUR RESPONSE....")
        with NamedTemporaryFile(
                "wb", prefix="intercom.voice-out.", suffix=".ogg", delete=False
        ) as oggfile:

            record_ogg(oggfile, cfg)
            with open(oggfile.name, "rb") as _f:
                update.message.reply_voice(voice=_f)

        # update.message.reply_text(f"Saved voice note as: {fname}")

    else:
        update.message.reply_text("Got it. Thanks")


def add_command(dispatcher: Dispatcher, cmdinfo: list, cfg: Config):
    """Add a Telegram command"""

    key, cmd, _ = cmdinfo
    # print(f"{key} maps to {cmd}")
    dispatcher.add_handler(CommandHandler(key, lambda u, cx: cmd(u, cx, cfg)))


def start(cfg: Config):
    """Setup / start the Telegram bot"""

    bot = hello(cfg)
    set_commands(bot)

    updater = Updater(
        cfg.token,
        use_context=True,
        user_sig_handler=lambda sig, frame: goodbye(cfg, sig, frame),
    )
    dispatcher = updater.dispatcher

    for cmd in COMMANDS:
        add_command(dispatcher, cmd, cfg)

    dispatcher.add_handler(
        MessageHandler(Filters.all, lambda u, cx: converse(u, cx, cfg))
    )

    updater.start_polling()
    updater.idle()


def print_help():
    """Print available Telegram commands to the console."""

    my_commands = [f"{k} - {helptxt}" for (k, _, helptxt) in COMMANDS]
    print("The following commands are available:\n\n" + "\n".join(my_commands) + "\n\n")


COMMANDS = [
    ("help", show_help, "Show this help"),
    ("chatinfo", chatinfo, "Display information about this chat"),
    (
        "lsaudio",
        lsaudio,
        "[idx] (Optional)\n\t\t\tList audio device information from bot host.\n\t\t\t"
        "With index param, show details.",
    ),
    ("audiograb", audiograb, "Record some audio on the bot host and send it back"),
]

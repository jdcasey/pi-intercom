import logging
from pyaudio import PyAudio
import tempfile
from time import sleep
import os

import intercompy.audio as audio
from intercompy.config import Config

from telegram import Bot, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    Filters, Dispatcher,
)


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


def set_commands(cfg: Config, bot: Bot):
    my_commands = [(k, helptxt) for (k, _, helptxt) in COMMANDS]
    bot.set_my_commands(my_commands)


def hello(cfg: Config) -> Bot:
    bot = Bot(cfg.token)
    me = bot.get_me()
    logger.info("Sending hello to {c}".format(c=cfg.chat))
    bot.send_message(cfg.chat, f"{me.full_name} is online 🎉")

    return bot


def goodbye(cfg: Config, sig, frame):
    bot = Bot(cfg.token)
    me = bot.get_me()
    logger.info("Sending goodbye to {c}".format(c=cfg.chat))
    bot.send_message(cfg.chat, f"{me.full_name} is offline 😴 (SIG={sig})")


def show_help(update: Update, context: CallbackContext, cfg: Config):
    # logger.info("sending help message")
    my_commands = [f"/{k} - {helptxt}" for (k, _, helptxt) in COMMANDS]
    update.message.reply_text("\n".join(my_commands))


def chatinfo(update: Update, context: CallbackContext, cfg: Config):
    msg = (
        f"User: {update.effective_user.full_name} is in chat: {update.message.chat_id}"
    )
    logger.info(msg)
    update.message.reply_text(msg)


def lsaudio(update: Update, context: CallbackContext, cfg: Config):
    # print(f"RECV params: {update.message.text} and args: {str(context.args)}")
    p = PyAudio()
    if context.args is not None and len(context.args) > 0:
        idxarg = context.args[0]
        info = None
        if "default" == idxarg:
            info = p.get_default_input_device_info()
        else:
            idx = int(idxarg)
            info = p.get_device_info_by_index(idx)

        if info is None:
            msg = f"No audio device found for: {idxarg}"
        else:
            msg = "\n".join([f"{k}={v}" for (k, v) in info.items()])

    else:
        lines = []
        for idx in range(p.get_device_count()):
            dev = p.get_device_info_by_index(idx)
            lines.append(
                f"{idx}. {dev.get('name')} (input channels: {dev.get('maxInputChannels')})"
            )
            dev = None

        msg = "\n".join(lines)
        # definfo = "\n".join([f"{k}={v}" for (k,v) in p.get_default_input_device_info().items()])
        # msg = "\n".join(lines) + "\n\nDefault input device:\n" + definfo

    logger.info(msg)
    update.message.reply_text(msg)


def audiograb(update: Update, context: CallbackContext, cfg: Config):
    # print("Grabbing current audio sample...")
    outfile = audio.record_ogg(cfg)
    with open(outfile, "rb") as f:
        update.message.reply_voice(voice=f)
    os.remove(outfile)


def converse(update: Update, context: CallbackContext, cfg: Config):
    print(
        f"RECV: {update.message}\n\ndocument: {update.message.document}\n\nvoice: {update.message.voice}\n\n"
        f"location: {update.message.location}"
    )
    if (
        update.message.text is not None
        and "who's online?" in update.message.text.lower()
    ):
        update.message.reply_text("I'm online")
    elif update.message.voice is not None:
        fid = update.message.voice.get_file()
        fext = update.message.voice.mime_type.split("/")[-1]

        infile = None
        with tempfile.NamedTemporaryFile(
            "wb", prefix="intercom.", suffix="." + fext, delete=False
        ) as temp:
            temp.write(fid.download_as_bytearray())
            temp.flush()
            infile = temp.name
            print(f"Wrote: {infile}")

        audio.playback_ogg(infile, cfg)
        os.remove(infile)

        sleep(5)
        print("RECORD YOUR RESPONSE....")
        outfile = audio.record_ogg(cfg)
        with open(outfile, "rb") as f:
            update.message.reply_voice(voice=f)
        os.remove(outfile)

        # update.message.reply_text(f"Saved voice note as: {fname}")

    else:
        update.message.reply_text("Got it. Thanks")


def add_command(dispatcher: Dispatcher, cmdinfo: list, cfg: Config):
    key, cmd, _ = cmdinfo
    # print(f"{key} maps to {cmd}")
    dispatcher.add_handler(CommandHandler(key, lambda u, cx: cmd(u, cx, cfg)))


def start(cfg: Config):
    bot = hello(cfg)
    set_commands(cfg, bot)

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

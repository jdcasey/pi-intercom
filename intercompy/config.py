"""Handle configuration for intercompy bot"""
import logging
import os
from typing import Optional, List

from ruamel.yaml import YAML

logger = logging.getLogger(__name__)

ETC_CONFIG_FILE = "/etc/intercompy/config.yaml"
HOME_CONFIG_FILE = os.path.join(
    os.environ.get("HOME"), ".config/intercompy/config.yaml"
)

APP_STATE_DIR = os.path.join(os.environ.get("HOME"), ".local/state/intercompy")

ROLODEX = "rolodex"

TELEGRAM_SECTION = "telegram"
TELEGRAM_SESSION_FILE = "telegram.session"

SESSION = "session"
ACCOUNT_NAME = "account-name"
API_HASH = "api-hash"
API_ID = "api-id"
CHAT = "chat"

AUDIO_SECTION = "audio"

WAV_THRESHOLD = "wav-threshold"
WAV_SILENCE_THRESHOLD = "wav-silence-threshold"
VOLUME = "playback-volume"
AUDIO_DEVICE = "device"
TEXT_LANGUAGE = "text-language"
TEXT_ACCENT = "text-accent"
AUDIO_PROMPTS = "prompts"

TEXT_MESSAGE_LINE_ENDING = "text-message-line-ending"

GPIO_SECTION = "pin-targets"

DEFAULT_VOLUME = 100
DEFAULT_WAV_THRESHOLD = 1000
DEFAULT_WAV_SILENCE_THRESHOLD = 30


# pylint: disable=too-few-public-methods
class Audio:
    """Contain config options for audio input / output"""

    def __init__(self, data: dict, audio_dir: str):
        if data is None:
            data = {}

        if not os.path.isdir(audio_dir):
            os.makedirs(audio_dir)

        self.audio_dir = audio_dir

        self.wav_threshold = data.get(WAV_THRESHOLD) or DEFAULT_WAV_THRESHOLD
        self.wav_threshold = int(self.wav_threshold)

        self.wav_silence_threshold = (
            data.get(WAV_SILENCE_THRESHOLD) or DEFAULT_WAV_SILENCE_THRESHOLD
        )
        self.wav_silence_threshold = int(self.wav_silence_threshold)

        self.text_lang = data.get(TEXT_LANGUAGE) or "en"
        self.text_accent = data.get(TEXT_ACCENT) or "com"

        self.prompts = data.get(AUDIO_PROMPTS) or {}

        self.volume = data.get(VOLUME) or DEFAULT_VOLUME
        self.volume = int(self.volume)

        self.audio_device = data.get(AUDIO_DEVICE)

        self.text_msg_line_ending = data.get(TEXT_MESSAGE_LINE_ENDING)


# pylint: disable=too-few-public-methods
class Telegram:
    """Contain configuration options for Telegram client"""

    def __init__(self, data: dict, session_dir: str):
        if data is None:
            data = {}

        self.account_name = data.get(ACCOUNT_NAME)
        self.api_hash = data.get(API_HASH)
        self.api_id = data.get(API_ID)

        self.session_file = os.path.join(session_dir, TELEGRAM_SESSION_FILE)
        if not os.path.exists(self.session_file):
            print(
                f"Telegram session not found at: {self.session_file}\n"
                "You may need to run `intercompy-session-setup` again."
            )

        else:
            with open(self.session_file) as f:
                self.session = str(f.read()).strip()

        self.chat = data.get(CHAT)


# pylint: disable=too-few-public-methods
class Rolodex:
    """Contain configuration related to intercom chat members"""

    def __init__(self, data: dict):
        if data is None:
            logger.debug("rolodex data is None. Using empty dict.")
            data = {}

        self.data = data

    def get_alias(self, name: str) -> str:
        """Return the registered alias for the name, or else the name itself"""
        if name in self.data:
            return self.data[name]["alias"] or name

        return name

    def get_volume(self, name: str) -> str:
        """Return the registered volume for the name, or else 100"""
        if name in self.data:
            return self.data[name]["volume"] or 100

        return name

    def get_pin_alias(self, pin: int) -> str:
        """Return the registered alias for the pin, or else the name itself"""
        for name, entry in self.data.items():
            if int(entry["pin"]) == pin:
                return entry["alias"] or name

        return None

    def get_pins(self) -> List[int]:
        """Return the list of GPIO pins to watch"""
        logger.debug("Extracting pins from: %s", self.data)
        return [int(e["pin"]) for e in self.data.values()]

    def get_pin_target(self, pin: int) -> Optional[str]:
        """Return the target for the specified GPIO pin"""
        for entry in self.data.values():
            if int(entry["pin"]) == pin:
                return entry["id"]

        return None


# pylint: disable=too-few-public-methods
class Config:
    """Contain the configuration parameters for intercompy"""

    def __init__(self, data: dict, app_state_dir: str):
        if data is None:
            data = {}

        self.telegram = Telegram(data.get(TELEGRAM_SECTION), app_state_dir)
        self.audio = Audio(
            data.get(AUDIO_SECTION), os.path.join(app_state_dir, "audio")
        )
        self.rolodex = Rolodex(data.get(ROLODEX))


def load_config(config_file: str = None) -> Config:
    """
    Load configuration, starting with the specified file if available.
    If not, try to load from one of two standard locations, in the
    following order of precedence:
        $HOME/.config/intercompy/config.yaml
        /etc/intercompy/config.yaml
    """
    config_path = config_file or HOME_CONFIG_FILE
    if os.path.exists(config_path) is not True:
        config_path = ETC_CONFIG_FILE

    if os.path.exists(config_path) is not True:
        raise Exception(
            f"No configuration defined for intercompy in {config_file} or {HOME_CONFIG_FILE} or "
            f"{ETC_CONFIG_FILE}"
        )

    logger.info("Using configuration at: %s", config_path)
    with open(config_path, encoding="utf-8") as _f:
        data = YAML().load(_f)

    if not os.path.isdir(APP_STATE_DIR):
        os.makedirs(APP_STATE_DIR)

    return Config(data, APP_STATE_DIR)

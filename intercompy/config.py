"""Handle configuration for intercompy bot"""
import os
import logging

from ruamel.yaml import YAML


ETC_CONFIG_FILE = "/etc/intercompy/config.yaml"
HOME_CONFIG_FILE = os.path.join(
    os.environ.get("HOME"), ".config/intercompy/config.yaml"
)

TELEGRAM_SECTION = "telegram"

SESSION = "session"
API_HASH = "api-hash"
API_ID = "api-id"
CHAT = "chat"

AUDIO_SECTION = "audio"

WAV_THRESHOLD = "wav-threshold"
WAV_SILENCE_THRESHOLD = "wav-silence-threshold"
VOLUME = "playback-volume"
AUDIO_DEVICE = "device"

DEFAULT_VOLUME = 75
DEFAULT_WAV_THRESHOLD = 500
DEFAULT_WAV_SILENCE_THRESHOLD = 30


def load(config_file: str = None):
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

    with open(config_path, encoding="utf-8") as _f:
        data = YAML().load(_f)

    return Config(data)


class GPIO:
    """Contain config mappings of GPIO pins to chat / user for sending recordings"""
    def __init__(self, data: dict):
        pin_map = {}
        for pin,target in dict.items():
            if isinstance(pin, int):
                pin_map[pin] = target

        self.pins = pin_map

class Audio:
    """Contain config options for audio input / output"""
    def __init__(self, data: dict):
        self.wav_threshold = data.get(WAV_THRESHOLD) or DEFAULT_WAV_THRESHOLD
        self.wav_silence_threshold = data.get(WAV_SILENCE_THRESHOLD) or \
                                     DEFAULT_WAV_SILENCE_THRESHOLD

        self.volume = data.get(VOLUME) or DEFAULT_VOLUME
        self.audio_device = data.get(AUDIO_DEVICE)


class Telegram:
    """Contain configuration options for Telegram client"""
    def __init__(self, data: dict):
        self.api_hash = data.get(API_HASH)
        self.api_id = data.get(API_ID)
        self.session = data.get(SESSION)
        self.chat = data.get(CHAT)


class Config:
    """Contain the configuration parameters for intercompy
    """
    # pylint: disable=too-many-instance-attributes
    def __init__(self, data: dict):
        self.telegram = Telegram(data.get(TELEGRAM_SECTION))
        self.audio = Audio(data.get(AUDIO_SECTION))

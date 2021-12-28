"""Handle configuration for intercompy bot"""
import os
from ruamel.yaml import YAML


ETC_CONFIG_FILE = "/etc/intercompy/config.yaml"
HOME_CONFIG_FILE = os.path.join(
    os.environ.get("HOME"), ".config/intercompy/config.yaml"
)
TOKEN = "token"
CHAT = "chat"
WAV_THRESHOLD = "wav-threshold"
VOLUME = "playback-volume"
AUDIO_DEVICE = "audio-device"

DEFAULT_VOLUME = 75
DEFAULT_WAV_THRESHOLD = 500


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


class Config:
    """Contain the configuration parameters for intercompy
    """
    def __init__(self, data):
        self.token = data.get(TOKEN)
        self.chat = data.get(CHAT)
        self.wav_threshold = data.get(WAV_THRESHOLD) or DEFAULT_WAV_THRESHOLD
        self.volume = data.get(VOLUME) or DEFAULT_VOLUME
        self.audio_device_index = data.get(AUDIO_DEVICE)

    def print(self):
        """Print a diagnostic message containing this configuration"""
        print(f"Token: {self.token}"
              f"\nChat: {self.chat}"
              f"\nWAV Threshold:{self.wav_threshold}"
              f"\nPlayback volume: {self.volume}"
              f"\nAudio device index: {self.audio_device_index}")

    def dump(self, stream):
        """Dump the config as YAML to the specified stream"""
        YAML().dump({
            TOKEN: self.token,
            CHAT: self.chat,
            WAV_THRESHOLD: self.wav_threshold,
            VOLUME: self.volume,
            AUDIO_DEVICE: self.audio_device_index,
        }, stream)

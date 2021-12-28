"""
Capture and play audio for use with Telegram. Uses ffmpeg for recording and vlc for playback.
"""
import os
import wave
from array import array
from struct import pack
from sys import byteorder
from tempfile import NamedTemporaryFile
from typing import Tuple

import ffmpy
import vlc
from pyaudio import PyAudio, paInt16

from intercompy.config import Config

WAV_FORMAT = paInt16
WAV_CHUNK_SIZE = 4096

# WAV recording logic is adapted from:
# https://stackoverflow.com/questions/892199/detect-record-audio-in-python


def is_silent(snd_data: array, cfg: Config) -> bool:
    "Returns 'True' if below the 'silent' threshold"
    return max(snd_data) < cfg.wav_threshold


def trim(snd_data: array, cfg: Config) -> array:
    """Trim the blank spots at the start and end
    """

    def _trim(_sd: array, _c: Config) -> array:
        snd_started = False
        _r = array("h")

        for i in _sd:
            if not snd_started and abs(i) > cfg.wav_threshold:
                snd_started = True
                _r.append(i)

            elif snd_started:
                _r.append(i)
        return _r

    # Trim to the left
    snd_data = _trim(snd_data, cfg)

    # Trim to the right
    snd_data.reverse()
    snd_data = _trim(snd_data, cfg)
    snd_data.reverse()
    return snd_data


def __is_valid_input(dev):
    """Determine whether the given audio device is suitable for recording voice."""

    return int(dev.get("maxInputChannels")) > 0


def detect_input(pyaudio: PyAudio, cfg: Config) -> dict:
    """
    Find the audio input device
    """

    device_index = cfg.audio_device_index
    input_info = None

    if device_index is None:
        input_info = pyaudio.get_default_input_device_info()

    if input_info is None:
        pyaudio = PyAudio()
        device_count = pyaudio.get_device_count()
        if device_index is not None and device_index < device_count-1:
            dev = pyaudio.get_device_info_by_index(int(device_index))
            if __is_valid_input(dev):
                input_info = dev
        else:
            for idx in range(device_count):
                dev = pyaudio.get_device_info_by_index(idx)
                if __is_valid_input(dev):
                    input_info = dev
                    break

    return input_info


def record_wav(pyaudio: PyAudio, input_info: dict, cfg: Config, channels: int = 1) \
        -> Tuple[int, array]:
    """
    Record a word or words from the microphone and
    return the data as an array of signed shorts.

    Normalizes the audio, trims silence from the
    start and end, and pads with 0.5 seconds of
    blank sound to make sure VLC et al can play
    it without getting chopped off.
    """
    stream = pyaudio.open(
        format=WAV_FORMAT,
        channels=channels,
        rate=int(input_info.get("defaultSampleRate")),
        input_device_index=int(input_info.get("index")),
        input=True,
        frames_per_buffer=WAV_CHUNK_SIZE,
    )

    num_silent = 0
    snd_started = False

    _r = array("h")

    while True:
        # little endian, signed short
        snd_data = array("h", stream.read(WAV_CHUNK_SIZE, exception_on_overflow=False))
        if byteorder == "big":
            snd_data.byteswap()
        _r.extend(snd_data)

        silent = is_silent(snd_data, cfg)

        if silent and snd_started:
            num_silent += 1
        elif not silent and not snd_started:
            snd_started = True

        if snd_started and num_silent > 30:
            break

    sample_width = pyaudio.get_sample_size(WAV_FORMAT)
    stream.stop_stream()
    stream.close()
    pyaudio.terminate()

    _r = trim(_r, cfg)
    return sample_width, _r


def __write_wav(input_info: dict, channels: int, sample_width: int, data: array,
                _wf: wave.Wave_write):
    """Take input from device recording (in memory) and write it to a WAV file"""
    _wf.setnchannels(channels)
    _wf.setsampwidth(sample_width)
    _wf.setframerate(int(input_info.get("defaultSampleRate")))
    _wf.writeframes(data)


def record_ogg(oggfile: NamedTemporaryFile, cfg: Config) -> str:
    """Records from the microphone and outputs the resulting data to 'path'
    """

    pyaudio = PyAudio()
    input_info = detect_input(pyaudio, cfg)
    channels = min(int(input_info.get("maxInputChannels")), 4)

    sample_width, data = record_wav(pyaudio, input_info, cfg, channels)
    data = pack("<" + ("h" * len(data)), *data)

    with NamedTemporaryFile(
        "wb", prefix="intercom.recording.", suffix=".wav", delete=False
    ) as wavfile:

        with wave.open(wavfile.name, mode="wb") as _wf:
            __write_wav(input_info, channels, sample_width, data, _wf)

        ffmpeg = ffmpy.FFmpeg(
            inputs={wavfile.name: None}, outputs={oggfile.name: ["-y", "-f", "ogg"]}
        )
        ffmpeg.run()

    os.remove(wavfile.name)


def playback_ogg(filename: str, cfg: Config):
    """ Play a .ogg file using VLC
    """
    _v = vlc.Instance("--aout=alsa")
    _p = _v.media_player_new()
    vlc.libvlc_audio_set_volume(_p, cfg.volume)

    _m = _v.media_new(filename)
    _p.set_media(_m)
    _p.play()

"""
Capture and play audio for use with Telegram. Uses ffmpeg for recording and vlc for playback.
"""
import logging
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

from intercompy.config import Audio

WAV_FORMAT = paInt16
WAV_CHUNK_SIZE = 4096

logger = logging.getLogger(__name__)

# WAV recording logic is adapted from:
# https://stackoverflow.com/questions/892199/detect-record-audio-in-python


def is_silent(snd_data: array, cfg: Audio) -> bool:
    "Returns 'True' if below the 'silent' threshold"
    return max(snd_data) < cfg.wav_threshold


def trim(snd_data: array, cfg: Audio) -> array:
    """Trim the blank spots at the start and end
    """

    def _trim(_sd: array, _c: Audio) -> array:
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

    in_channels = int(dev.get("maxInputChannels"))
    return 0 < in_channels < 3


def detect_input(pyaudio: PyAudio, cfg: Audio) -> dict:
    """
    Find the audio input device
    """

    device = cfg.audio_device
    device_name = None
    device_index = None
    if isinstance(device, str):
        device_name = device
    else:
        device_index = device

    input_info = pyaudio.get_default_input_device_info()
    device_count = pyaudio.get_device_count()

    if input_info is None and device_index is not None and device_index < device_count-1:
        dev = pyaudio.get_device_info_by_index(int(device_index))
        if __is_valid_input(dev):
            input_info = dev
        else:
            logger.error("Configured input device %s is INVALID! Info:\n\n%s", device_index, dev)

    if input_info is None:
        logger.info("Selecting a candidate input device from the list...")
        for idx in range(device_count):
            dev = pyaudio.get_device_info_by_index(idx)
            if __is_valid_input(dev):
                if device_name is None or dev['name'] == device_name:
                    input_info = dev
                    break

    if input_info is None:
        logger.error("No valid input devices found!")

    return input_info


async def record_wav(pyaudio: PyAudio, input_info: dict, cfg: Audio, channels: int, stop_fn=None) \
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

        if silent:
            logger.debug(
                "Silence detected. Number of contiguous, silent samples so far: %s",
                num_silent
            )
            if snd_started:
                logger.debug("Silent++")
                num_silent += 1
        else:
            logger.debug("Sound detected")
            if not snd_started:
                logger.debug("Sound started")
                snd_started = True
            else:
                # We're resetting here, since we want to count CONSECUTIVE silent samples
                num_silent = 0

        if snd_started:
            if stop_fn is not None:
                print(f"Using stop function: {stop_fn}")
                if await stop_fn():
                    logger.debug("Got the recording. Formatting / returning")
                    break
            elif num_silent > cfg.wav_silence_threshold:
                logger.debug("Got the recording. Formatting / returning")
                break

    sample_width = pyaudio.get_sample_size(WAV_FORMAT)
    logger.debug("Got sample width")
    stream.stop_stream()
    logger.debug("stream stopped")
    stream.close()
    logger.debug("stream closed")

    _r = trim(_r, cfg)
    logger.debug("audio sample has been trimmed")
    return sample_width, _r


def __write_wav(input_info: dict, channels: int, sample_width: int, data: bytes,
                _wf: wave.Wave_write):
    """Take input from device recording (in memory) and write it to a WAV file"""
    _wf.setnchannels(channels)
    _wf.setsampwidth(sample_width)
    _wf.setframerate(int(input_info.get("defaultSampleRate")))
    _wf.writeframes(data)


async def record_ogg(oggfile: NamedTemporaryFile, cfg: Audio, stop_fn=None):
    """Records from the microphone and outputs the resulting data to 'path'
    """

    pyaudio = PyAudio()
    try:
        input_info = detect_input(pyaudio, cfg)
        if input_info is None:
            raise Exception("Cannot find valid input!")
        channels = min(int(input_info.get("maxInputChannels")), 4)

        sample_width, data = await record_wav(pyaudio, input_info, cfg, channels, stop_fn)
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
    finally:
        pyaudio.terminate()
        print("pyaudio terminated")


def playback_ogg(filename: str, cfg: Audio):
    """ Play a .ogg file using VLC
    """
    _v = vlc.Instance("--aout=alsa")
    _p = _v.media_player_new()
    vlc.libvlc_audio_set_volume(_p, cfg.volume)

    _m = _v.media_new(filename)
    _p.set_media(_m)
    _p.play()


def get_input_devices(pyaudio: PyAudio) -> dict:
    """Retrieve the list of viable recording devices"""
    devices = []

    count = pyaudio.get_device_count()
    logger.debug("Checking %s devices...", count)
    for idx in range(count):
        dev = pyaudio.get_device_info_by_index(idx)
        logger.debug("Checking device: %(index)s - %(name)s", dev)
        if __is_valid_input(dev):
            # dev['index'] = idx
            logger.debug("adding device: %(index)s - %(name)s", dev)
            devices.append(dev)

    return devices

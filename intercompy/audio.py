from typing import Tuple

import vlc
import ffmpy

from sys import byteorder
from array import array
from struct import pack

from pyaudio import PyAudio, paInt16
import wave
import os

from tempfile import NamedTemporaryFile

from intercompy.config import WAV_THRESHOLD, Config

WAV_FORMAT = paInt16
WAV_CHUNK_SIZE = 4096

# WAV recording logic is adapted from:
# https://stackoverflow.com/questions/892199/detect-record-audio-in-python


def is_silent(snd_data: array, cfg: Config) -> bool:
    "Returns 'True' if below the 'silent' threshold"
    return max(snd_data) < WAV_THRESHOLD


def trim(snd_data: array, cfg: Config) -> array:
    "Trim the blank spots at the start and end"

    def _trim(sd: array, c: Config) -> array:
        snd_started = False
        r = array("h")

        for i in sd:
            if not snd_started and abs(i) > WAV_THRESHOLD:
                snd_started = True
                r.append(i)

            elif snd_started:
                r.append(i)
        return r

    # Trim to the left
    snd_data = _trim(snd_data, cfg)

    # Trim to the right
    snd_data.reverse()
    snd_data = _trim(snd_data, cfg)
    snd_data.reverse()
    return snd_data


def detect_input(pyaudio: PyAudio, cfg: Config) -> dict:
    input_info = pyaudio.get_default_input_device_info()
    if input_info is None:
        pyaudio = PyAudio()
        lines = []
        for idx in range(pyaudio.get_device_count()):
            dev = pyaudio.get_device_info_by_index(idx)
            if int(dev.get("maxInputChannels")) > 0:
                input_info = dev
                break

    return input_info


def record_wav(pyaudio: PyAudio, input_info: dict, cfg: Config, channels: int = 1) -> Tuple[int, array]:
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

    r = array("h")

    while True:
        # little endian, signed short
        snd_data = array("h", stream.read(WAV_CHUNK_SIZE, exception_on_overflow=False))
        if byteorder == "big":
            snd_data.byteswap()
        r.extend(snd_data)

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

    r = trim(r, cfg)
    return sample_width, r


def record_ogg(cfg: Config) -> str:
    "Records from the microphone and outputs the resulting data to 'path'"

    wavfile = NamedTemporaryFile(
        "wb", prefix="intercom.recording.", suffix=".wav", delete=False
    )
    oggfile = NamedTemporaryFile(
        "wb", prefix="intercom.voice-out.", suffix=".ogg", delete=False
    )

    pyaudio = PyAudio()
    input_info = detect_input(pyaudio, cfg)
    channels = int(input_info.get("maxInputChannels"))
    if channels > 4:
        channels = 4

    sample_width, data = record_wav(pyaudio, input_info, cfg, channels)
    data = pack("<" + ("h" * len(data)), *data)

    with wave.open(wavfile.name, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(int(input_info.get("defaultSampleRate")))
        wf.writeframes(data)

    ffmpeg = ffmpy.FFmpeg(
        inputs={wavfile.name: None}, outputs={oggfile.name: ["-y", "-f", "ogg"]}
    )
    ffmpeg.run()

    os.remove(wavfile.name)

    return oggfile.name


def playback_ogg(filename: str, cfg: Config):
    volume = 75  # TODO: Replace with config param

    v = vlc.Instance("--aout=alsa")
    p = v.media_player_new()
    vlc.libvlc_audio_set_volume(p, volume)

    m = v.media_new(filename)
    p.set_media(m)
    p.play()

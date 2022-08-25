"""
Capture and play audio for use with Telegram. Uses ffmpeg for recording and vlc for playback.
"""
import logging
import os
import wave
from array import array
from asyncio import sleep
from struct import pack
from sys import byteorder
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Tuple, Optional

import ffmpy
import speech_recognition as sr
import vlc
from gtts import gTTS as tts
from pyaudio import PyAudio, paInt16
from pydub import AudioSegment
from pydub.silence import split_on_silence

from .config import Audio

WAV_FORMAT = paInt16
WAV_CHUNK_SIZE = 4096

logger = logging.getLogger(__name__)

# WAV recording logic is adapted from:
# https://stackoverflow.com/questions/892199/detect-record-audio-in-python

SND_INTERCOM_ONLINE = ("intercom-online", "Your intercom is now online.")
SND_PROCESSING_RECORDING = ("processing-recording", "Processing your recording.")
SND_RECORD_YOUR_MESSAGE = ("record-message", "Please record your message.")
SND_SENDING_MESSAGE = ("sending-message", "Sending audio message.")
SND_SNOOPING_AUDIO_START = (
    "snoop-audio-start",
    "Starting remote recording in 3 seconds.",
)

PROMPTS = [
    SND_INTERCOM_ONLINE,
    SND_PROCESSING_RECORDING,
    SND_RECORD_YOUR_MESSAGE,
    SND_SENDING_MESSAGE,
    SND_SNOOPING_AUDIO_START,
]

RECORDINGS = {}


def setup_audio(cfg: Audio):
    """Pre-record all prompts at startup to avoid lag when messaging."""
    for prompt in PROMPTS:
        record_prompt(prompt, cfg)


async def speech_to_text(soundfile: NamedTemporaryFile) -> str:
    """
    Transform a recorded voice to text for sending separately, to help in high-noise
    environments on the receiving end
    """

    recognizer = sr.Recognizer()
    sound = AudioSegment.from_ogg(soundfile.name)

    chunks = split_on_silence(
        sound, min_silence_len=100, silence_thresh=sound.dBFS - 24, keep_silence=100
    )
    translation = []
    with TemporaryDirectory("intercom.speech-to-text") as tdname:
        for i, chunk in enumerate(chunks, start=1):
            fname = os.path.join(tdname, f"chunk{i}.wav")
            chunk.export(fname, format="wav")

            with sr.AudioFile(fname) as source:
                aud = recognizer.record(source)
                try:
                    text = recognizer.recognize_google(aud)
                    translation.append(text)
                except sr.UnknownValueError as error:
                    logger.warning("Translation error: %s", error)
                    translation.append("*garbled*")

    return " ".join(translation)


def record_prompt(snd: Tuple[str, str], cfg: Audio) -> str:
    """Record a standard audio prompt for a given text directive, for later use"""

    # pylint: disable=consider-using-with
    key = snd[0]

    prompts_dir = os.path.join(
        cfg.audio_dir, f"prompts-{cfg.text_lang}-{cfg.text_accent}"
    )
    if not os.path.isdir(prompts_dir):
        os.makedirs(prompts_dir)

    fname = os.path.join(prompts_dir, f"intercom.prompt.{key}.ogg")

    if not os.path.exists(fname):
        logger.debug("Generating prompt audio %s at: %s", key, fname)

        prompts = cfg.prompts
        txt = prompts.get(key) or snd[1]
        speech = tts(txt, lang=cfg.text_lang, tld=cfg.text_accent)
        logger.debug("Saving generated speech data for: %s", key)
        speech.save(fname)

    RECORDINGS[key] = fname
    return fname


async def play_prompt_text(snd: Tuple[str, str], cfg: Audio):
    """Play a standard prompt text, and cache the audio file for reuse."""

    key = snd[0]
    message_file = RECORDINGS.get(key)
    if message_file is None:
        message_file = record_prompt(snd, cfg)

    logger.debug("Playing sound: %s from file: %s", key, message_file)
    await playback_ogg(message_file, cfg)


async def play_impromptu_text(text: str, cfg: Audio):
    """Play an impromptu prompt text, without caching the audio file for reuse."""

    with NamedTemporaryFile(
        "wb", prefix="intercom.text.", suffix=".ogg", delete=True
    ) as msg:
        speech = tts(text, lang=cfg.text_lang, tld=cfg.text_accent)
        logger.debug("Saving generated speech data")
        speech.save(msg.name)

        logger.debug("Playing sound for: '%s' from file: %s", text, msg.name)
        await playback_ogg(msg.name, cfg)


async def record_ogg(cfg: Audio, stop_fn=None) -> NamedTemporaryFile:
    """Records from the microphone and outputs the resulting data to 'path'"""

    # pylint: disable=consider-using-with
    oggfile = NamedTemporaryFile(
        "wb", prefix="intercom.voice-out.", suffix=".ogg", delete=False
    )

    pyaudio = PyAudio()

    try:
        input_info = _detect_input(pyaudio, cfg)
        if input_info is None:
            raise Exception("Cannot find valid input!")
        channels = min(int(input_info.get("maxInputChannels")), 2)

        logger.info("Starting WAV recording with %d channels.", channels)
        sample_width, data = await _record_wav(
            pyaudio, input_info, cfg, channels, stop_fn
        )
    finally:
        pyaudio.terminate()
        print("pyaudio terminated")

    with NamedTemporaryFile(
        "wb", prefix="intercom.voice-out.", suffix=".wav"
    ) as wavfile:
        logger.debug("Packing WAV data")
        data = pack("<" + ("h" * len(data)), *data)

        logger.info("Writing WAV file")
        with wave.open(wavfile.name, mode="wb") as _wf:
            _write_wav(input_info, channels, sample_width, data, _wf)

        await play_prompt_text(SND_PROCESSING_RECORDING, cfg)

        logger.info("Converting WAV to OGG")
        ffmpeg = ffmpy.FFmpeg(
            inputs={wavfile.name: None}, outputs={oggfile.name: ["-y", "-f", "ogg"]}
        )
        ffmpeg.run()
        logger.info("OGG file recorded to: %s", oggfile.name)

        return oggfile


async def playback_ogg(filename: str, cfg: Audio, vol_override: Optional[int] = None):
    """Play an .ogg file"""
    vol = vol_override or cfg.volume

    _v = vlc.Instance("--aout=alsa")
    _p = _v.media_player_new()
    vlc.libvlc_audio_set_volume(_p, vol)

    _m = _v.media_new(filename)
    _p.set_media(_m)
    _p.play()

    finished = False
    while not finished:
        state = _p.get_state()
        if state in (vlc.State.Ended, vlc.State.Error, vlc.State.Stopped):
            finished = True

        await sleep(0.5)


def _is_silent(snd_data: array, cfg: Audio) -> bool:
    """Returns 'True' if below the 'silent' threshold"""
    return max(snd_data) < cfg.wav_threshold


def _trim(snd_data: array, cfg: Audio) -> array:
    """Trim the blank spots at the start and end"""

    # Trim to the left
    logger.info("Trimming WAV (left side) from: %d frames", len(snd_data))
    snd_started = False
    end = len(snd_data)
    i = 0
    while i < end:
        if not snd_started:
            if abs(i) > cfg.wav_threshold:
                snd_started = True
            else:
                snd_data.remove(i)

        i += 1

    # Trim to the right
    logger.info("Trimming WAV (right side) from: %d frames", len(snd_data))
    snd_started = False
    i = len(snd_data) - 1
    while i >= 0:
        if not snd_started:
            if abs(i) > cfg.wav_threshold:
                snd_started = True
            else:
                snd_data.remove(i)

        i -= 1

    logger.info("Resulting recording has %d frames", len(snd_data))
    return snd_data


def _is_valid_input(dev) -> bool:
    """Determine whether the given audio device is suitable for recording voice."""

    in_channels = int(dev.get("maxInputChannels"))
    return 0 < in_channels < 3


def _detect_input(pyaudio: PyAudio, cfg: Audio) -> dict:
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

    if (
        input_info is None
        and device_index is not None
        and device_index < device_count - 1
    ):
        dev = pyaudio.get_device_info_by_index(int(device_index))
        if _is_valid_input(dev):
            input_info = dev
        else:
            logger.error(
                "Configured input device %s is INVALID! Info:\n\n%s", device_index, dev
            )

    if input_info is None:
        logger.info("Selecting a candidate input device from the list...")
        for idx in range(device_count):
            dev = pyaudio.get_device_info_by_index(idx)
            if _is_valid_input(dev):
                if device_name is None or dev["name"] == device_name:
                    input_info = dev
                    break

    if input_info is None:
        logger.error("No valid input devices found!")

    logger.info("Recording using device: %s", input_info)
    return input_info


async def _record_wav(
    pyaudio: PyAudio, input_info: dict, cfg: Audio, channels: int, stop_fn=None
) -> Tuple[int, array]:
    """
    Record a word or words from the microphone and
    return the data as an array of signed shorts.

    Normalizes the audio, trims silence from the
    start and end, and pads with 0.5 seconds of
    blank sound to make sure VLC et al can play
    it without getting chopped off.
    """
    logger.info("Opening pyAudio stream")
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

    logger.info("Detecting voice message")
    while True:
        # little endian, signed short
        snd_data = array("h", stream.read(WAV_CHUNK_SIZE, exception_on_overflow=False))
        if byteorder == "big":
            snd_data.byteswap()
        _r.extend(snd_data)

        silent = _is_silent(snd_data, cfg)

        if silent:
            if snd_started:
                num_silent += 1
        else:
            if not snd_started:
                snd_started = True
            else:
                # We're resetting here, since we want to count CONSECUTIVE silent samples
                num_silent = 0

        if snd_started:
            if stop_fn is not None:
                if await stop_fn():
                    logger.info(
                        "Got the recording based on stop_fn. Formatting / returning"
                    )
                    break
            elif num_silent > cfg.wav_silence_threshold:
                logger.info(
                    "Got the recording based on silence. Formatting / returning"
                )
                break

    logger.info("Finished capturing voice message")

    sample_width = pyaudio.get_sample_size(WAV_FORMAT)
    logger.debug("Got sample width %d", sample_width)

    stream.stop_stream()
    stream.close()

    _r = _trim(_r, cfg)
    logger.info("audio sample has been trimmed to %d frames", len(_r))
    return sample_width, _r


def _write_wav(
    input_info: dict,
    channels: int,
    sample_width: int,
    data: bytes,
    _wf: wave.Wave_write,
):
    """Take input from device recording (in memory) and write it to a WAV file"""
    _wf.setnchannels(channels)
    _wf.setsampwidth(sample_width)
    _wf.setframerate(int(input_info.get("defaultSampleRate")))
    _wf.writeframes(data)

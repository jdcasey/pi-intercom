"""Text enhancement and analysis utilities"""
from logging import getLogger

import nltk

from .config import Audio

logger = getLogger(__name__)


def setup_text_analysis():
    """Setup natural language processing"""
    nltk.download("punkt")


async def format_inbound_message_for_speech(txt: str, cfg: Audio) -> str:
    """Insert any quirky text modifications, such as to make the message sound like a telegram"""
    result = txt
    if cfg.text_msg_line_ending:
        # tokenizer = nltk_load("tokenizers/punkt/english.pickle")
        sep = f"{cfg.text_msg_line_ending}\n"
        result = sep.join(nltk.sent_tokenize(txt))

    logger.info("Formatted message is: '%s'", result)
    return result

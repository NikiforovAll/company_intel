from __future__ import annotations

import re
import unicodedata

from langdetect import LangDetectException, detect

MAX_LENGTH = 50_000
MIN_LENGTH = 50

_MULTI_NEWLINE = re.compile(r"\n{3,}")
_MULTI_SPACE = re.compile(r"[ \t]{2,}")
_MD_IMAGE = re.compile(r"!\[[^\]]*\]\([^)]*\)")
_BARE_URL = re.compile(r"(?<!\()\bhttps?://\S+")
_WIKI_EDIT = re.compile(r"\[edit\]")
_WIKI_CITE = re.compile(r"\[\d+\]")
_SKIP_LINE = re.compile(r"^Skip to main content$", re.MULTILINE)
_SLIDE_INDICATOR = re.compile(r"Slide \d+ of \d+")
_COOKIE_BLOCK = re.compile(
    r"(?:^|\n)#{1,3} Cookie (?:policy|settings).*?(?=\n#|\Z)", re.DOTALL
)


def clean_text(raw: str) -> str | None:
    text = unicodedata.normalize("NFC", raw)
    text = _MD_IMAGE.sub("", text)
    text = _BARE_URL.sub("", text)
    text = _WIKI_EDIT.sub("", text)
    text = _WIKI_CITE.sub("", text)
    text = _SKIP_LINE.sub("", text)
    text = _SLIDE_INDICATOR.sub("", text)
    text = _COOKIE_BLOCK.sub("", text)
    text = _MULTI_NEWLINE.sub("\n\n", text)
    text = _MULTI_SPACE.sub(" ", text)
    text = text.strip()
    if len(text) < MIN_LENGTH:
        return None
    if len(text) > MAX_LENGTH:
        text = text[:MAX_LENGTH]
    return text


def is_english(text: str) -> bool:
    try:
        return bool(detect(text) == "en")
    except LangDetectException:
        return True

"""Parse a WhatsApp `.txt` export into clean structured messages.

Designed against a real export, handling every edge case observed in it:

  * Timestamp prefix `M/D/YY, HH:MM - ` (US month/day, 2-digit year, 24-hour).
  * Multi-line messages whose continuation lines (including blank lines inside
    the body) carry no timestamp prefix.
  * Phone-number senders (`+91 94451 23479`), plain names (`Shashank VIT`), and
    unicode / `~`-prefixed names (`~ AᏒᎨᏃᎯ`).
  * System / notification lines (joins, adds, leaves, settings changes, the
    encryption notice) — including the trap line
    `+91 ... added you to a group in the community: 'Aspirations'` which contains
    a colon and would otherwise be misread as a user message.
  * Media placeholders (`<Media omitted>`), deleted messages
    (`This message was deleted`), and the trailing edit marker
    `<This message was edited>`.
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

from .models import Message


class ChatParseError(Exception):
    """Raised when an export cannot be read or contains no parseable messages."""


# A new logical message starts with: M/D/YY, HH:MM -  (then the body).
# Day/month/hour may be 1 or 2 digits; year is 2 digits; 24-hour clock.
_TS_RE = re.compile(
    r"^(?P<m>\d{1,2})/(?P<d>\d{1,2})/(?P<y>\d{2}), "
    r"(?P<H>\d{1,2}):(?P<M>\d{2}) - (?P<body>.*)$"
)

# Substrings that mark a line as a system/notification event rather than a
# message someone typed. Checked against the candidate sender (the part before
# the first ": ") so they never match incidental phrasing inside real chat text.
_SYSTEM_PATTERNS = (
    "added you to a group in the community",
    "joined using a group link",
    "joined using your invite link",
    "joined from the community",
    " was added",
    " added ",
    " left",
    " removed ",
    "created group ",
    "changed this group's ",
    "changed the group ",
    "changed their phone number",
    "changed the subject",
    "changed to ",
    "You were added",
    "Messages and calls are end-to-end encrypted",
    "pinned a message",
    "turned on ",
    "turned off ",
    "deleted this group's icon",
    "now an admin",
    "no longer an admin",
)

# Lines that are themselves complete system messages (no sender, no colon split).
_MEDIA_MARKER = "<Media omitted>"
_DELETED_MARKERS = ("This message was deleted", "You deleted this message")
_EDITED_SUFFIX = "<This message was edited>"


def _looks_like_system(candidate: str) -> bool:
    return any(pat in candidate for pat in _SYSTEM_PATTERNS)


def _parse_timestamp(m: re.Match) -> datetime:
    # %y maps 00-68 -> 2000-2068, so "26" -> 2026 as intended.
    return datetime.strptime(
        f"{m['m']}/{m['d']}/{m['y']}, {m['H']}:{m['M']}", "%m/%d/%y, %H:%M"
    )


def _classify(idx: int, ts: datetime, body: str) -> Message:
    """Turn a reassembled record body into a typed Message."""
    # Split sender from text only on the first ": ". A system line either has no
    # ": " at all, or its pre-colon part matches a known system pattern.
    sender: str | None = None
    text = body

    if ": " in body:
        candidate, rest = body.split(": ", 1)
        # A real sender is a single line; a multi-line "candidate" means the
        # colon lives inside the message body, not in a "Sender: text" header.
        if "\n" not in candidate and not _looks_like_system(candidate):
            sender = candidate
            text = rest

    if sender is None:
        # No usable sender -> system / notification event.
        return Message(id=idx, timestamp=ts, sender=None, text=body, is_system=True)

    is_edited = False
    if text.rstrip().endswith(_EDITED_SUFFIX):
        text = text.rstrip()[: -len(_EDITED_SUFFIX)].rstrip()
        is_edited = True

    is_media = text.strip() == _MEDIA_MARKER
    is_deleted = text.strip() in _DELETED_MARKERS

    return Message(
        id=idx,
        timestamp=ts,
        sender=sender,
        text=text,
        is_media=is_media,
        is_deleted=is_deleted,
        is_edited=is_edited,
    )


def parse_chat(path: str | Path) -> list[Message]:
    """Parse an export file into a list of `Message` objects.

    Raises `ChatParseError` for a missing/empty file or an export with no
    recognizable messages.
    """
    p = Path(path)
    if not p.exists():
        raise ChatParseError(f"File not found: {p}")

    try:
        raw = p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # Some exports (older Android/iOS) use UTF-8 with a BOM or latin-1.
        raw = p.read_text(encoding="utf-8-sig", errors="replace")

    if not raw.strip():
        raise ChatParseError(f"File is empty: {p}")

    # Pass 1: group physical lines into records. A line starting with a timestamp
    # opens a new record; anything else (including blank lines) belongs to the
    # body of the current record.
    records: list[tuple[datetime, str]] = []
    cur_ts: datetime | None = None
    cur_lines: list[str] = []

    def flush() -> None:
        if cur_ts is not None:
            records.append((cur_ts, "\n".join(cur_lines)))

    for line in raw.splitlines():
        m = _TS_RE.match(line)
        if m:
            flush()
            cur_ts = _parse_timestamp(m)
            cur_lines = [m["body"]]
        elif cur_ts is not None:
            cur_lines.append(line)
        # Lines before the first timestamp (rare/none) are ignored.
    flush()

    if not records:
        raise ChatParseError(
            f"No WhatsApp messages found in {p}. Expected lines like "
            "'4/9/26, 19:24 - Name: message'. Is this a WhatsApp .txt export?"
        )

    # Pass 2: classify each record.
    return [_classify(i, ts, body) for i, (ts, body) in enumerate(records)]

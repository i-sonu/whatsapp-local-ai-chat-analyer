"""Data model for a single parsed chat message."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    """One message (or system event) from a WhatsApp export.

    `id` is a stable index into the parsed sequence and is the join key that
    survives the embed -> retrieve -> cite pipeline, so a citation can always be
    traced back to the exact original message.
    """

    id: int
    timestamp: datetime
    sender: str | None  # None for system/notification messages
    text: str
    is_system: bool = False
    is_media: bool = False
    is_deleted: bool = False
    is_edited: bool = False

    @property
    def is_human(self) -> bool:
        """True for real, embeddable text messages (the only thing we index)."""
        return (
            not self.is_system
            and not self.is_media
            and not self.is_deleted
            and bool(self.text.strip())
        )

    def to_dict(self) -> dict:
        """JSON-serializable form with ISO 8601 timestamp + convenience fields."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "date": self.timestamp.strftime("%Y-%m-%d"),
            "time": self.timestamp.strftime("%H:%M"),
            "sender": self.sender,
            "text": self.text,
            "is_system": self.is_system,
            "is_media": self.is_media,
            "is_deleted": self.is_deleted,
            "is_edited": self.is_edited,
        }

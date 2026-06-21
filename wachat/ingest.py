"""Parse -> filter -> embed -> persist.

Builds a local Chroma vector store from the human messages in an export, and
writes the full structured parse (every message, including system/media/deleted)
to JSON. Each embedded document keeps the metadata needed to cite it later:
message id, sender, ISO timestamp, and split date/time.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import config
from .models import Message
from .parser import parse_chat


def _embeddings(embed_model: str):
    # Imported lazily so `--help` and parsing don't pay the heavy import cost.
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(model_name=embed_model)


def _to_document(msg: Message):
    from langchain_core.documents import Document

    return Document(
        page_content=msg.text,
        metadata={
            "id": msg.id,
            "sender": msg.sender or "",
            "timestamp": msg.timestamp.isoformat(),
            "date": msg.timestamp.strftime("%Y-%m-%d"),
            "time": msg.timestamp.strftime("%H:%M"),
            "is_edited": msg.is_edited,
        },
    )


def write_json(messages: list[Message], json_out: str | Path) -> Path:
    """Write the full structured parse to disk and return the path."""
    out = Path(json_out)
    out.write_text(
        json.dumps([m.to_dict() for m in messages], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return out


def ingest(
    chat_path: str | Path,
    db_path: str | Path = config.DB_PATH,
    embed_model: str = config.EMBED_MODEL,
    json_out: str | Path = config.JSON_OUT,
    reingest: bool = False,
) -> int:
    """Parse the export, persist the vector store, and write JSON.

    Returns the number of human messages embedded. If a store already exists and
    `reingest` is False, the existing store is reused (no re-embedding).
    """
    from langchain_chroma import Chroma

    db_path = Path(db_path)

    messages = parse_chat(chat_path)
    write_json(messages, json_out)

    human = [m for m in messages if m.is_human]
    if not human:
        from .parser import ChatParseError

        raise ChatParseError(
            "The export parsed, but it contains no human text messages to index "
            "(only system/media/deleted lines)."
        )

    if db_path.exists() and not reingest:
        return len(human)

    if db_path.exists():
        shutil.rmtree(db_path)

    docs = [_to_document(m) for m in human]
    Chroma.from_documents(
        documents=docs,
        embedding=_embeddings(embed_model),
        persist_directory=str(db_path),
        collection_name=config.COLLECTION,
    )
    return len(human)

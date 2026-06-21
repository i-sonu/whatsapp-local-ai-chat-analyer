"""Load the vector store and retrieve messages for a question.

Produces two things from a query: a numbered context block fed to the LLM, and a
citation map (number -> original message metadata) used to render the Sources
section. Citations therefore always point back to real, retrieved messages.
"""

from __future__ import annotations

from pathlib import Path

from . import config


class RetrieverError(Exception):
    """Raised when the vector store is missing or unreadable."""


class Retriever:
    def __init__(
        self,
        db_path: str | Path = config.DB_PATH,
        embed_model: str = config.EMBED_MODEL,
    ):
        db_path = Path(db_path)
        if not db_path.exists():
            raise RetrieverError(
                f"No vector store at '{db_path}'. Run `wachat ingest <chat.txt>` "
                "first."
            )

        from langchain_chroma import Chroma
        from langchain_huggingface import HuggingFaceEmbeddings

        self._store = Chroma(
            persist_directory=str(db_path),
            embedding_function=HuggingFaceEmbeddings(model_name=embed_model),
            collection_name=config.COLLECTION,
        )

    def retrieve(self, query: str, k: int = config.K):
        """Return (context_block, citation_map) for a query.

        `citation_map` maps the 1-based citation number to a dict with sender,
        date, time and exact text of the source message.
        """
        docs = self._store.similarity_search(query, k=k)

        lines: list[str] = []
        citation_map: dict[int, dict] = {}
        for n, doc in enumerate(docs, start=1):
            md = doc.metadata
            sender = md.get("sender") or "Unknown"
            date = md.get("date", "")
            time = md.get("time", "")
            text = doc.page_content
            lines.append(f"[{n}] {sender} ({date}, {time}): {text}")
            citation_map[n] = {
                "sender": sender,
                "date": date,
                "time": time,
                "text": text,
            }

        context_block = "\n".join(lines)
        return context_block, citation_map

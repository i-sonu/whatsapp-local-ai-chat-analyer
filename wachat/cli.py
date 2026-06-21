"""Typer CLI: `run` (ingest + chat), `ingest`, and `chat`."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.text import Text

from . import config
from .chat import make_console
from .parser import ChatParseError

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="Turn an exported WhatsApp chat into a citation-backed local chatbot.",
)
console = make_console()


def _fail(message: str) -> None:
    console.print(Text(message, style="bold red"))
    raise typer.Exit(code=1)


def _do_ingest(
    chat_file: Path,
    db_path: Path,
    embed_model: str,
    json_out: Path,
    reingest: bool,
) -> int:
    from .ingest import ingest

    try:
        with console.status("parsing and embedding messages...", spinner="dots"):
            count = ingest(
                chat_path=chat_file,
                db_path=db_path,
                embed_model=embed_model,
                json_out=json_out,
                reingest=reingest,
            )
    except ChatParseError as exc:
        _fail(str(exc))
    console.print(
        Text(f"Indexed {count} messages  ", style="green")
        + Text(f"(store: {db_path}, json: {json_out})", style="grey62")
    )
    return count


def _start_chat(db_path: Path, embed_model: str, model: str, ollama_url: str, k: int):
    from .chat import ChatEngine, run_chat_loop
    from .retrieval import Retriever, RetrieverError

    try:
        retriever = Retriever(db_path=db_path, embed_model=embed_model)
    except RetrieverError as exc:
        _fail(str(exc))

    engine = ChatEngine(retriever, model=model, ollama_url=ollama_url, k=k)
    run_chat_loop(engine, console=console)


@app.command()
def run(
    chat_file: Path = typer.Argument(..., help="Path to the WhatsApp .txt export."),
    model: str = typer.Option(config.MODEL, help="Ollama model to use."),
    db_path: Path = typer.Option(config.DB_PATH, help="Vector store directory."),
    embed_model: str = typer.Option(config.EMBED_MODEL, help="Embedding model."),
    json_out: Path = typer.Option(config.JSON_OUT, help="Structured JSON output."),
    k: int = typer.Option(config.K, help="Messages retrieved per question."),
    ollama_url: str = typer.Option(config.OLLAMA_URL, help="Ollama base URL."),
    reingest: bool = typer.Option(False, help="Rebuild the index from scratch."),
):
    """Ingest the export (or reuse an existing index) and start chatting."""
    _do_ingest(chat_file, db_path, embed_model, json_out, reingest)
    _start_chat(db_path, embed_model, model, ollama_url, k)


@app.command()
def ingest(
    chat_file: Path = typer.Argument(..., help="Path to the WhatsApp .txt export."),
    db_path: Path = typer.Option(config.DB_PATH, help="Vector store directory."),
    embed_model: str = typer.Option(config.EMBED_MODEL, help="Embedding model."),
    json_out: Path = typer.Option(config.JSON_OUT, help="Structured JSON output."),
    reingest: bool = typer.Option(False, help="Rebuild the index from scratch."),
):
    """Parse the export, build the vector store, and write structured JSON."""
    _do_ingest(chat_file, db_path, embed_model, json_out, reingest)


@app.command()
def chat(
    model: str = typer.Option(config.MODEL, help="Ollama model to use."),
    db_path: Path = typer.Option(config.DB_PATH, help="Vector store directory."),
    embed_model: str = typer.Option(config.EMBED_MODEL, help="Embedding model."),
    k: int = typer.Option(config.K, help="Messages retrieved per question."),
    ollama_url: str = typer.Option(config.OLLAMA_URL, help="Ollama base URL."),
):
    """Chat against an already-ingested export."""
    _start_chat(db_path, embed_model, model, ollama_url, k)


if __name__ == "__main__":
    app()

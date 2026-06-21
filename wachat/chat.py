"""LLM answering with Perplexity-style inline citations + the Rich chat loop."""

from __future__ import annotations

import re
import sys

from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule
from rich.text import Text

from . import config
from .retrieval import Retriever

# Numbers the model actually used in its answer, e.g. [1] or [1, 3].
_CITE_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")

_SYSTEM_PROMPT = """You answer questions about a WhatsApp group chat using ONLY \
the numbered sources provided.

Rules:
- Use only information found in the sources. Do not use outside knowledge.
- After each factual claim, cite the source(s) it came from with inline markers \
like [1] or [2]. Place the marker right after the claim it supports.
- If several sources support a claim, cite all of them, e.g. [1][3].
- Only cite source numbers that appear in the list. Never invent a citation.
- If the sources do not contain the answer, say so plainly and do not cite.
- Be concise and factual. Do not repeat the sources verbatim as a list; weave \
the information into a natural answer with citations."""

_USER_TEMPLATE = """Sources:
{context}

Question: {question}

Answer using inline citations:"""


class OllamaUnavailable(Exception):
    """Raised when the Ollama server can't be reached or the model is missing."""


class ChatEngine:
    def __init__(
        self,
        retriever: Retriever,
        model: str = config.MODEL,
        ollama_url: str = config.OLLAMA_URL,
        k: int = config.K,
    ):
        from langchain_ollama import ChatOllama

        self.retriever = retriever
        self.k = k
        self.model = model
        self._llm = ChatOllama(model=model, base_url=ollama_url, temperature=0.2)

    def ask(self, question: str) -> tuple[str, dict[int, dict]]:
        """Return (answer_text, used_citations) for a question.

        `used_citations` contains only the sources actually referenced in the
        answer, keyed by citation number.
        """
        context, citation_map = self.retriever.retrieve(question, k=self.k)
        prompt = [
            ("system", _SYSTEM_PROMPT),
            ("human", _USER_TEMPLATE.format(context=context, question=question)),
        ]
        try:
            response = self._llm.invoke(prompt)
        except Exception as exc:  # noqa: BLE001 - normalize to a friendly error
            raise OllamaUnavailable(_friendly_ollama_error(exc, self.model)) from exc

        answer = response.content if hasattr(response, "content") else str(response)
        used = _used_citations(answer, citation_map)
        return answer.strip(), used


def _used_citations(answer: str, citation_map: dict[int, dict]) -> dict[int, dict]:
    used: dict[int, dict] = {}
    for group in _CITE_RE.findall(answer):
        for part in group.split(","):
            n = int(part.strip())
            if n in citation_map:  # ignore any number the model invented
                used[n] = citation_map[n]
    return dict(sorted(used.items()))


def _friendly_ollama_error(exc: Exception, model: str) -> str:
    msg = str(exc).lower()
    if "connection" in msg or "refused" in msg or "max retries" in msg:
        return (
            "Could not reach Ollama. Start it with `ollama serve`, then make sure "
            f"the model is available: `ollama pull {model}`."
        )
    if "not found" in msg or "no such model" in msg or "model" in msg and "pull" in msg:
        return f"Model '{model}' is not installed. Run: `ollama pull {model}`."
    return f"Ollama request failed: {exc}"


# --------------------------------------------------------------------------- UI


def make_console() -> Console:
    """A Console that renders box/unicode glyphs safely on Windows too.

    Reconfigures stdout/stderr to UTF-8 and disables Rich's legacy win32
    renderer (which raises on box-drawing chars under the cp1252 code page),
    routing output through ANSI on UTF-8 stdout instead.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    return Console(legacy_windows=False)


def render_answer(
    console: Console, answer: str, citations: dict[int, dict]
) -> None:
    """Render the answer body and a clean, distinct Sources block."""
    console.print()
    console.print(Markdown(answer))

    if not citations:
        console.print()
        return

    console.print()
    console.print(Rule(style="grey42"))
    console.print(Text("Sources", style="bold"))
    console.print()
    for n, c in citations.items():
        header = Text()
        header.append(f"[{n}] ", style="bold cyan")
        header.append(c["sender"], style="bold")
        header.append(f"  ·  {c['date']}, {c['time']}", style="grey62")
        console.print(header)

        quote = c["text"].replace("\n", " ").strip()
        console.print(Text(f'    "{quote}"', style="italic grey74"))
        console.print()


def run_chat_loop(engine: ChatEngine, console: Console | None = None) -> None:
    """Interactive REPL. Exit with /exit, /quit, or Ctrl-C / Ctrl-D."""
    console = console or make_console()

    console.print()
    console.print(Text("WhatsApp Chat — ask anything", style="bold"))
    console.print(
        Text(f"model: {engine.model}    type /exit to quit", style="grey62")
    )
    console.print(Rule(style="grey42"))

    while True:
        try:
            console.print()
            question = console.input("[bold green]you[/bold green]  ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not question:
            continue
        if question.lower() in {"/exit", "/quit", "/q"}:
            break

        try:
            with console.status("thinking...", spinner="dots"):
                answer, citations = engine.ask(question)
        except OllamaUnavailable as exc:
            console.print()
            console.print(Text(str(exc), style="bold red"))
            continue

        render_answer(console, answer, citations)

    console.print(Text("bye", style="grey62"))

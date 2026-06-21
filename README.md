<div align="center">

# 💬 WhatsApp Local AI Chat Analyzer

**Turn exported WhatsApp chats into a citation-backed local chatbot with Perplexity-style sourcing — 100% offline, no APIs, no cloud.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Status: Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=flat-square)](#)

</div>

---

## 🎯 What It Does

Export a WhatsApp group chat. Ask questions. Get answers backed by **exact citations** pointing to the original messages.

Every factual claim in the answer gets a numbered marker `[1]`, `[2]`, and a **Sources** section lists the exact sender, date, time, and original text for each citation. No hallucinations. No invented sources.

```
you  How is John Doe for DET?

John Doe is regarded as a good teacher with strong teaching quality and a 
high class average [1][2], though he is known to give a fair amount of work [1]. 
For DET specifically, some students suggest Jane Doe gives easier marks while 
Pankaj is the better teacher [3].

────────────────────────────────────────────────────────────────
Sources

[1] +91 95660 39887  ·  2026-04-10, 10:45
    "Good teacher ( teaching is good high avg ) but yeah works"

[2] +91 97909 70726  ·  2026-04-10, 10:46
    "his class has the least strength for cvla this sem"

[3] Sebastian  ·  2026-04-10, 10:57
    "Marks:Jane Doe \nTeaching:John Doe"
```

---

## ⚡ Features

<table>
<tr>
<td width="50%">

### 🔒 100% Local
- No cloud APIs
- No data leaves your machine
- Works offline
- Your chat stays private

</td>
<td width="50%">

### 🎓 Citation-Backed
- Every claim is sourced
- Inline markers `[1]`, `[2]`
- Original sender/date/time
- Exact message text

</td>
</tr>
<tr>
<td width="50%">

### 🧠 Smart Parsing
- Multi-line messages
- Media/system events
- Deleted/edited messages
- Unicode-safe

</td>
<td width="50%">

### ⚙️ Zero Config
- Sensible defaults
- All flags optional
- ~80 MB embedding model
- Single command to chat

</td>
</tr>
</table>

---

## 🚀 Quick Start

### 1. Install

```bash
git clone https://github.com/i-sonu/whatsapp-local-ai-chat-analyzer.git
cd whatsapp-local-ai-chat-analyzer
python -m venv .venv

# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -e .
```

### 2. Set Up Ollama (the local LLM)

```bash
# Install from https://ollama.com/download
# Then:
ollama pull llama3.1:8b
ollama serve          # keep this running
```

### 3. Export Your Chat

On your phone:
- Open WhatsApp → pick a group chat
- **⋮ (menu) → More → Export chat → Without media**
- Transfer the `.txt` file to your computer

### 4. Chat

```bash
wachat run "path/to/WhatsApp Chat with GroupName.txt"
```

That's it. You'll drop straight into an interactive chat session.

---

## 📖 Commands

```bash
# Ingest + Chat (primary flow)
wachat run "chat.txt"

# Just build the index
wachat ingest "chat.txt"

# Chat against an existing index
wachat chat

# Customize model, embedding, retrieval count, etc.
wachat run "chat.txt" --model qwen2.5:7b --k 8
```

**Options:**
- `--model` — Ollama model (default: `llama3.1:8b`)
- `--embed-model` — Embedding model (default: `sentence-transformers/all-MiniLM-L6-v2`)
- `--db-path` — Vector store directory (default: `chroma_db/`)
- `--json-out` — Structured JSON output (default: `parsed_messages.json`)
- `--k` — Messages retrieved per question (default: `6`)
- `--ollama-url` — Ollama server URL (default: `http://localhost:11434`)
- `--reingest` — Rebuild the index from scratch

---

## 📋 How It Works

<div style="background: #f6f8fa; padding: 20px; border-radius: 8px; margin: 20px 0;">

### The Pipeline

1. **Parse** → Read the `.txt` export, extract timestamps, senders, text
2. **Filter** → Keep human messages; exclude system/media/deleted
3. **Embed** → Convert each message to a vector using `all-MiniLM-L6-v2`
4. **Store** → Persist embeddings in local Chroma database
5. **Retrieve** → For each question, find the 6 most relevant messages
6. **Answer** → LLM (llama3.1:8b via Ollama) generates response from sources only
7. **Cite** → Extract `[1]`, `[2]` markers from answer, render Sources block

</div>

---

## 🛠️ Project Structure

```
wachat/
  ├── parser.py        Two-pass WhatsApp export parser
  ├── models.py        Message dataclass with ISO timestamps
  ├── ingest.py        Parse → embed → store pipeline
  ├── retrieval.py     Load Chroma, retrieve messages, build citation map
  ├── chat.py          Ollama integration, citation rendering, chat loop
  ├── cli.py           Typer CLI (run/ingest/chat commands)
  └── config.py        Central defaults (model, paths, K)

parsed_messages.json   Full structured parse (all messages + metadata)
chroma_db/            Local vector store (auto-created)
```

---

## 🐛 Troubleshooting

| Issue | Fix |
| --- | --- |
| **Could not reach Ollama** | Run `ollama serve` in another terminal |
| **Model not installed** | `ollama pull llama3.1:8b` |
| **File not found** | Check the path to your `.txt` export |
| **No WhatsApp messages found** | Ensure it's a WhatsApp text export (not PDF) |
| **No vector store** | Run `wachat ingest <chat.txt>` first |
| **Slow first response** | First LLM inference loads the model (~30s). Subsequent queries are faster. |

---

## 📊 Verified Against Real Data

- ✅ **Parser:** 1,720 messages (1,228 human, 292 system)
- ✅ **Media handling:** 152 `<Media omitted>` entries correctly flagged
- ✅ **Deleted messages:** 43 `This message was deleted` correctly marked
- ✅ **Edited messages:** 41 trailing `<This message was edited>` stripped + flagged
- ✅ **Multi-line messages:** Including blank lines, reassembled intact
- ✅ **Unicode support:** Including emojis, RTL text, special chars
- ✅ **Edge cases:** System messages with colons, various senders (phones, names, unicode)

---

## 🎨 Tech Stack

- **Python 3.10+** — Language
- **LangChain** — RAG orchestration
- **Chroma** — Local vector database
- **Ollama** — Local LLM inference
- **sentence-transformers** — Embedding model
- **Typer** — CLI framework
- **Rich** — Terminal UI

All free, all open-source, all run locally.

---

## 📄 Output Files

- **`parsed_messages.json`** — Complete structured parse
  ```json
  {
    "id": 125,
    "timestamp": "2026-04-10T09:21:00",
    "date": "2026-04-10",
    "time": "09:21",
    "sender": "+91 94451 23479",
    "text": "Guys, anyone has the link for summer sem registration",
    "is_system": false,
    "is_media": false,
    "is_deleted": false,
    "is_edited": false
  }
  ```

- **`chroma_db/`** — Persistent vector store (1,228 human messages indexed)

---

## 🔐 Privacy & Security

- ✅ Zero network calls — Ollama runs locally on your machine
- ✅ No API keys — No cloud dependencies
- ✅ No telemetry — Your chat never leaves your disk
- ✅ Open source — Audit the code, run it offline

---

## 📝 License

MIT. Use, modify, share freely.

---

## 🤝 Contributing

Found a bug? Have an idea? Open an issue or submit a PR.

---

<div align="center">

**Built with ❤️ for privacy-first chat analysis**

[Star on GitHub](https://github.com/i-sonu/whatsapp-local-ai-chat-analyzer) • [Report Issues](https://github.com/i-sonu/whatsapp-local-ai-chat-analyzer/issues)

</div>

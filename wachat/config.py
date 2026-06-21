"""Central configuration defaults.

Every value here is overridable from the CLI. Keeping them in one place makes the
tool easy to retarget (different model, different paths) without hunting through
the code.
"""

from __future__ import annotations

# Local LLM served by Ollama. Configurable with `--model`.
MODEL = "llama3.1:8b"

# Sentence-transformer embedding model. Runs locally on CPU, ~80MB.
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Where the Ollama daemon listens.
OLLAMA_URL = "http://localhost:11434"

# Persistent Chroma vector store directory.
DB_PATH = "chroma_db"

# Full structured parse output (ALL messages, including system/media/deleted).
JSON_OUT = "parsed_messages.json"

# Number of messages retrieved per question.
K = 6

# Chroma collection name.
COLLECTION = "whatsapp_messages"

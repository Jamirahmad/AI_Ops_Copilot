import os
from dotenv import load_dotenv

load_dotenv()

# Phase map for graders:
# - Phase 3: LLM provider/model configuration.
# - Phase 4: Embedding model configuration for RAG.
# - Phase 5/6/8: runtime constraints, memory/tool limits, and operational paths.

# OpenRouter settings (OpenAI-compatible API)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_EMBEDDING_MODEL = os.getenv("OPENROUTER_EMBEDDING_MODEL", "text-embedding-3-small")

MODEL_NAME = OPENROUTER_MODEL
EMBEDDING_MODEL_NAME = OPENROUTER_EMBEDDING_MODEL
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.2"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "3"))

# App-level defaults
DEFAULT_PROMPT_STRATEGY = os.getenv("DEFAULT_PROMPT_STRATEGY", "v3_rag_tools_cautious")
MAX_TOOL_CALLS = int(os.getenv("MAX_TOOL_CALLS", "2"))
MAX_MEMORY_TURNS = int(os.getenv("MAX_MEMORY_TURNS", "6"))

# Paths
DATA_DIR = os.getenv("DATA_DIR", "data")
RUNBOOKS_PATH = os.path.join(DATA_DIR, "runbooks.txt")
LOGS_SOURCE_PATH = os.path.join(DATA_DIR, "logs.txt")
KNOWLEDGE_ROOT = os.path.join(DATA_DIR, "knowledge")
KNOWLEDGE_BASE_DIR = os.path.join(DATA_DIR, "knowledge_base")
KNOWLEDGE_BASE_FAISS_DIR = os.path.join(KNOWLEDGE_BASE_DIR, "faiss_index")
RUNTIME_LOG_PATH = os.path.join(DATA_DIR, "agent_runs.jsonl")
ERROR_LOG_PATH = os.path.join(DATA_DIR, "errors.jsonl")
FEEDBACK_PATH = os.path.join(DATA_DIR, "feedback.jsonl")
MEMORY_PATH = os.path.join(DATA_DIR, "memory_store.json")

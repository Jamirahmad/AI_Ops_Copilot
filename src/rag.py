from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config import (
    EMBEDDING_MODEL_NAME,
    KNOWLEDGE_BASE_DIR,
    KNOWLEDGE_BASE_FAISS_DIR,
    KNOWLEDGE_ROOT,
    LOGS_SOURCE_PATH,
    OPENROUTER_API_KEY,
    OPENROUTER_BASE_URL,
    RUNBOOKS_PATH,
)

# Phase map for graders:
# - Phase 4: Knowledge ingestion, chunking, embeddings, semantic retrieval.
# - Phase 4 improvement: Hybrid retrieval (semantic + lexical fallback) over multi-file corpus.
# - Phase 8 improvement: Optional persisted FAISS load for deployment-readiness.


@dataclass
class RetrievedChunk:
    source: str
    content: str
    score: Optional[float]


@dataclass
class LocalChunk:
    source: str
    content: str


LOCAL_CHUNKS: List[LocalChunk] = []


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_\-]+", text.lower()))


def _load_file_text(path: Path) -> str:
    if path.suffix.lower() == ".jsonl":
        lines = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                lines.append(json.dumps(obj, ensure_ascii=False))
            except json.JSONDecodeError:
                lines.append(line)
        return "\n".join(lines)
    return path.read_text(encoding="utf-8")


def _gather_source_paths() -> List[Path]:
    paths: List[Path] = []
    for p in [Path(RUNBOOKS_PATH), Path(LOGS_SOURCE_PATH)]:
        if p.exists() and p.is_file():
            paths.append(p)

    knowledge_root = Path(KNOWLEDGE_ROOT)
    if knowledge_root.exists():
        for p in knowledge_root.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".txt", ".md", ".jsonl", ".pdf"}:
                paths.append(p)

    deduped = []
    seen = set()
    for p in paths:
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)
    return deduped


def _load_documents() -> list:
    docs = []
    for path in _gather_source_paths():
        try:
            if path.suffix.lower() in {".txt", ".md"}:
                loader = TextLoader(str(path), encoding="utf-8")
                docs.extend(loader.load())
            else:
                text = _load_file_text(path)
                if text.strip():
                    from langchain_core.documents import Document

                    docs.append(Document(page_content=text, metadata={"source": str(path)}))
        except Exception:
            continue
    return docs


def _split_documents(docs: list) -> list:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(docs)


def _build_local_chunks() -> List[LocalChunk]:
    docs = _load_documents()
    split_docs = _split_documents(docs)
    chunks: List[LocalChunk] = []
    for d in split_docs:
        text = d.page_content.strip()
        if not text:
            continue
        chunks.append(LocalChunk(source=d.metadata.get("source", "unknown"), content=text))
    return chunks


def _load_local_chunks_from_artifacts() -> List[LocalChunk]:
    chunks_file = Path(KNOWLEDGE_BASE_DIR) / "chunks.jsonl"
    if not chunks_file.exists():
        return []
    out: List[LocalChunk] = []
    try:
        for line in chunks_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            content = str(obj.get("content", "")).strip()
            if not content:
                continue
            out.append(LocalChunk(source=str(obj.get("source", "unknown")), content=content))
    except Exception:
        return []
    return out


def _embeddings_client() -> Optional[OpenAIEmbeddings]:
    if not OPENROUTER_API_KEY:
        return None
    return OpenAIEmbeddings(
        model=EMBEDDING_MODEL_NAME,
        openai_api_key=OPENROUTER_API_KEY,
        openai_api_base=OPENROUTER_BASE_URL,
    )


def build_vectorstore() -> Optional[FAISS]:
    global LOCAL_CHUNKS

    LOCAL_CHUNKS = _load_local_chunks_from_artifacts()
    if not LOCAL_CHUNKS:
        LOCAL_CHUNKS = _build_local_chunks()

    embeddings = _embeddings_client()
    if embeddings is not None:
        faiss_dir = Path(KNOWLEDGE_BASE_FAISS_DIR)
        if faiss_dir.exists() and (faiss_dir / "index.faiss").exists():
            try:
                return FAISS.load_local(
                    str(faiss_dir),
                    embeddings,
                    allow_dangerous_deserialization=True,
                )
            except Exception:
                pass

    docs = _load_documents()
    split_docs = _split_documents(docs)
    LOCAL_CHUNKS = [
        LocalChunk(source=d.metadata.get("source", "unknown"), content=d.page_content)
        for d in split_docs
        if d.page_content.strip()
    ]

    if not split_docs or embeddings is None:
        return None

    return FAISS.from_documents(split_docs, embeddings)


def _lexical_retrieve(query: str, k: int = 3) -> List[RetrievedChunk]:
    global LOCAL_CHUNKS
    if not LOCAL_CHUNKS:
        LOCAL_CHUNKS = _load_local_chunks_from_artifacts() or _build_local_chunks()
    if not LOCAL_CHUNKS:
        return []

    q_tokens = _tokenize(query)
    scored = []
    for chunk in LOCAL_CHUNKS:
        c_tokens = _tokenize(chunk.content)
        overlap = len(q_tokens.intersection(c_tokens))
        if overlap == 0:
            continue
        score = 1.0 / (overlap + 1.0)
        scored.append((score, chunk))

    scored.sort(key=lambda x: x[0])
    top = scored[:k]
    return [
        RetrievedChunk(source=item.source, content=item.content, score=float(score))
        for score, item in top
    ]


def retrieve_context(vectorstore: Optional[FAISS], query: str, k: int = 4) -> List[RetrievedChunk]:
    results: List[RetrievedChunk] = []

    if vectorstore is not None:
        try:
            pairs = vectorstore.similarity_search_with_score(query, k=k)
            for doc, score in pairs:
                results.append(
                    RetrievedChunk(
                        source=doc.metadata.get("source", "unknown"),
                        content=doc.page_content,
                        score=float(score) if score is not None else None,
                    )
                )
        except Exception:
            pass

    lexical = _lexical_retrieve(query, k=k)

    merged = {}
    for chunk in results + lexical:
        key = f"{chunk.source}::{chunk.content[:80]}"
        if key not in merged:
            merged[key] = chunk
        else:
            prev = merged[key]
            prev_score = prev.score if prev.score is not None else 9999.0
            new_score = chunk.score if chunk.score is not None else 9999.0
            if new_score < prev_score:
                merged[key] = chunk

    out = list(merged.values())
    out.sort(key=lambda c: (c.score if c.score is not None else 9999.0))
    return out[:k]


def stringify_context(chunks: List[RetrievedChunk]) -> str:
    if not chunks:
        return "No retrieved context available."

    lines = []
    for i, c in enumerate(chunks, start=1):
        score_text = "n/a" if c.score is None else f"{c.score:.4f}"
        lines.append(f"[{i}] source={c.source} score={score_text}")
        lines.append(c.content)
    return "\n".join(lines)


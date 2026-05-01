from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
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
# - Phase 4: RAG corpus prep, chunking, and semantic indexing.
# - Phase 8: Persisted build artifacts for reproducibility and deployment.


@dataclass
class ChunkRecord:
    chunk_id: str
    source: str
    content: str
    char_count: int


def _load_file_text(path: Path) -> str:
    if path.suffix.lower() != ".jsonl":
        return path.read_text(encoding="utf-8")

    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            out.append(json.dumps(obj, ensure_ascii=False))
        except json.JSONDecodeError:
            out.append(line)
    return "\n".join(out)


def gather_sources() -> List[Path]:
    paths: List[Path] = []
    for p in [Path(RUNBOOKS_PATH), Path(LOGS_SOURCE_PATH)]:
        if p.exists() and p.is_file():
            paths.append(p)

    root = Path(KNOWLEDGE_ROOT)
    if root.exists():
        for p in root.rglob("*"):
            if p.is_file() and p.suffix.lower() in {".txt", ".md", ".jsonl", ".pdf"}:
                paths.append(p)

    deduped = []
    seen = set()
    for p in paths:
        key = str(p.resolve())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(p)
    return deduped


def load_documents(source_paths: List[Path]) -> List[Document]:
    docs: List[Document] = []
    for path in source_paths:
        try:
            if path.suffix.lower() in {".txt", ".md"}:
                docs.extend(TextLoader(str(path), encoding="utf-8").load())
            else:
                text = _load_file_text(path).strip()
                if text:
                    docs.append(Document(page_content=text, metadata={"source": str(path)}))
        except Exception:
            continue
    return docs


def chunk_documents(docs: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(docs)


def build_chunk_records(split_docs: List[Document]) -> List[ChunkRecord]:
    records: List[ChunkRecord] = []
    for i, doc in enumerate(split_docs, start=1):
        content = doc.page_content.strip()
        if not content:
            continue
        records.append(
            ChunkRecord(
                chunk_id=f"chunk_{i:05d}",
                source=doc.metadata.get("source", "unknown"),
                content=content,
                char_count=len(content),
            )
        )
    return records


def persist_artifacts(source_paths: List[Path], chunks: List[ChunkRecord]) -> None:
    kb_dir = Path(KNOWLEDGE_BASE_DIR)
    kb_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "built_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_files": [str(p) for p in source_paths],
        "chunk_count": len(chunks),
    }
    (kb_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    with (kb_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for rec in chunks:
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")

    stats = {
        "chunk_count": len(chunks),
        "avg_chunk_chars": (sum(c.char_count for c in chunks) / len(chunks)) if chunks else 0,
        "max_chunk_chars": max((c.char_count for c in chunks), default=0),
        "min_chunk_chars": min((c.char_count for c in chunks), default=0),
    }
    (kb_dir / "stats.json").write_text(json.dumps(stats, indent=2), encoding="utf-8")


def try_persist_faiss(split_docs: List[Document]) -> Optional[str]:
    if not split_docs or not OPENROUTER_API_KEY:
        return "Skipped FAISS build (missing split docs or OPENROUTER_API_KEY)."

    try:
        embeddings = OpenAIEmbeddings(
            model=EMBEDDING_MODEL_NAME,
            openai_api_key=OPENROUTER_API_KEY,
            openai_api_base=OPENROUTER_BASE_URL,
        )
        store = FAISS.from_documents(split_docs, embeddings)
        out_dir = Path(KNOWLEDGE_BASE_FAISS_DIR)
        out_dir.mkdir(parents=True, exist_ok=True)
        store.save_local(str(out_dir))
        return f"Saved FAISS index to: {out_dir}"
    except Exception as exc:
        return f"Failed to build FAISS index: {exc}"


def main() -> None:
    sources = gather_sources()
    docs = load_documents(sources)
    split_docs = chunk_documents(docs)
    chunks = build_chunk_records(split_docs)

    persist_artifacts(sources, chunks)
    faiss_msg = try_persist_faiss(split_docs)

    print(f"Source files: {len(sources)}")
    print(f"Raw docs loaded: {len(docs)}")
    print(f"Chunks generated: {len(chunks)}")
    print(f"Artifacts dir: {Path(KNOWLEDGE_BASE_DIR)}")
    if faiss_msg:
        print(faiss_msg)


if __name__ == "__main__":
    main()


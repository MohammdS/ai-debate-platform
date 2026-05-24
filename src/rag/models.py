from dataclasses import dataclass, field


@dataclass
class RAGConfig:
    """All tuneable parameters for the RAG pipeline."""

    knowledge_dir: str = "knowledge"
    vector_db_path: str = ".chroma_db"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    collection_name: str = "debate_knowledge"
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k: int = 3


@dataclass
class RetrievedChunk:
    """A single passage returned by the retriever."""

    content: str
    source: str
    score: float = 0.0
    metadata: dict = field(default_factory=dict)

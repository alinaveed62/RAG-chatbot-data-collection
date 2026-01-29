"""JSONL export for RAG-ready chunks."""

import json
from pathlib import Path
from typing import List, Iterator, Optional
from datetime import datetime

from models.document import Document
from models.chunk import Chunk
from utils.logging_config import get_logger

logger = get_logger()


class JSONLExporter:
    """Exports documents and chunks to JSONL format."""

    def __init__(self, output_dir: Path):
        """
        Initialize exporter.

        Args:
            output_dir: Directory for output files
        """
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export_documents(
        self,
        documents: List[Document],
        filename: str = "documents.jsonl",
    ) -> Path:
        """
        Export documents to JSONL file.

        Args:
            documents: List of documents to export
            filename: Output filename

        Returns:
            Path to created file
        """
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            for doc in documents:
                line = json.dumps(doc.to_dict(), ensure_ascii=False)
                f.write(line + "\n")

        logger.info(f"Exported {len(documents)} documents to {filepath}")
        return filepath

    def export_chunks(
        self,
        chunks: List[Chunk],
        filename: str = "handbook_chunks.jsonl",
    ) -> Path:
        """
        Export chunks to JSONL file.

        Args:
            chunks: List of chunks to export
            filename: Output filename

        Returns:
            Path to created file
        """
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            for chunk in chunks:
                line = json.dumps(chunk.to_dict(), ensure_ascii=False)
                f.write(line + "\n")

        logger.info(f"Exported {len(chunks)} chunks to {filepath}")
        return filepath

    def export_embedding_format(
        self,
        chunks: List[Chunk],
        filename: str = "chunks_for_embedding.jsonl",
    ) -> Path:
        """
        Export chunks in format optimized for embedding.

        Args:
            chunks: List of chunks
            filename: Output filename

        Returns:
            Path to created file
        """
        filepath = self.output_dir / filename

        with open(filepath, "w", encoding="utf-8") as f:
            for chunk in chunks:
                line = json.dumps(chunk.to_embedding_format(), ensure_ascii=False)
                f.write(line + "\n")

        logger.info(f"Exported {len(chunks)} chunks for embedding to {filepath}")
        return filepath

    def create_index(
        self,
        chunks: List[Chunk],
        filename: str = "chunk_index.json",
    ) -> Path:
        """
        Create a quick lookup index for chunks.

        Args:
            chunks: List of chunks
            filename: Output filename

        Returns:
            Path to created file
        """
        filepath = self.output_dir / filename

        index = {
            "created_at": datetime.utcnow().isoformat(),
            "total_chunks": len(chunks),
            "chunks_by_section": {},
            "chunks_by_document": {},
        }

        for chunk in chunks:
            # Index by section
            section = chunk.metadata.section or "Unknown"
            if section not in index["chunks_by_section"]:
                index["chunks_by_section"][section] = []
            index["chunks_by_section"][section].append(chunk.id)

            # Index by document
            doc_id = chunk.metadata.document_id
            if doc_id not in index["chunks_by_document"]:
                index["chunks_by_document"][doc_id] = {
                    "title": chunk.metadata.document_title,
                    "chunks": [],
                }
            index["chunks_by_document"][doc_id]["chunks"].append(chunk.id)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=2, ensure_ascii=False)

        logger.info(f"Created chunk index at {filepath}")
        return filepath

    @staticmethod
    def load_chunks(filepath: Path) -> Iterator[Chunk]:
        """
        Load chunks from JSONL file.

        Args:
            filepath: Path to JSONL file

        Yields:
            Chunk objects
        """
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                yield Chunk(**data)

    @staticmethod
    def load_documents(filepath: Path) -> Iterator[Document]:
        """
        Load documents from JSONL file.

        Args:
            filepath: Path to JSONL file

        Yields:
            Document objects
        """
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                yield Document(**data)

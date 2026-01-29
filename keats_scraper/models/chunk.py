"""Chunk data model for RAG-ready text segments."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
import hashlib


class ChunkMetadata(BaseModel):
    """Metadata for a text chunk."""

    source_url: str = Field(..., description="Original document URL")
    document_id: str = Field(..., description="Parent document ID")
    document_title: str = Field(..., description="Parent document title")
    section: str = Field(default="", description="Handbook section")
    subsection: Optional[str] = Field(default=None, description="Subsection if applicable")
    heading_path: List[str] = Field(
        default_factory=list, description="Hierarchy of headings at chunk position"
    )
    chunk_index: int = Field(..., description="Index of this chunk in document")
    total_chunks_in_doc: int = Field(..., description="Total chunks in parent document")
    char_count: int = Field(default=0, description="Character count")
    word_count: int = Field(default=0, description="Word count")
    extraction_date: datetime = Field(
        default_factory=datetime.utcnow, description="When extracted"
    )
    content_hash: str = Field(default="", description="Hash for deduplication")


class Chunk(BaseModel):
    """A text chunk ready for RAG embedding."""

    id: str = Field(..., description="Unique chunk identifier")
    text: str = Field(..., description="Chunk text content")
    metadata: ChunkMetadata

    @classmethod
    def create(
        cls,
        text: str,
        document_id: str,
        document_title: str,
        source_url: str,
        chunk_index: int,
        total_chunks: int,
        section: str = "",
        heading_path: Optional[List[str]] = None,
        **metadata_kwargs,
    ) -> "Chunk":
        """Factory method to create a chunk with auto-generated ID and hash."""
        # Generate content hash for deduplication
        content_hash = hashlib.md5(text.encode()).hexdigest()

        # Generate unique chunk ID
        chunk_id = f"{document_id}_chunk_{chunk_index}"

        metadata = ChunkMetadata(
            source_url=source_url,
            document_id=document_id,
            document_title=document_title,
            section=section,
            heading_path=heading_path or [],
            chunk_index=chunk_index,
            total_chunks_in_doc=total_chunks,
            char_count=len(text),
            word_count=len(text.split()),
            content_hash=content_hash,
            **metadata_kwargs,
        )

        return cls(id=chunk_id, text=text, metadata=metadata)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSONL export."""
        return {
            "id": self.id,
            "text": self.text,
            "metadata": self.metadata.model_dump(mode="json"),
        }

    def to_embedding_format(self) -> dict:
        """Format for embedding pipeline input."""
        return {
            "id": self.id,
            "text": self.text,
            "source": self.metadata.source_url,
            "title": self.metadata.document_title,
            "section": self.metadata.section,
        }

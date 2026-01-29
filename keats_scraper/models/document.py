"""Document data model for extracted content."""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import hashlib


class DocumentMetadata(BaseModel):
    """Metadata for an extracted document."""

    source_url: str = Field(..., description="Original URL of the document")
    title: str = Field(..., description="Document title")
    section: str = Field(default="", description="Handbook section name")
    subsection: Optional[str] = Field(default=None, description="Subsection if applicable")
    content_type: str = Field(..., description="Type: page, pdf, folder, etc.")
    last_modified: Optional[datetime] = Field(default=None, description="Last modified date")
    extraction_date: datetime = Field(
        default_factory=datetime.utcnow, description="When content was extracted"
    )
    word_count: int = Field(default=0, description="Word count of content")
    parent_id: Optional[str] = Field(default=None, description="Parent document ID if nested")


class Document(BaseModel):
    """Represents an extracted document from KEATS."""

    id: str = Field(..., description="Unique document identifier")
    content: str = Field(..., description="Extracted text content")
    raw_html: Optional[str] = Field(default=None, description="Original HTML if applicable")
    metadata: DocumentMetadata

    @classmethod
    def create(
        cls,
        source_url: str,
        title: str,
        content: str,
        content_type: str,
        section: str = "",
        raw_html: Optional[str] = None,
        **metadata_kwargs,
    ) -> "Document":
        """Factory method to create a document with auto-generated ID."""
        # Generate ID from URL hash
        doc_id = hashlib.md5(source_url.encode()).hexdigest()[:12]

        metadata = DocumentMetadata(
            source_url=source_url,
            title=title,
            section=section,
            content_type=content_type,
            word_count=len(content.split()),
            **metadata_kwargs,
        )

        return cls(
            id=doc_id,
            content=content,
            raw_html=raw_html,
            metadata=metadata,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata.model_dump(mode="json"),
        }


class ResourceInfo(BaseModel):
    """Information about a KEATS resource to be scraped."""

    url: str = Field(..., description="Resource URL")
    title: str = Field(..., description="Resource title")
    resource_type: str = Field(..., description="Moodle resource type")
    section: str = Field(default="", description="Section name")
    section_index: int = Field(default=0, description="Section order index")
    processed: bool = Field(default=False, description="Whether already processed")

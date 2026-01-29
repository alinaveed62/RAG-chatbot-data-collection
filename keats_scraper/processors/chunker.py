"""Document chunking for RAG pipeline."""

import re
from typing import List, Optional, Tuple

from models.document import Document
from models.chunk import Chunk
from config import ChunkConfig
from utils.logging_config import get_logger

logger = get_logger()


class Chunker:
    """Splits documents into chunks suitable for RAG embedding."""

    def __init__(self, config: Optional[ChunkConfig] = None):
        """
        Initialize chunker.

        Args:
            config: Chunking configuration
        """
        self.config = config or ChunkConfig()
        self._tokenizer = None

    def _get_tokenizer(self):
        """Lazy load tiktoken tokenizer."""
        if self._tokenizer is None:
            try:
                import tiktoken
                self._tokenizer = tiktoken.get_encoding("cl100k_base")
            except ImportError:
                logger.warning("tiktoken not installed, using word-based chunking")
                self._tokenizer = "word"
        return self._tokenizer

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        tokenizer = self._get_tokenizer()
        if tokenizer == "word":
            return len(text.split())
        return len(tokenizer.encode(text))

    def _extract_heading_at_position(self, text: str, position: int) -> List[str]:
        """
        Extract heading hierarchy at a given position in text.

        Args:
            text: Full document text
            position: Character position

        Returns:
            List of headings leading to this position
        """
        # Find all headings before this position
        heading_pattern = r"^(#{1,6})\s+(.+)$"
        headings = []

        for match in re.finditer(heading_pattern, text[:position], re.MULTILINE):
            level = len(match.group(1))
            title = match.group(2).strip()
            headings.append((level, title))

        # Build hierarchy (keep only most recent at each level)
        hierarchy = {}
        for level, title in headings:
            hierarchy[level] = title
            # Remove lower-level headings when we see a higher-level one
            for l in list(hierarchy.keys()):
                if l > level:
                    del hierarchy[l]

        return [hierarchy[l] for l in sorted(hierarchy.keys())]

    def _split_by_separators(self, text: str) -> List[Tuple[str, int]]:
        """
        Split text by configured separators.

        Returns list of (chunk_text, start_position) tuples.
        """
        chunks = []
        current_chunk = []
        current_start = 0
        current_length = 0

        # Split into paragraphs first
        paragraphs = re.split(r"\n\n+", text)

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_tokens = self._count_tokens(para)

            # If this paragraph alone exceeds chunk size, split it further
            if para_tokens > self.config.chunk_size:
                # Save current chunk if any
                if current_chunk:
                    chunks.append(("\n\n".join(current_chunk), current_start))
                    current_chunk = []
                    current_length = 0

                # Split long paragraph by sentences
                # Note: para is already stripped, so sentence split won't produce empty strings
                sentences = re.split(r"(?<=[.!?])\s+", para)
                for sentence in sentences:
                    sentence = sentence.strip()
                    sent_tokens = self._count_tokens(sentence)

                    if current_length + sent_tokens > self.config.chunk_size:
                        if current_chunk:
                            chunks.append(("\n\n".join(current_chunk), current_start))
                        current_chunk = [sentence]
                        current_start = text.find(sentence, current_start)
                        current_length = sent_tokens
                    else:
                        current_chunk.append(sentence)
                        current_length += sent_tokens

            elif current_length + para_tokens > self.config.chunk_size:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(("\n\n".join(current_chunk), current_start))
                current_chunk = [para]
                current_start = text.find(para, current_start)
                current_length = para_tokens
            else:
                # Add to current chunk
                if not current_chunk:
                    current_start = text.find(para, current_start)
                current_chunk.append(para)
                current_length += para_tokens

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(("\n\n".join(current_chunk), current_start))

        return chunks

    def _add_overlap(
        self, chunks: List[Tuple[str, int]], full_text: str
    ) -> List[Tuple[str, int]]:
        """Add overlap between chunks."""
        if not chunks or self.config.chunk_overlap == 0:
            return chunks

        result = []
        for i, (chunk_text, start_pos) in enumerate(chunks):
            if i > 0:
                # Add overlap from previous chunk
                prev_text = chunks[i - 1][0]
                overlap_tokens = self.config.chunk_overlap

                # Get last N tokens worth of text from previous chunk
                prev_words = prev_text.split()
                overlap_words = prev_words[-overlap_tokens:] if len(prev_words) > overlap_tokens else prev_words
                overlap_text = " ".join(overlap_words)

                chunk_text = f"...{overlap_text}\n\n{chunk_text}"

            result.append((chunk_text, start_pos))

        return result

    def chunk_document(self, document: Document) -> List[Chunk]:
        """
        Split a document into chunks.

        Args:
            document: Document to chunk

        Returns:
            List of Chunk objects
        """
        text = document.content

        if not text or not text.strip():
            logger.warning(f"Empty document: {document.id}")
            return []

        # Split into chunks
        raw_chunks = self._split_by_separators(text)

        # Add overlap
        chunks_with_overlap = self._add_overlap(raw_chunks, text)

        # Create Chunk objects
        chunks = []
        total_chunks = len(chunks_with_overlap)

        for i, (chunk_text, start_pos) in enumerate(chunks_with_overlap):
            # Extract heading hierarchy at this position
            heading_path = self._extract_heading_at_position(text, start_pos)

            # Prepend heading context if configured
            if self.config.preserve_headings and heading_path:
                heading_context = " > ".join(heading_path)
                chunk_text = f"[Context: {heading_context}]\n\n{chunk_text}"

            chunk = Chunk.create(
                text=chunk_text,
                document_id=document.id,
                document_title=document.metadata.title,
                source_url=document.metadata.source_url,
                chunk_index=i,
                total_chunks=total_chunks,
                section=document.metadata.section,
                heading_path=heading_path,
            )

            chunks.append(chunk)

        logger.info(f"Created {len(chunks)} chunks from document '{document.metadata.title}'")
        return chunks

    def chunk_documents(self, documents: List[Document]) -> List[Chunk]:
        """
        Chunk multiple documents.

        Args:
            documents: List of documents to chunk

        Returns:
            Combined list of all chunks
        """
        all_chunks = []

        for doc in documents:
            chunks = self.chunk_document(doc)
            all_chunks.extend(chunks)

        logger.info(f"Created {len(all_chunks)} total chunks from {len(documents)} documents")
        return all_chunks

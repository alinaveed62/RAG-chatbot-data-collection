"""PDF download and text extraction handler."""

import tempfile
from pathlib import Path
from typing import Optional
import requests

from ..models.document import Document
from ..config import ScraperConfig
from ..utils.logging_config import get_logger
from ..utils.exceptions import ContentExtractionError
from .rate_limiter import RateLimiter

logger = get_logger()


class PDFHandler:
    """Handles PDF downloading and text extraction."""

    def __init__(
        self,
        session: requests.Session,
        rate_limiter: RateLimiter,
        config: ScraperConfig,
    ):
        """
        Initialize PDF handler.

        Args:
            session: Authenticated requests session
            rate_limiter: Rate limiter instance
            config: Scraper configuration
        """
        self.session = session
        self.rate_limiter = rate_limiter
        self.config = config
        self.pdf_dir = config.raw_dir / "pdf"

    def download_pdf(self, url: str, filename: Optional[str] = None) -> Path:
        """
        Download a PDF file.

        Args:
            url: PDF URL
            filename: Optional filename (auto-generated if not provided)

        Returns:
            Path to downloaded PDF

        Raises:
            ContentExtractionError: If download fails
        """
        self.rate_limiter.wait()

        try:
            response = self.session.get(url, stream=True, timeout=60)
            response.raise_for_status()

            # Determine filename
            if not filename:
                # Try to get from Content-Disposition header
                cd = response.headers.get("Content-Disposition", "")
                if "filename=" in cd:
                    filename = cd.split("filename=")[-1].strip('"\'')
                else:
                    # Use URL path
                    filename = url.split("/")[-1].split("?")[0]

                if not filename.endswith(".pdf"):
                    filename += ".pdf"

            filepath = self.pdf_dir / filename

            # Download in chunks
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"Downloaded PDF: {filepath}")
            return filepath

        except requests.RequestException as e:
            logger.error(f"Failed to download PDF from {url}: {e}")
            raise ContentExtractionError(f"PDF download failed: {e}")

    def extract_text(self, pdf_path: Path) -> str:
        """
        Extract text from a PDF file.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Extracted text content
        """
        try:
            import pdfplumber

            text_parts = []

            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(f"[Page {i + 1}]\n{page_text}")

            text = "\n\n".join(text_parts)
            logger.info(f"Extracted {len(text)} chars from {pdf_path.name}")
            return text

        except ImportError:
            logger.error("pdfplumber not installed. Run: pip install pdfplumber")
            raise ContentExtractionError("pdfplumber not available")
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
            raise ContentExtractionError(f"PDF text extraction failed: {e}")

    def process_pdf(
        self,
        url: str,
        title: str,
        section: str = "",
    ) -> Optional[Document]:
        """
        Download and extract text from a PDF.

        Args:
            url: PDF URL
            title: Document title
            section: Handbook section

        Returns:
            Document or None if processing fails
        """
        logger.info(f"Processing PDF: {url}")

        try:
            # Download
            pdf_path = self.download_pdf(url)

            # Extract text
            content = self.extract_text(pdf_path)

            if not content.strip():
                logger.warning(f"No text extracted from PDF: {url}")
                return None

            # Create document
            document = Document.create(
                source_url=url,
                title=title,
                content=content,
                content_type="pdf",
                section=section,
            )

            return document

        except ContentExtractionError:
            return None
        except Exception as e:
            logger.error(f"Failed to process PDF {url}: {e}")
            return None

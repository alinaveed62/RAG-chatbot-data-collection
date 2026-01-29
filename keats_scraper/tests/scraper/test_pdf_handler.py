"""Tests for PDFHandler."""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open
from pathlib import Path
import requests

from scraper.pdf_handler import PDFHandler
from scraper.rate_limiter import RateLimiter
from config import ScraperConfig
from models.document import Document
from utils.exceptions import ContentExtractionError


class TestPDFHandlerInit:
    """Tests for PDFHandler initialization."""

    @pytest.fixture
    def mock_config(self, tmp_path):
        """Create mock config with temp directories."""
        config = Mock(spec=ScraperConfig)
        config.raw_dir = tmp_path / "raw"
        config.raw_dir.mkdir(parents=True)
        return config

    def test_init_sets_session(self, mock_config):
        """Test session is set correctly."""
        mock_session = Mock(spec=requests.Session)
        mock_limiter = Mock(spec=RateLimiter)

        handler = PDFHandler(mock_session, mock_limiter, mock_config)
        assert handler.session is mock_session

    def test_init_sets_rate_limiter(self, mock_config):
        """Test rate_limiter is set correctly."""
        mock_session = Mock(spec=requests.Session)
        mock_limiter = Mock(spec=RateLimiter)

        handler = PDFHandler(mock_session, mock_limiter, mock_config)
        assert handler.rate_limiter is mock_limiter

    def test_init_sets_config(self, mock_config):
        """Test config is set correctly."""
        mock_session = Mock(spec=requests.Session)
        mock_limiter = Mock(spec=RateLimiter)

        handler = PDFHandler(mock_session, mock_limiter, mock_config)
        assert handler.config is mock_config

    def test_init_sets_pdf_dir(self, mock_config):
        """Test pdf_dir is set from config.raw_dir."""
        mock_session = Mock(spec=requests.Session)
        mock_limiter = Mock(spec=RateLimiter)

        handler = PDFHandler(mock_session, mock_limiter, mock_config)
        assert handler.pdf_dir == mock_config.raw_dir / "pdf"


class TestDownloadPDF:
    """Tests for download_pdf method."""

    @pytest.fixture
    def handler(self, tmp_path):
        """Create handler with mocked dependencies."""
        mock_session = Mock(spec=requests.Session)
        mock_limiter = Mock(spec=RateLimiter)
        mock_config = Mock(spec=ScraperConfig)
        mock_config.raw_dir = tmp_path / "raw"
        mock_config.raw_dir.mkdir(parents=True)

        handler = PDFHandler(mock_session, mock_limiter, mock_config)
        # Create pdf directory
        handler.pdf_dir.mkdir(parents=True, exist_ok=True)
        return handler

    def test_download_calls_rate_limiter(self, handler):
        """Test rate limiter wait is called."""
        mock_response = Mock()
        mock_response.headers = {"Content-Disposition": 'filename="test.pdf"'}
        mock_response.iter_content.return_value = [b"fake pdf content"]
        handler.session.get.return_value = mock_response

        handler.download_pdf("https://example.com/doc.pdf")
        handler.rate_limiter.wait.assert_called_once()

    def test_download_returns_path(self, handler):
        """Test download returns Path object."""
        mock_response = Mock()
        mock_response.headers = {"Content-Disposition": 'filename="test.pdf"'}
        mock_response.iter_content.return_value = [b"fake pdf content"]
        handler.session.get.return_value = mock_response

        result = handler.download_pdf("https://example.com/doc.pdf")
        assert isinstance(result, Path)

    def test_download_creates_file(self, handler):
        """Test file is created."""
        mock_response = Mock()
        mock_response.headers = {"Content-Disposition": 'filename="test.pdf"'}
        mock_response.iter_content.return_value = [b"fake pdf content"]
        handler.session.get.return_value = mock_response

        filepath = handler.download_pdf("https://example.com/doc.pdf")
        assert filepath.exists()

    def test_download_writes_content(self, handler):
        """Test content is written to file."""
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2", b"chunk3"]
        handler.session.get.return_value = mock_response

        filepath = handler.download_pdf("https://example.com/doc.pdf")
        content = filepath.read_bytes()
        assert content == b"chunk1chunk2chunk3"

    def test_download_uses_provided_filename(self, handler):
        """Test custom filename is used."""
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.iter_content.return_value = [b"content"]
        handler.session.get.return_value = mock_response

        filepath = handler.download_pdf("https://example.com/doc.pdf", filename="custom.pdf")
        assert filepath.name == "custom.pdf"

    def test_download_extracts_filename_from_content_disposition(self, handler):
        """Test filename extracted from Content-Disposition header."""
        mock_response = Mock()
        mock_response.headers = {"Content-Disposition": 'attachment; filename="handbook.pdf"'}
        mock_response.iter_content.return_value = [b"content"]
        handler.session.get.return_value = mock_response

        filepath = handler.download_pdf("https://example.com/download?id=123")
        assert filepath.name == "handbook.pdf"

    def test_download_extracts_filename_from_content_disposition_single_quotes(self, handler):
        """Test filename extracted with single quotes."""
        mock_response = Mock()
        mock_response.headers = {"Content-Disposition": "attachment; filename='guide.pdf'"}
        mock_response.iter_content.return_value = [b"content"]
        handler.session.get.return_value = mock_response

        filepath = handler.download_pdf("https://example.com/download")
        assert "guide" in filepath.name

    def test_download_uses_url_path_as_fallback(self, handler):
        """Test URL path used when no Content-Disposition."""
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.iter_content.return_value = [b"content"]
        handler.session.get.return_value = mock_response

        filepath = handler.download_pdf("https://example.com/documents/report.pdf")
        assert filepath.name == "report.pdf"

    def test_download_adds_pdf_extension(self, handler):
        """Test .pdf extension added if missing."""
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.iter_content.return_value = [b"content"]
        handler.session.get.return_value = mock_response

        filepath = handler.download_pdf("https://example.com/documents/report")
        assert filepath.name == "report.pdf"

    def test_download_strips_query_params(self, handler):
        """Test query parameters stripped from filename."""
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.iter_content.return_value = [b"content"]
        handler.session.get.return_value = mock_response

        filepath = handler.download_pdf("https://example.com/doc.pdf?token=abc123")
        assert "?" not in filepath.name
        assert filepath.name == "doc.pdf"

    def test_download_uses_stream_mode(self, handler):
        """Test download uses stream=True."""
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.iter_content.return_value = [b"content"]
        handler.session.get.return_value = mock_response

        handler.download_pdf("https://example.com/doc.pdf")

        handler.session.get.assert_called_once()
        call_kwargs = handler.session.get.call_args[1]
        assert call_kwargs["stream"] is True

    def test_download_uses_60_second_timeout(self, handler):
        """Test download uses 60 second timeout."""
        mock_response = Mock()
        mock_response.headers = {}
        mock_response.iter_content.return_value = [b"content"]
        handler.session.get.return_value = mock_response

        handler.download_pdf("https://example.com/doc.pdf")

        call_kwargs = handler.session.get.call_args[1]
        assert call_kwargs["timeout"] == 60

    def test_download_raises_on_http_error(self, handler):
        """Test raises for HTTP errors."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")
        handler.session.get.return_value = mock_response

        with pytest.raises(ContentExtractionError) as exc_info:
            handler.download_pdf("https://example.com/notfound.pdf")

        assert "PDF download failed" in str(exc_info.value)

    def test_download_raises_on_connection_error(self, handler):
        """Test raises for connection errors."""
        handler.session.get.side_effect = requests.ConnectionError("Connection refused")

        with pytest.raises(ContentExtractionError):
            handler.download_pdf("https://example.com/doc.pdf")


class TestExtractText:
    """Tests for extract_text method."""

    @pytest.fixture
    def handler(self, tmp_path):
        """Create handler with mocked dependencies."""
        mock_session = Mock(spec=requests.Session)
        mock_limiter = Mock(spec=RateLimiter)
        mock_config = Mock(spec=ScraperConfig)
        mock_config.raw_dir = tmp_path / "raw"
        mock_config.raw_dir.mkdir(parents=True)

        handler = PDFHandler(mock_session, mock_limiter, mock_config)
        handler.pdf_dir.mkdir(parents=True, exist_ok=True)
        return handler

    def test_extract_text_success(self, handler, tmp_path):
        """Test successful text extraction."""
        pdf_path = tmp_path / "test.pdf"

        # Mock pdfplumber
        mock_page = Mock()
        mock_page.extract_text.return_value = "Page content here"

        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = handler.extract_text(pdf_path)

        assert "Page content here" in result

    def test_extract_text_multiple_pages(self, handler, tmp_path):
        """Test extraction from multiple pages."""
        pdf_path = tmp_path / "test.pdf"

        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "First page"
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = "Second page"
        mock_page3 = Mock()
        mock_page3.extract_text.return_value = "Third page"

        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = handler.extract_text(pdf_path)

        assert "[Page 1]" in result
        assert "[Page 2]" in result
        assert "[Page 3]" in result
        assert "First page" in result
        assert "Second page" in result
        assert "Third page" in result

    def test_extract_text_skips_empty_pages(self, handler, tmp_path):
        """Test empty pages are skipped."""
        pdf_path = tmp_path / "test.pdf"

        mock_page1 = Mock()
        mock_page1.extract_text.return_value = "Has content"
        mock_page2 = Mock()
        mock_page2.extract_text.return_value = None
        mock_page3 = Mock()
        mock_page3.extract_text.return_value = ""

        mock_pdf = Mock()
        mock_pdf.pages = [mock_page1, mock_page2, mock_page3]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = handler.extract_text(pdf_path)

        assert "[Page 1]" in result
        assert "Has content" in result
        # Page 2 and 3 should not have markers since they're empty
        assert "[Page 2]" not in result
        assert "[Page 3]" not in result

    def test_extract_text_returns_string(self, handler, tmp_path):
        """Test extract_text returns string."""
        pdf_path = tmp_path / "test.pdf"

        mock_page = Mock()
        mock_page.extract_text.return_value = "Content"

        mock_pdf = Mock()
        mock_pdf.pages = [mock_page]
        mock_pdf.__enter__ = Mock(return_value=mock_pdf)
        mock_pdf.__exit__ = Mock(return_value=False)

        with patch("pdfplumber.open", return_value=mock_pdf):
            result = handler.extract_text(pdf_path)

        assert isinstance(result, str)

    def test_extract_text_import_error(self, handler, tmp_path):
        """Test raises when pdfplumber not installed."""
        pdf_path = tmp_path / "test.pdf"

        with patch.dict("sys.modules", {"pdfplumber": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module")):
                with pytest.raises(ContentExtractionError) as exc_info:
                    handler.extract_text(pdf_path)

                assert "pdfplumber not available" in str(exc_info.value)

    def test_extract_text_pdf_error(self, handler, tmp_path):
        """Test raises for PDF processing errors."""
        pdf_path = tmp_path / "test.pdf"

        with patch("pdfplumber.open", side_effect=Exception("Corrupt PDF")):
            with pytest.raises(ContentExtractionError) as exc_info:
                handler.extract_text(pdf_path)

            assert "PDF text extraction failed" in str(exc_info.value)


class TestProcessPDF:
    """Tests for process_pdf method."""

    @pytest.fixture
    def handler(self, tmp_path):
        """Create handler with mocked dependencies."""
        mock_session = Mock(spec=requests.Session)
        mock_limiter = Mock(spec=RateLimiter)
        mock_config = Mock(spec=ScraperConfig)
        mock_config.raw_dir = tmp_path / "raw"
        mock_config.raw_dir.mkdir(parents=True)

        handler = PDFHandler(mock_session, mock_limiter, mock_config)
        handler.pdf_dir.mkdir(parents=True, exist_ok=True)
        return handler

    def test_process_returns_document(self, handler, tmp_path):
        """Test successful processing returns Document."""
        pdf_path = tmp_path / "test.pdf"

        # Mock download
        with patch.object(handler, "download_pdf", return_value=pdf_path):
            # Mock extraction
            with patch.object(handler, "extract_text", return_value="Extracted content"):
                result = handler.process_pdf(
                    "https://example.com/doc.pdf",
                    title="Test Document",
                    section="Test Section",
                )

        assert isinstance(result, Document)
        assert result.metadata.title == "Test Document"
        assert result.metadata.section == "Test Section"
        assert result.content == "Extracted content"
        assert result.metadata.content_type == "pdf"

    def test_process_sets_source_url(self, handler, tmp_path):
        """Test source_url is set correctly."""
        pdf_path = tmp_path / "test.pdf"

        with patch.object(handler, "download_pdf", return_value=pdf_path):
            with patch.object(handler, "extract_text", return_value="Content"):
                result = handler.process_pdf(
                    "https://example.com/document.pdf",
                    title="Title",
                )

        assert result.metadata.source_url == "https://example.com/document.pdf"

    def test_process_default_section_empty(self, handler, tmp_path):
        """Test section defaults to empty string."""
        pdf_path = tmp_path / "test.pdf"

        with patch.object(handler, "download_pdf", return_value=pdf_path):
            with patch.object(handler, "extract_text", return_value="Content"):
                result = handler.process_pdf(
                    "https://example.com/doc.pdf",
                    title="Title",
                )

        assert result.metadata.section == ""

    def test_process_returns_none_on_download_error(self, handler):
        """Test None returned when download fails."""
        with patch.object(handler, "download_pdf", side_effect=ContentExtractionError("Failed")):
            result = handler.process_pdf(
                "https://example.com/doc.pdf",
                title="Title",
            )

        assert result is None

    def test_process_returns_none_on_extraction_error(self, handler, tmp_path):
        """Test None returned when extraction fails."""
        pdf_path = tmp_path / "test.pdf"

        with patch.object(handler, "download_pdf", return_value=pdf_path):
            with patch.object(
                handler, "extract_text", side_effect=ContentExtractionError("Failed")
            ):
                result = handler.process_pdf(
                    "https://example.com/doc.pdf",
                    title="Title",
                )

        assert result is None

    def test_process_returns_none_for_empty_content(self, handler, tmp_path):
        """Test None returned when no text extracted."""
        pdf_path = tmp_path / "test.pdf"

        with patch.object(handler, "download_pdf", return_value=pdf_path):
            with patch.object(handler, "extract_text", return_value="   "):
                result = handler.process_pdf(
                    "https://example.com/doc.pdf",
                    title="Title",
                )

        assert result is None

    def test_process_returns_none_on_unexpected_error(self, handler, tmp_path):
        """Test None returned for unexpected errors."""
        pdf_path = tmp_path / "test.pdf"

        with patch.object(handler, "download_pdf", return_value=pdf_path):
            with patch.object(
                handler, "extract_text", side_effect=ValueError("Unexpected")
            ):
                result = handler.process_pdf(
                    "https://example.com/doc.pdf",
                    title="Title",
                )

        assert result is None


class TestIntegration:
    """Integration tests for PDFHandler."""

    @pytest.fixture
    def handler(self, tmp_path):
        """Create handler with mocked dependencies."""
        mock_session = Mock(spec=requests.Session)
        mock_limiter = Mock(spec=RateLimiter)
        mock_config = Mock(spec=ScraperConfig)
        mock_config.raw_dir = tmp_path / "raw"
        mock_config.raw_dir.mkdir(parents=True)

        handler = PDFHandler(mock_session, mock_limiter, mock_config)
        handler.pdf_dir.mkdir(parents=True, exist_ok=True)
        return handler

    def test_full_download_flow(self, handler):
        """Test complete download flow creates file with content."""
        # Mock response
        mock_response = Mock()
        mock_response.headers = {"Content-Disposition": 'filename="test.pdf"'}
        mock_response.iter_content.return_value = [b"PDF", b"CONTENT", b"HERE"]
        handler.session.get.return_value = mock_response

        filepath = handler.download_pdf("https://example.com/doc.pdf")

        assert filepath.exists()
        assert filepath.read_bytes() == b"PDFCONTENTHERE"
        handler.rate_limiter.wait.assert_called_once()

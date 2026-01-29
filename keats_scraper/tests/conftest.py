"""Shared fixtures for KEATS scraper tests."""

import sys
from pathlib import Path
from unittest.mock import MagicMock
from datetime import datetime

import pytest
import requests

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ScraperConfig, KEATSConfig, AuthConfig, RateLimitConfig, ChunkConfig
from models.document import Document, DocumentMetadata, ResourceInfo
from models.chunk import Chunk, ChunkMetadata


# --- Configuration Fixtures ---


@pytest.fixture
def temp_data_dir(tmp_path):
    """Provide a temporary data directory structure."""
    data_dir = tmp_path / "data"
    (data_dir / "raw" / "html").mkdir(parents=True)
    (data_dir / "raw" / "pdf").mkdir(parents=True)
    (data_dir / "processed").mkdir(parents=True)
    (data_dir / "chunks").mkdir(parents=True)
    return data_dir


@pytest.fixture
def mock_config(tmp_path, temp_data_dir):
    """Create a ScraperConfig with temp directories."""
    config = ScraperConfig()
    config.data_dir = temp_data_dir
    config.raw_dir = temp_data_dir / "raw"
    config.processed_dir = temp_data_dir / "processed"
    config.chunks_dir = temp_data_dir / "chunks"
    config.auth.cookie_file = tmp_path / ".cookies"
    config.log_file = tmp_path / "test.log"
    return config


@pytest.fixture
def rate_limit_config():
    """Create RateLimitConfig for fast testing (no delays)."""
    return RateLimitConfig(
        requests_per_minute=10000,
        min_delay_seconds=0,
        max_delay_seconds=0.001,
        max_retries=3,
        backoff_factor=2.0,
    )


@pytest.fixture
def chunk_config():
    """Create ChunkConfig for testing."""
    return ChunkConfig(
        chunk_size=100,
        chunk_overlap=10,
        preserve_headings=True,
    )


# --- HTTP Mocking Fixtures ---


@pytest.fixture
def mock_session(mocker):
    """Create a mock requests.Session."""
    session = mocker.MagicMock(spec=requests.Session)
    session.cookies = mocker.MagicMock()
    session.headers = {}
    return session


@pytest.fixture
def mock_response_factory(mocker):
    """Factory for creating mock HTTP responses."""
    def _create_response(
        status_code=200,
        text="",
        content=b"",
        headers=None,
        url="https://keats.kcl.ac.uk/test",
    ):
        response = mocker.MagicMock()
        response.status_code = status_code
        response.text = text
        response.content = content
        response.url = url
        response.headers = headers or {}
        response.raise_for_status = mocker.MagicMock()
        if status_code >= 400:
            response.raise_for_status.side_effect = requests.HTTPError()
        return response
    return _create_response


# --- Model Fixtures ---


@pytest.fixture
def sample_document():
    """Create a sample Document for testing."""
    return Document.create(
        source_url="https://keats.kcl.ac.uk/mod/page/view.php?id=12345",
        title="Test Document Title",
        content="This is the test document content. It has multiple sentences for testing purposes.",
        content_type="page",
        section="Test Section",
    )


@pytest.fixture
def sample_documents(sample_document):
    """Create a list of sample documents."""
    doc2 = Document.create(
        source_url="https://keats.kcl.ac.uk/mod/page/view.php?id=67890",
        title="Second Test Document",
        content="Another document with different content for testing the chunker.",
        content_type="page",
        section="Another Section",
    )
    return [sample_document, doc2]


@pytest.fixture
def sample_chunk():
    """Create a sample Chunk for testing."""
    return Chunk.create(
        text="This is a test chunk with some content.",
        document_id="abc123def456",
        document_title="Test Document",
        source_url="https://keats.kcl.ac.uk/test",
        chunk_index=0,
        total_chunks=3,
        section="Test Section",
        heading_path=["Main Heading", "Sub Heading"],
    )


@pytest.fixture
def sample_chunks(sample_chunk):
    """Create a list of sample chunks."""
    chunk2 = Chunk.create(
        text="Second chunk content here.",
        document_id="abc123def456",
        document_title="Test Document",
        source_url="https://keats.kcl.ac.uk/test",
        chunk_index=1,
        total_chunks=3,
        section="Test Section",
        heading_path=["Main Heading", "Sub Heading"],
    )
    chunk3 = Chunk.create(
        text="Third and final chunk.",
        document_id="xyz789",
        document_title="Other Document",
        source_url="https://keats.kcl.ac.uk/other",
        chunk_index=0,
        total_chunks=1,
        section="Other Section",
    )
    return [sample_chunk, chunk2, chunk3]


@pytest.fixture
def sample_resource_info():
    """Create a sample ResourceInfo for testing."""
    return ResourceInfo(
        url="https://keats.kcl.ac.uk/mod/page/view.php?id=12345",
        title="Test Resource",
        resource_type="page",
        section="Test Section",
        section_index=0,
    )


# --- Cookie Fixtures ---


@pytest.fixture
def sample_cookies():
    """Sample browser cookies."""
    return [
        {
            "name": "MoodleSession",
            "value": "abc123sessiontoken",
            "domain": "keats.kcl.ac.uk",
            "path": "/",
        },
        {
            "name": "MOODLEID1_",
            "value": "xyz789userid",
            "domain": ".kcl.ac.uk",
            "path": "/",
        },
    ]


# --- HTML Fixture ---


@pytest.fixture
def sample_course_html():
    """Sample KEATS course page HTML."""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>Course: Informatics Student Handbook</title></head>
    <body>
        <div id="page">
            <ul class="topics">
                <li class="section main" id="section-0">
                    <h3 class="sectionname">General Information</h3>
                    <ul class="section">
                        <li class="activity page">
                            <a href="/mod/page/view.php?id=12345">
                                <span class="instancename">Welcome Page</span>
                            </a>
                        </li>
                        <li class="activity resource">
                            <a href="/mod/resource/view.php?id=12346">
                                <span class="instancename">Handbook PDF</span>
                            </a>
                        </li>
                    </ul>
                </li>
                <li class="section main" id="section-1">
                    <h3 class="sectionname">Academic Regulations</h3>
                    <ul class="section">
                        <li class="activity page">
                            <a href="/mod/page/view.php?id=12347">
                                <span class="instancename">Attendance Policy</span>
                            </a>
                        </li>
                        <li class="activity folder">
                            <a href="/mod/folder/view.php?id=12348">
                                <span class="instancename">Supporting Documents</span>
                            </a>
                        </li>
                    </ul>
                </li>
                <li class="section main hidden" id="section-2">
                    <h3 class="sectionname">Hidden Section</h3>
                </li>
            </ul>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_moodle_page_html():
    """Sample Moodle page content HTML."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Welcome Page - KEATS</title>
        <script>alert('test');</script>
        <style>.hidden { display: none; }</style>
    </head>
    <body>
        <nav class="navbar">Navigation content to remove</nav>
        <div id="page">
            <div id="region-main">
                <h1>Welcome to the Informatics Handbook</h1>
                <div class="content">
                    <p>This handbook contains important information for students.</p>
                    <h2>Key Information</h2>
                    <p>Please read all sections carefully.</p>
                    <table>
                        <tr><th>Topic</th><th>Page</th></tr>
                        <tr><td>Attendance</td><td>5</td></tr>
                        <tr><td>Assessment</td><td>10</td></tr>
                    </table>
                    <ul>
                        <li>Item 1</li>
                        <li>Item 2</li>
                    </ul>
                </div>
            </div>
        </div>
        <footer>Footer content</footer>
        <span class="accesshide">Screen reader text</span>
    </body>
    </html>
    """


@pytest.fixture
def sample_book_html():
    """Sample Moodle book table of contents HTML."""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <div class="book_toc">
            <a href="/mod/book/view.php?id=123&chapterid=1">Chapter 1: Introduction</a>
            <a href="/mod/book/view.php?id=123&chapterid=2">Chapter 2: Policies</a>
            <a href="/mod/book/view.php?id=123&chapterid=3">Chapter 3: Procedures</a>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def sample_folder_html():
    """Sample Moodle folder contents HTML."""
    return """
    <!DOCTYPE html>
    <html>
    <body>
        <div class="fp-filename-icon">
            <a href="/pluginfile.php/123/mod_folder/content/0/document.pdf">document.pdf</a>
        </div>
        <div class="fp-filename-icon">
            <a href="/pluginfile.php/123/mod_folder/content/0/guide.docx">guide.docx</a>
        </div>
    </body>
    </html>
    """


# --- WebDriver Mock Fixtures ---


@pytest.fixture
def mock_webdriver(mocker):
    """Mock Selenium WebDriver."""
    driver = mocker.MagicMock()
    driver.current_url = "https://keats.kcl.ac.uk/my/"
    driver.get_cookies.return_value = [
        {"name": "MoodleSession", "value": "test123", "domain": "keats.kcl.ac.uk"}
    ]
    return driver


# --- Time Mock Helpers ---


@pytest.fixture
def mock_time(mocker):
    """Mock time.time() to return predictable values."""
    mock = mocker.patch("time.time")
    mock.return_value = 1000.0
    return mock


@pytest.fixture
def mock_sleep(mocker):
    """Mock time.sleep() to skip delays."""
    return mocker.patch("time.sleep")


@pytest.fixture
def mock_random_uniform(mocker):
    """Mock random.uniform() for deterministic tests."""
    mock = mocker.patch("random.uniform")
    mock.return_value = 1.0
    return mock

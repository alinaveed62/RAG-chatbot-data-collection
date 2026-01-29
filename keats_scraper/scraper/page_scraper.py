"""Page content scraper for KEATS Moodle pages."""

from typing import Optional, Tuple
import requests
from bs4 import BeautifulSoup

from ..models.document import Document
from ..utils.logging_config import get_logger
from ..utils.exceptions import ContentExtractionError
from .rate_limiter import RateLimiter

logger = get_logger()


class PageScraper:
    """Scrapes content from KEATS Moodle pages."""

    # CSS selectors for Moodle content areas
    CONTENT_SELECTORS = [
        "#region-main",
        ".course-content",
        "#page-content",
        "div[role='main']",
        ".generalbox",
    ]

    # Elements to remove
    REMOVE_SELECTORS = [
        "nav",
        ".navbar",
        "footer",
        ".footer",
        "#page-footer",
        ".breadcrumb",
        ".block",
        ".activity-navigation",
        "script",
        "style",
        "noscript",
        ".sr-only",
        ".visually-hidden",
    ]

    def __init__(self, session: requests.Session, rate_limiter: RateLimiter):
        """
        Initialize page scraper.

        Args:
            session: Authenticated requests session
            rate_limiter: Rate limiter instance
        """
        self.session = session
        self.rate_limiter = rate_limiter

    def fetch_page(self, url: str) -> Tuple[str, int]:
        """
        Fetch page HTML with rate limiting.

        Args:
            url: Page URL to fetch

        Returns:
            Tuple of (html_content, status_code)

        Raises:
            ContentExtractionError: If fetch fails
        """
        self.rate_limiter.wait()

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text, response.status_code

        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            raise ContentExtractionError(f"Failed to fetch page: {e}")

    def extract_content(self, html: str, url: str) -> Tuple[str, str]:
        """
        Extract main content from Moodle page HTML.

        Args:
            html: Raw HTML content
            url: Source URL (for logging)

        Returns:
            Tuple of (title, main_content_html)
        """
        soup = BeautifulSoup(html, "lxml")

        # Extract title
        title = ""
        title_elem = soup.find("h1") or soup.find("title")
        if title_elem:
            title = title_elem.get_text(strip=True)

        # Remove unwanted elements
        for selector in self.REMOVE_SELECTORS:
            for elem in soup.select(selector):
                elem.decompose()

        # Find main content
        content_elem = None
        for selector in self.CONTENT_SELECTORS:
            content_elem = soup.select_one(selector)
            if content_elem:
                break

        if not content_elem:
            logger.warning(f"No main content found for {url}")
            content_elem = soup.body if soup.body else soup

        return title, str(content_elem)

    def scrape_page(
        self,
        url: str,
        section: str = "",
    ) -> Optional[Document]:
        """
        Scrape a single KEATS page.

        Args:
            url: Page URL
            section: Handbook section name

        Returns:
            Document or None if extraction fails
        """
        logger.info(f"Scraping page: {url}")

        try:
            html, status = self.fetch_page(url)

            if status != 200:
                logger.warning(f"Non-200 status ({status}) for {url}")
                return None

            title, content_html = self.extract_content(html, url)

            if not title:
                title = "Untitled Page"

            # Create document with raw HTML (cleaning happens later)
            document = Document.create(
                source_url=url,
                title=title,
                content="",  # Will be populated after cleaning
                content_type="page",
                section=section,
                raw_html=content_html,
            )

            logger.info(f"Extracted: '{title}' from {url}")
            return document

        except ContentExtractionError:
            return None
        except Exception as e:
            logger.error(f"Unexpected error scraping {url}: {e}")
            return None

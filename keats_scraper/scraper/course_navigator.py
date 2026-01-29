"""KEATS course structure navigator."""

import re
from typing import List, Dict, Optional
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup

from models.document import ResourceInfo
from config import ScraperConfig
from utils.logging_config import get_logger
from utils.exceptions import ContentExtractionError
from scraper.rate_limiter import RateLimiter

logger = get_logger()


class CourseNavigator:
    """Navigates and discovers resources in a KEATS course."""

    # Moodle resource type patterns
    RESOURCE_PATTERNS = {
        "page": r"/mod/page/view\.php",
        "resource": r"/mod/resource/view\.php",  # Files (PDFs, etc.)
        "folder": r"/mod/folder/view\.php",
        "book": r"/mod/book/view\.php",
        "url": r"/mod/url/view\.php",
        "label": r"/mod/label/view\.php",
    }

    def __init__(
        self,
        session: requests.Session,
        config: ScraperConfig,
        rate_limiter: RateLimiter,
    ):
        """
        Initialize course navigator.

        Args:
            session: Authenticated requests session
            config: Scraper configuration
            rate_limiter: Rate limiter instance
        """
        self.session = session
        self.config = config
        self.rate_limiter = rate_limiter
        self.base_url = config.keats.base_url

    def fetch_course_page(self) -> str:
        """
        Fetch the main course page HTML.

        Returns:
            Course page HTML

        Raises:
            ContentExtractionError: If fetch fails
        """
        self.rate_limiter.wait()

        try:
            response = self.session.get(self.config.keats.course_url, timeout=30)
            response.raise_for_status()

            # Check if we got redirected to login
            if "login" in response.url.lower():
                raise ContentExtractionError(
                    "Session expired - redirected to login page"
                )

            return response.text

        except requests.RequestException as e:
            logger.error(f"Failed to fetch course page: {e}")
            raise ContentExtractionError(f"Failed to fetch course page: {e}")

    def _identify_resource_type(self, url: str) -> str:
        """Identify Moodle resource type from URL."""
        for resource_type, pattern in self.RESOURCE_PATTERNS.items():
            if re.search(pattern, url):
                return resource_type
        return "unknown"

    def _parse_sections(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Parse course sections from page.

        Args:
            soup: BeautifulSoup of course page

        Returns:
            List of section info dicts
        """
        sections = []

        # Moodle uses various section container classes
        section_selectors = [
            ".section.main",
            "li.section",
            ".topics .section",
            ".weeks .section",
        ]

        section_elements = []
        for selector in section_selectors:
            section_elements = soup.select(selector)
            if section_elements:
                break

        for i, section in enumerate(section_elements):
            # Get section name
            name_elem = section.select_one(
                ".sectionname, .section-title, h3.sectionname"
            )
            section_name = name_elem.get_text(strip=True) if name_elem else f"Section {i}"

            # Skip empty/hidden sections
            if "hidden" in section.get("class", []):
                continue

            sections.append({
                "index": i,
                "name": section_name,
                "element": section,
            })

        return sections

    def discover_resources(self) -> List[ResourceInfo]:
        """
        Discover all resources in the course.

        Returns:
            List of ResourceInfo objects for each discovered resource
        """
        logger.info(f"Discovering resources in course: {self.config.keats.course_url}")

        html = self.fetch_course_page()
        soup = BeautifulSoup(html, "lxml")

        resources = []
        sections = self._parse_sections(soup)

        logger.info(f"Found {len(sections)} sections")

        for section_info in sections:
            section = section_info["element"]
            section_name = section_info["name"]
            section_index = section_info["index"]

            # Find all activity links in this section
            activities = section.select(".activity a, .activityinstance a")

            for activity in activities:
                href = activity.get("href", "")

                if not href or href == "#":
                    continue

                # Make absolute URL
                url = urljoin(self.base_url, href)

                # Only process KEATS URLs
                if "keats.kcl.ac.uk" not in url:
                    continue

                # Identify resource type
                resource_type = self._identify_resource_type(url)

                if resource_type == "unknown":
                    continue

                # Get title
                title_elem = activity.select_one(".instancename, .activityname")
                if title_elem:
                    # Remove accesshide spans
                    for hidden in title_elem.select(".accesshide"):
                        hidden.decompose()
                    title = title_elem.get_text(strip=True)
                else:
                    title = activity.get_text(strip=True)

                if not title:
                    title = f"Untitled {resource_type}"

                resource = ResourceInfo(
                    url=url,
                    title=title,
                    resource_type=resource_type,
                    section=section_name,
                    section_index=section_index,
                )

                resources.append(resource)
                logger.debug(f"Found {resource_type}: {title}")

        # Remove duplicates (same URL)
        seen_urls = set()
        unique_resources = []
        for resource in resources:
            if resource.url not in seen_urls:
                seen_urls.add(resource.url)
                unique_resources.append(resource)

        logger.info(f"Discovered {len(unique_resources)} unique resources")
        return unique_resources

    def discover_book_chapters(self, book_url: str) -> List[ResourceInfo]:
        """
        Discover chapters within a Moodle book.

        Args:
            book_url: URL of the book resource

        Returns:
            List of ResourceInfo for each chapter
        """
        self.rate_limiter.wait()

        try:
            response = self.session.get(book_url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch book {book_url}: {e}")
            return []

        soup = BeautifulSoup(response.text, "lxml")
        chapters = []

        # Book table of contents
        toc = soup.select(".book_toc a, #book-toc a")

        for link in toc:
            href = link.get("href", "")
            if not href:
                continue

            url = urljoin(self.base_url, href)
            title = link.get_text(strip=True)

            chapter = ResourceInfo(
                url=url,
                title=title,
                resource_type="book_chapter",
                section="",  # Will inherit from parent book
            )
            chapters.append(chapter)

        logger.info(f"Found {len(chapters)} chapters in book")
        return chapters

    def discover_folder_contents(self, folder_url: str) -> List[ResourceInfo]:
        """
        Discover files within a Moodle folder.

        Args:
            folder_url: URL of the folder resource

        Returns:
            List of ResourceInfo for each file
        """
        self.rate_limiter.wait()

        try:
            response = self.session.get(folder_url, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            logger.error(f"Failed to fetch folder {folder_url}: {e}")
            return []

        soup = BeautifulSoup(response.text, "lxml")
        files = []

        # Folder file listings
        file_links = soup.select(".fp-filename-icon a, .folder-content a")

        for link in file_links:
            href = link.get("href", "")
            if not href:
                continue

            url = urljoin(self.base_url, href)
            title = link.get_text(strip=True)

            # Determine if PDF or other file
            resource_type = "resource"
            if ".pdf" in url.lower() or ".pdf" in title.lower():
                resource_type = "pdf"

            file_info = ResourceInfo(
                url=url,
                title=title,
                resource_type=resource_type,
            )
            files.append(file_info)

        logger.info(f"Found {len(files)} files in folder")
        return files

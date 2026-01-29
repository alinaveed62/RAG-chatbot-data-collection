"""Text normalization for consistent processing."""

import re
import unicodedata
from typing import Optional

from ..utils.logging_config import get_logger

logger = get_logger()


class TextNormalizer:
    """Normalizes text for consistent RAG processing."""

    # Characters to replace with standard equivalents
    CHAR_REPLACEMENTS = {
        "\u2018": "'",  # Left single quote
        "\u2019": "'",  # Right single quote
        "\u201c": '"',  # Left double quote
        "\u201d": '"',  # Right double quote
        "\u2013": "-",  # En dash
        "\u2014": "-",  # Em dash
        "\u2026": "...",  # Ellipsis
        "\u00a0": " ",  # Non-breaking space
        "\u200b": "",  # Zero-width space
        "\ufeff": "",  # BOM
    }

    def __init__(self):
        """Initialize text normalizer."""
        pass

    def normalize_unicode(self, text: str) -> str:
        """
        Normalize unicode to NFC form.

        Args:
            text: Input text

        Returns:
            Normalized text
        """
        return unicodedata.normalize("NFC", text)

    def replace_special_chars(self, text: str) -> str:
        """
        Replace special unicode characters with ASCII equivalents.

        Args:
            text: Input text

        Returns:
            Text with replacements applied
        """
        for char, replacement in self.CHAR_REPLACEMENTS.items():
            text = text.replace(char, replacement)
        return text

    def fix_encoding_issues(self, text: str) -> str:
        """
        Fix common encoding issues.

        Args:
            text: Input text

        Returns:
            Fixed text
        """
        # Fix mojibake for common characters
        replacements = [
            ("â€™", "'"),
            ("â€œ", '"'),
            ("â€", '"'),
            ("â€"", "-"),
            ("â€"", "-"),
            ("â€¦", "..."),
            ("Â ", " "),
        ]

        for wrong, right in replacements:
            text = text.replace(wrong, right)

        return text

    def normalize_whitespace(self, text: str) -> str:
        """
        Normalize all whitespace.

        Args:
            text: Input text

        Returns:
            Text with normalized whitespace
        """
        # Replace tabs with spaces
        text = text.replace("\t", " ")

        # Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Replace multiple spaces with single space
        text = re.sub(r" +", " ", text)

        # Replace 3+ newlines with 2
        text = re.sub(r"\n{3,}", "\n\n", text)

        # Strip whitespace from each line
        lines = [line.strip() for line in text.split("\n")]
        text = "\n".join(lines)

        return text.strip()

    def remove_control_characters(self, text: str) -> str:
        """
        Remove control characters except newlines and tabs.

        Args:
            text: Input text

        Returns:
            Cleaned text
        """
        # Keep printable characters, newlines, and tabs
        cleaned = []
        for char in text:
            if char in "\n\t":
                cleaned.append(char)
            elif unicodedata.category(char) != "Cc":
                cleaned.append(char)
            elif char == " ":
                cleaned.append(char)
        return "".join(cleaned)

    def standardize_bullets(self, text: str) -> str:
        """
        Standardize bullet point characters.

        Args:
            text: Input text

        Returns:
            Text with standardized bullets
        """
        bullet_chars = ["•", "·", "●", "○", "▪", "▫", "◦", "‣", "⁃"]
        for bullet in bullet_chars:
            text = text.replace(bullet, "-")
        return text

    def normalize(self, text: str) -> str:
        """
        Apply all normalizations.

        Args:
            text: Input text

        Returns:
            Fully normalized text
        """
        if not text:
            return ""

        try:
            text = self.normalize_unicode(text)
            text = self.fix_encoding_issues(text)
            text = self.replace_special_chars(text)
            text = self.remove_control_characters(text)
            text = self.standardize_bullets(text)
            text = self.normalize_whitespace(text)
            return text

        except Exception as e:
            logger.error(f"Text normalization failed: {e}")
            return text

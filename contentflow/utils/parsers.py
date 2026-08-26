import httpx
import hashlib
import socket
import ipaddress
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
import feedparser
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)


def validate_public_url(url: str) -> bool:
    """Validate URL to prevent SSRF attacks."""
    try:
        parsed = urlparse(url)

        # Only allow http and https
        if parsed.scheme not in ("http", "https"):
            logger.warning(f"SSRF blocked: Invalid scheme in {url}")
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        # Resolve hostname and check if it's a private IP
        try:
            addrinfo = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
            for family, type_, proto, canonname, sockaddr in addrinfo:
                ip_str = sockaddr[0]
                ip = ipaddress.ip_address(ip_str)

                # Reject private, loopback, link-local, multicast, reserved
                if (ip.is_private or ip.is_loopback or ip.is_link_local or
                    ip.is_multicast or ip.is_reserved):
                    logger.warning(f"SSRF blocked: Private IP {ip} for {url}")
                    return False
        except (socket.gaierror, ValueError):
            logger.warning(f"SSRF blocked: Could not resolve {hostname}")
            return False

        return True
    except Exception as e:
        logger.error(f"URL validation error: {e}")
        return False


class ParserResult:
    def __init__(self, title: str, url: str, content: str,
                 description: str = "", author: str = "",
                 published_at: Optional[datetime] = None):
        self.title = title
        self.url = url
        self.content = content
        self.description = description
        self.author = author
        self.published_at = published_at
        self.content_hash = hashlib.sha256(content.encode()).hexdigest()


class RSSParser:
    @staticmethod
    async def parse(url: str) -> List[ParserResult]:
        """Parse RSS feed and return list of articles."""
        if not validate_public_url(url):
            logger.warning(f"RSS feed URL blocked by SSRF protection: {url}")
            return []

        try:
            async with httpx.AsyncClient(follow_redirects=False) as client:
                response = await client.get(url, timeout=10)
                response.raise_for_status()

            feed = feedparser.parse(response.content)
            results = []

            for entry in feed.entries[:20]:  # Limit to 20 entries
                try:
                    title = entry.get("title", "Untitled")
                    link = entry.get("link", "")
                    description = entry.get("summary", "")
                    author = entry.get("author", "")

                    # Extract published date
                    published_at = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published_at = datetime(*entry.published_parsed[:6])

                    # Use description as content for RSS
                    content = description if description else title

                    result = ParserResult(
                        title=title,
                        url=link,
                        content=content,
                        description=description,
                        author=author,
                        published_at=published_at
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Error parsing RSS entry: {e}")
                    continue

            return results
        except Exception as e:
            logger.error(f"Error parsing RSS feed {url}: {e}")
            return []


class WebsiteParser:
    @staticmethod
    async def parse(url: str) -> List[ParserResult]:
        """Parse website and extract article content."""
        if not validate_public_url(url):
            logger.warning(f"Website URL blocked by SSRF protection: {url}")
            return []

        try:
            async with httpx.AsyncClient(follow_redirects=False) as client:
                response = await client.get(url, timeout=10)
                response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            results = []

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Try to find main content
            title = WebsiteParser._extract_title(soup)
            content = WebsiteParser._extract_content(soup)

            if content:
                result = ParserResult(
                    title=title or "Website Content",
                    url=url,
                    content=content,
                    published_at=datetime.utcnow()
                )
                results.append(result)

            return results
        except Exception as e:
            logger.error(f"Error parsing website {url}: {e}")
            return []

    @staticmethod
    def _extract_title(soup: BeautifulSoup) -> str:
        """Extract title from webpage."""
        if soup.title:
            return soup.title.string
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)
        return "Website Content"

    @staticmethod
    def _extract_content(soup: BeautifulSoup) -> str:
        """Extract main content from webpage."""
        # Try common article containers
        for selector in ["article", "main", "[role='main']", ".content", ".post", ".entry"]:
            content = soup.select_one(selector)
            if content:
                return content.get_text(separator=" ", strip=True)[:2000]

        # Fallback: get all paragraphs
        paragraphs = soup.find_all("p")
        if paragraphs:
            content = " ".join([p.get_text(strip=True) for p in paragraphs])
            return content[:2000]

        return soup.get_text(separator=" ", strip=True)[:2000]


class TelegramChannelParser:
    """Parser for Telegram channels - requires bot to have access."""

    @staticmethod
    async def parse(channel_id: int, bot) -> List[ParserResult]:
        """
        Parse recent messages from Telegram channel.
        Requires bot to be a member of the channel.
        """
        try:
            # Get last 20 messages from channel
            results = []
            async for message in bot.get_chat_history(channel_id, limit=20):
                if message.text or message.caption:
                    content = message.text or message.caption or ""

                    result = ParserResult(
                        title=content[:100] if content else "Telegram message",
                        url=f"https://t.me/c/{abs(channel_id)}/{message.message_id}",
                        content=content,
                        author=message.author_signature or "Unknown",
                        published_at=message.date
                    )
                    results.append(result)

            return results
        except Exception as e:
            logger.error(f"Error parsing Telegram channel {channel_id}: {e}")
            return []


class ContentDeduplicator:
    """Helper to detect duplicate content."""

    @staticmethod
    def get_content_hash(content: str) -> str:
        """Generate hash of content for deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()

    @staticmethod
    def are_similar(content1: str, content2: str, threshold: float = 0.8) -> bool:
        """Check if two contents are similar using simple heuristics."""
        if not content1 or not content2:
            return False

        # Check if one contains most of the other (simplified similarity)
        len1, len2 = len(content1), len(content2)
        min_len = min(len1, len2)
        max_len = max(len1, len2)

        if min_len == 0:
            return False

        similarity = min_len / max_len
        return similarity >= threshold

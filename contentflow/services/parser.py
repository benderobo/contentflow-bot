import logging
import hashlib
import asyncio
import socket
from datetime import datetime
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import aiohttp
import feedparser
from bs4 import BeautifulSoup
from core.config import is_private_ip

logger = logging.getLogger(__name__)


class BaseParser:
    async def parse(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        raise NotImplementedError


class RSSParser(BaseParser):
    @staticmethod
    def _validate_url(url: str) -> bool:
        """Validate URL to prevent SSRF attacks."""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False

            hostname = parsed.hostname
            if not hostname:
                return False

            # Resolve hostname and check if it's private
            try:
                ip_info = socket.getaddrinfo(hostname, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
                for family, type_, proto, canonname, sockaddr in ip_info:
                    ip = sockaddr[0]
                    if is_private_ip(ip):
                        logger.warning(f"SSRF attempt blocked for URL: {url}")
                        return False
            except socket.gaierror:
                return False

            return True
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False

    async def parse(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        url = config.get("url")
        if not url or not self._validate_url(url):
            return []

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    content = await resp.text()
                    feed = feedparser.parse(content)

            items = []
            for entry in feed.entries[:20]:  # Limit to last 20
                item = {
                    "title": entry.get("title", ""),
                    "description": entry.get("summary", ""),
                    "url": entry.get("link", ""),
                    "author": entry.get("author", ""),
                    "published_at": self._parse_date(entry.get("published", "")),
                }
                items.append(item)
            return items
        except Exception as e:
            logger.error(f"RSS parse error: {e}")
            return []

    def _parse_date(self, date_str: str) -> Optional[datetime]:
        try:
            from dateutil import parser
            return parser.isoparse(date_str)
        except:
            return None


class WebsiteParser(BaseParser):
    @staticmethod
    def _validate_url(url: str) -> bool:
        """Validate URL to prevent SSRF attacks."""
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False

            hostname = parsed.hostname
            if not hostname:
                return False

            # Resolve hostname and check if it's private
            try:
                ip_info = socket.getaddrinfo(hostname, 80, socket.AF_UNSPEC, socket.SOCK_STREAM)
                for family, type_, proto, canonname, sockaddr in ip_info:
                    ip = sockaddr[0]
                    if is_private_ip(ip):
                        logger.warning(f"SSRF attempt blocked for URL: {url}")
                        return False
            except socket.gaierror:
                return False

            return True
        except Exception as e:
            logger.error(f"URL validation error: {e}")
            return False

    async def parse(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        url = config.get("url")
        if not url or not self._validate_url(url):
            return []

        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return []
                    html = await resp.text()

            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()

            title = soup.find("title")
            title_text = title.string if title else ""

            # Remove common ad/navigation patterns
            for element in soup.find_all(["div", "aside"]):
                if element.get("class", []) and any(
                    cls in str(element.get("class", [])).lower()
                    for cls in ["ad", "sidebar", "nav", "cookie", "banner"]
                ):
                    element.decompose()

            # Find main content
            main_content = soup.find("article") or soup.find("main") or soup.find("div", class_="content")
            if main_content:
                text = main_content.get_text(separator=" ", strip=True)
            else:
                text = soup.get_text(separator=" ", strip=True)

            # Find image
            image_url = None
            for img in soup.find_all("img"):
                if img.get("src"):
                    image_url = img.get("src")
                    break

            return [
                {
                    "title": title_text[:500],
                    "description": text[:1000],
                    "url": url,
                    "published_at": datetime.utcnow(),
                    "image_url": image_url,
                }
            ]
        except Exception as e:
            logger.error(f"Website parse error: {e}")
            return []


class TelegramParser(BaseParser):
    async def parse(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        channel_username = config.get("username")
        if not channel_username:
            logger.error("Telegram parser: username is required")
            return []

        try:
            from telethon import TelegramClient
            from core.config import get_settings

            settings = get_settings()
            if not settings.telegram_api_id or not settings.telegram_api_hash:
                logger.error("Telegram API credentials not configured")
                return []

            client = TelegramClient('anon', settings.telegram_api_id, settings.telegram_api_hash)

            async with client:
                entity = await client.get_entity(channel_username)
                messages = await client.get_messages(entity, limit=20)

                items = []
                for msg in messages:
                    if msg.text:
                        item = {
                            "title": msg.text[:100] if msg.text else "Telegram message",
                            "description": msg.text[:1000] if msg.text else "",
                            "url": f"https://t.me/{channel_username}/{msg.id}",
                            "author": channel_username,
                            "published_at": msg.date,
                        }
                        items.append(item)

                return items
        except Exception as e:
            logger.error(f"Telegram parse error: {e}")
            return []


class ParserFactory:
    _parsers = {
        "rss": RSSParser,
        "website": WebsiteParser,
        "telegram": TelegramParser,
    }

    @classmethod
    def get_parser(cls, source_type: str) -> Optional[BaseParser]:
        parser_class = cls._parsers.get(source_type.lower())
        return parser_class() if parser_class else None

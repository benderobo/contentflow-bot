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
            logger.debug(f"RSS: URL validation failed for {url}")
            return []

        logger.debug(f"RSS: Fetching from {url}")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    logger.debug(f"RSS: Got status {resp.status} from {url}")
                    if resp.status != 200:
                        logger.warning(f"RSS: Non-200 status {resp.status} from {url}")
                        return []
                    content = await resp.text()
                    feed = feedparser.parse(content)

            logger.debug(f"RSS: Parsed feed, found {len(feed.entries)} entries")
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
            logger.info(f"RSS: Successfully parsed {len(items)} items from {url}")
            return items
        except asyncio.TimeoutError:
            logger.error(f"RSS: Timeout fetching {url}")
            return []
        except Exception as e:
            logger.error(f"RSS parse error for {url}: {e}", exc_info=True)
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
            logger.debug(f"Website: URL validation failed for {url}")
            return []

        logger.debug(f"Website: Fetching from {url}")
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    logger.debug(f"Website: Got status {resp.status} from {url}")
                    if resp.status != 200:
                        logger.warning(f"Website: Non-200 status {resp.status} from {url}")
                        return []
                    html = await resp.text()
                    logger.debug(f"Website: Received {len(html)} bytes from {url}")

            soup = BeautifulSoup(html, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style", "nav", "footer"]):
                script.decompose()

            title = soup.find("title")
            title_text = title.string if title else ""
            logger.debug(f"Website: Found title: {title_text[:50]}")

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
                logger.debug(f"Website: Extracted text from article/main element")
            else:
                text = soup.get_text(separator=" ", strip=True)
                logger.debug(f"Website: Extracted text from entire page")

            logger.debug(f"Website: Text length: {len(text)} chars")

            # Find image
            image_url = None
            for img in soup.find_all("img"):
                if img.get("src"):
                    image_url = img.get("src")
                    break

            logger.info(f"Website: Successfully parsed {url}, text={len(text)} chars, image={image_url is not None}")
            return [
                {
                    "title": title_text[:500],
                    "description": text[:1000],
                    "url": url,
                    "published_at": datetime.utcnow(),
                    "image_url": image_url,
                }
            ]
        except asyncio.TimeoutError:
            logger.error(f"Website: Timeout fetching {url}")
            return []
        except Exception as e:
            logger.error(f"Website parse error for {url}: {e}", exc_info=True)
            return []


class TelegramParser(BaseParser):
    async def parse(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        # config can be URL (username) or full config dict with is_private flag
        if isinstance(config, str):
            channel_username = config
            is_private = False
        else:
            channel_username = config.get("username") or config.get("url")
            is_private = config.get("is_private", False)

        if not channel_username:
            logger.error("Telegram parser: username is required")
            return []

        logger.debug(f"Telegram: Parsing channel {channel_username}, is_private={is_private}")

        try:
            from telethon import TelegramClient
            from core.config import get_settings

            settings = get_settings()
            if not settings.telegram_api_id or not settings.telegram_api_hash:
                logger.error("Telegram: API credentials not configured (TELEGRAM_API_ID or TELEGRAM_API_HASH missing)")
                return []

            logger.debug(f"Telegram: API credentials configured")

            # For private channels, use authenticated session; for public, use anonymous
            if is_private:
                if not settings.telegram_phone:
                    logger.warning(f"Telegram: Private channel requires TELEGRAM_PHONE, falling back to public access")
                    is_private = False
                else:
                    logger.debug(f"Telegram: Using authenticated session for private channel")

            if is_private and settings.telegram_phone:
                session_name = f'session_{settings.telegram_phone}'
                client = TelegramClient(session_name, settings.telegram_api_id, settings.telegram_api_hash)

                async with client:
                    if not client.is_user_authorized():
                        logger.debug(f"Telegram: Authenticating with phone {settings.telegram_phone}")
                        await client.start(phone=settings.telegram_phone)

                    logger.debug(f"Telegram: Getting entity for {channel_username}")
                    entity = await client.get_entity(channel_username)
                    logger.debug(f"Telegram: Fetching messages from {channel_username}")
                    messages = await client.get_messages(entity, limit=20)
            else:
                logger.debug(f"Telegram: Using anonymous session for public channel")
                client = TelegramClient('anon', settings.telegram_api_id, settings.telegram_api_hash)

                async with client:
                    logger.debug(f"Telegram: Getting entity for {channel_username}")
                    entity = await client.get_entity(channel_username)
                    logger.debug(f"Telegram: Fetching messages from {channel_username}")
                    messages = await client.get_messages(entity, limit=20)

            logger.debug(f"Telegram: Got {len(messages)} messages from {channel_username}")
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

            logger.info(f"Telegram: Successfully parsed {len(items)} items from {channel_username}")
            return items
        except Exception as e:
            logger.error(f"Telegram parse error for {channel_username}: {e}", exc_info=True)
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

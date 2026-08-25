import logging
import hashlib
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import aiohttp
import feedparser
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class BaseParser:
    async def parse(self, config: Dict[str, Any]) -> list[Dict[str, Any]]:
        raise NotImplementedError


class RSSParser(BaseParser):
    async def parse(self, config: Dict[str, Any]) -> list[Dict[str, Any]]:
        url = config.get("url")
        if not url:
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
    async def parse(self, config: Dict[str, Any]) -> list[Dict[str, Any]]:
        url = config.get("url")
        if not url:
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


class ParserFactory:
    _parsers = {
        "rss": RSSParser,
        "website": WebsiteParser,
    }

    @classmethod
    def get_parser(cls, source_type: str) -> Optional[BaseParser]:
        parser_class = cls._parsers.get(source_type.lower())
        return parser_class() if parser_class else None

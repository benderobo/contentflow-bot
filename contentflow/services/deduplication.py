import hashlib
import logging
from typing import Optional
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


class DeduplicationService:
    SIMILARITY_THRESHOLD = 0.90

    @staticmethod
    def hash_content(text: str) -> str:
        """Generate SHA-256 hash of content."""
        cleaned = " ".join(text.split()).lower()
        return hashlib.sha256(cleaned.encode()).hexdigest()

    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL for comparison."""
        parsed = urlparse(url)
        # Reconstruct without fragment and query params
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

    @staticmethod
    def get_canonical_url(url: str, canonical_url: Optional[str]) -> str:
        """Get canonical URL, preferring provided one."""
        if canonical_url:
            return DeduplicationService.normalize_url(canonical_url)
        return DeduplicationService.normalize_url(url)

    @staticmethod
    def similarity_score(text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        # Simplified version using basic token overlap
        tokens1 = set(text1.lower().split())
        tokens2 = set(text2.lower().split())

        if not tokens1 or not tokens2:
            return 0.0

        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        return intersection / union if union > 0 else 0.0

    @classmethod
    def is_duplicate(
        cls, text: str, other_text: str, threshold: float = SIMILARITY_THRESHOLD
    ) -> bool:
        """Check if texts are similar enough to be considered duplicates."""
        score = cls.similarity_score(text, other_text)
        return score >= threshold

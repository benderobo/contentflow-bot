import pytest
from services.deduplication import DeduplicationService


def test_hash_content():
    """Test content hashing."""
    text = "This is a test content"
    hash1 = DeduplicationService.hash_content(text)
    hash2 = DeduplicationService.hash_content(text)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex length


def test_normalize_url():
    """Test URL normalization."""
    url = "https://example.com/path?query=1#fragment"
    normalized = DeduplicationService.normalize_url(url)

    assert "?" not in normalized
    assert "#" not in normalized
    assert normalized.endswith("/path")


def test_similarity_score():
    """Test text similarity scoring."""
    text1 = "The quick brown fox jumps over the lazy dog"
    text2 = "The quick brown fox jumps over the lazy dog"
    text3 = "Something completely different"

    score1 = DeduplicationService.similarity_score(text1, text2)
    score2 = DeduplicationService.similarity_score(text1, text3)

    assert score1 > 0.9
    assert score2 < 0.5


def test_is_duplicate():
    """Test duplicate detection."""
    text1 = "The quick brown fox jumps over the lazy dog"
    text2 = "The quick brown fox jumps over the lazy dog"
    text3 = "Something completely different"

    assert DeduplicationService.is_duplicate(text1, text2, threshold=0.9)
    assert not DeduplicationService.is_duplicate(text1, text3, threshold=0.9)

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean, JSON
from core.database import Base


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_item_id = Column(Integer, ForeignKey("source_items.id"), nullable=True)
    original_url = Column(String(2048), nullable=True)
    original_text = Column(Text, nullable=True)
    title = Column(String(500), nullable=True)
    body = Column(Text, nullable=True)
    hashtags = Column(JSON, default=[])
    status = Column(
        String(50),
        default="draft",
        index=True,
        nullable=False,
    )
    # new, processing, draft, needs_review, approved, scheduled, published, rejected, failed
    ai_analysis = Column(JSON, nullable=True)
    category = Column(String(100), nullable=True)
    importance = Column(Integer, nullable=True)  # 1-10
    clickbait = Column(Boolean, default=False)
    rewrite_original = Column(Text, nullable=True)
    rewrite_candidate = Column(Text, nullable=True)
    scheduled_at = Column(DateTime, nullable=True, index=True)
    published_at = Column(DateTime, nullable=True, index=True)
    rejected_reason = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Post {self.id} ({self.status})>"

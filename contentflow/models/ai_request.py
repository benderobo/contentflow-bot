from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from core.database import Base


class AIRequest(Base):
    __tablename__ = "ai_requests"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=True)
    prompt_id = Column(Integer, ForeignKey("ai_prompts.id"), nullable=True)
    request_type = Column(String(50), nullable=False)  # rewrite, analyze, etc.
    input_text = Column(Text, nullable=False)
    output_text = Column(Text, nullable=True)
    model = Column(String(255), nullable=False)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    cost = Column(String(50), nullable=True)
    status = Column(String(50), default="pending")  # pending, completed, failed
    error_message = Column(String(500), nullable=True)
    request_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<AIRequest {self.id} ({self.status})>"

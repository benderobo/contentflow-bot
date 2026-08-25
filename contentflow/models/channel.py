from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, JSON
from core.database import Base


class Channel(Base):
    __tablename__ = "channels"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    telegram_id = Column(String(255), nullable=False)
    username = Column(String(255), nullable=True)
    bot_token = Column(String(255), nullable=True)
    enabled = Column(Boolean, default=True)
    posting_rules = Column(JSON, default={})
    schedule = Column(JSON, default={})
    ai_prompt_id = Column(Integer, ForeignKey("ai_prompts.id"), nullable=True)
    post_template = Column(String(1024), nullable=True)
    auto_source_credit = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Channel {self.name}>"

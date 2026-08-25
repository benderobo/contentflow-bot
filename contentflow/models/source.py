from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, JSON, ForeignKey
from core.database import Base


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)  # telegram, rss, website, html, api
    url = Column(String(2048), nullable=True)
    enabled = Column(Boolean, default=True)
    parse_interval = Column(Integer, default=3600)  # seconds
    parser_config = Column(JSON, default={})
    filters = Column(JSON, default={})
    last_check = Column(DateTime, nullable=True)
    last_success = Column(DateTime, nullable=True)
    last_error = Column(String(1024), nullable=True)
    error_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Source {self.name} ({self.type})>"

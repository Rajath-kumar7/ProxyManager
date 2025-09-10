from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean,UniqueConstraint
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()


class Proxy(Base):
    """SQLAlchemy model for a proxy entry."""
    __tablename__ = 'proxies'

    id = Column(Integer, primary_key=True)
    protocol = Column(String, index=True)
    host = Column(String, index=True)
    port = Column(Integer)

    country = Column(String, nullable=True)
    anonymity = Column(String, nullable=True)

    is_working = Column(Boolean, default=False, index=True)
    latency_ms = Column(Integer, nullable=True)
    download_mbps = Column(Float, nullable=True)
    score = Column(Float, default=0.0, index=True)

    source = Column(String)  # Where the proxy was collected from
    last_tested = Column(DateTime, onupdate=datetime.datetime.utcnow)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('host', 'port', name='_host_port_uc'),
    )

    def __repr__(self):
        return f"<Proxy({self.protocol}://{self.host}:{self.port})>"

    @property
    def url(self) -> str:
        return f"{self.protocol}://{self.host}:{self.port}"

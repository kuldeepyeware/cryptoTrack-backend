"""SQLAlchemy model for cryptocurrency assets."""
from sqlalchemy import Column, Integer, String, Float, DateTime, Index
from sqlalchemy.sql import func

from app.core.database import Base


class Asset(Base):
    """Asset model representing a cryptocurrency holding."""

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    symbol = Column(String, nullable=False)   # e.g., "bitcoin"
    ticker = Column(String, nullable=False)    # e.g., "BTC"
    quantity = Column(Float, nullable=False)
    buy_price = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_user_assets", "user_id", "symbol"),
    )

    def __repr__(self):
        return f"<Asset(id={self.id}, user_id={self.user_id}, ticker={self.ticker}, quantity={self.quantity})>"

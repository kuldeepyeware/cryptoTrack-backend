"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class AssetBase(BaseModel):
    """Base asset schema."""

    symbol: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="CoinGecko ID (e.g., 'bitcoin')",
    )
    ticker: str = Field(
        ...,
        min_length=1,
        max_length=10,
        description="Ticker symbol (e.g., 'BTC')",
    )
    quantity: float = Field(..., gt=0, le=1_000_000_000, description="Amount held")
    buy_price: float = Field(
        ..., gt=0, le=100_000_000, description="Purchase price in USD"
    )

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("ticker")
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        return v.strip().upper()


class AssetCreate(AssetBase):
    """Schema for creating a new asset."""

    pass


class AssetUpdate(BaseModel):
    """Schema for updating an asset."""

    quantity: Optional[float] = Field(None, gt=0, le=1_000_000_000)
    buy_price: Optional[float] = Field(None, gt=0, le=100_000_000)


class AssetResponse(AssetBase):
    """Schema for asset response."""

    id: int
    user_id: str
    created_at: datetime
    current_price: Optional[float] = None
    total_value: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_percent: Optional[float] = None

    class Config:
        from_attributes = True


class AssetAllocation(BaseModel):
    """Schema for portfolio allocation."""

    symbol: str
    ticker: str
    value: float
    percentage: float


class DashboardStats(BaseModel):
    """Schema for dashboard statistics."""

    total_portfolio_value: float
    total_invested: float
    total_profit_loss: float
    total_profit_loss_percent: float
    asset_count: int
    allocations: list[AssetAllocation]

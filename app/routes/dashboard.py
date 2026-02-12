"""Dashboard statistics API routes."""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import verify_clerk_token
from app.schemas.asset import DashboardStats, AssetAllocation
from app.services.coingecko import coingecko_client
from app import crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    user_id: str = Depends(verify_clerk_token),
    db: AsyncSession = Depends(get_db),
):
    """Get portfolio statistics for the authenticated user."""
    assets = await crud.get_user_assets(db, user_id)

    if not assets:
        return DashboardStats(
            total_portfolio_value=0.0,
            total_invested=0.0,
            total_profit_loss=0.0,
            total_profit_loss_percent=0.0,
            asset_count=0,
            allocations=[],
        )

    symbols = [asset.symbol for asset in assets]
    prices = await coingecko_client.get_prices(symbols)

    total_value = 0.0
    total_invested = 0.0
    asset_values = {}

    for asset in assets:
        current_price = prices.get(asset.symbol, 0.0)
        value = current_price * asset.quantity
        invested = asset.buy_price * asset.quantity

        total_value += value
        total_invested += invested

        key = (asset.symbol, asset.ticker)
        if key in asset_values:
            asset_values[key] += value
        else:
            asset_values[key] = value

    total_profit_loss = total_value - total_invested
    total_profit_loss_percent = (
        (total_profit_loss / total_invested * 100) if total_invested > 0 else 0
    )

    allocations = []
    for (symbol, ticker), value in asset_values.items():
        percentage = (value / total_value * 100) if total_value > 0 else 0
        allocations.append(
            AssetAllocation(
                symbol=symbol,
                ticker=ticker,
                value=value,
                percentage=percentage,
            )
        )

    allocations.sort(key=lambda x: x.value, reverse=True)

    return DashboardStats(
        total_portfolio_value=total_value,
        total_invested=total_invested,
        total_profit_loss=total_profit_loss,
        total_profit_loss_percent=total_profit_loss_percent,
        asset_count=len(assets),
        allocations=allocations,
    )

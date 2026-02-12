"""Asset management API routes."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.core.auth import verify_clerk_token
from app.schemas.asset import (
    AssetCreate,
    AssetUpdate,
    AssetResponse,
    AssetResponseBase,
)
from app.services.coingecko import coingecko_client
from app import crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/assets", tags=["assets"])


@router.get("", response_model=List[AssetResponse])
async def get_assets(
    user_id: str = Depends(verify_clerk_token),
    db: AsyncSession = Depends(get_db),
):
    """Get all assets for the authenticated user with current prices."""
    assets = await crud.get_user_assets(db, user_id)

    symbols = [asset.symbol for asset in assets]
    prices = await coingecko_client.get_prices(symbols) if symbols else {}

    response = []
    for asset in assets:
        current_price = prices.get(asset.symbol, 0.0)
        total_value = current_price * asset.quantity
        invested_value = asset.buy_price * asset.quantity
        profit_loss = total_value - invested_value
        profit_loss_percent = (
            (profit_loss / invested_value * 100) if invested_value > 0 else 0
        )

        response.append(
            AssetResponse(
                id=asset.id,
                user_id=asset.user_id,
                symbol=asset.symbol,
                ticker=asset.ticker,
                quantity=asset.quantity,
                buy_price=asset.buy_price,
                created_at=asset.created_at,
                current_price=current_price,
                total_value=total_value,
                profit_loss=profit_loss,
                profit_loss_percent=profit_loss_percent,
            )
        )

    return response


@router.post("", response_model=AssetResponseBase, status_code=201)
async def create_asset(
    asset: AssetCreate,
    user_id: str = Depends(verify_clerk_token),
    db: AsyncSession = Depends(get_db),
):
    """Create a new asset for the authenticated user."""
    logger.info(f"Creating asset {asset.ticker} for user {user_id[:8]}...")
    db_asset = await crud.create_asset(db, asset, user_id)
    return db_asset


@router.put("/{asset_id}", response_model=AssetResponseBase)
async def update_asset(
    asset_id: int,
    asset_update: AssetUpdate,
    user_id: str = Depends(verify_clerk_token),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing asset."""
    db_asset = await crud.update_asset(db, asset_id, asset_update, user_id)

    if not db_asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return db_asset


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: int,
    user_id: str = Depends(verify_clerk_token),
    db: AsyncSession = Depends(get_db),
):
    """Delete an asset."""
    deleted = await crud.delete_asset(db, asset_id, user_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Asset not found")

    return None


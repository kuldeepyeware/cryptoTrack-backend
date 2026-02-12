"""CRUD operations for assets."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List, Optional

from app.models.asset import Asset
from app.schemas.asset import AssetCreate, AssetUpdate


async def get_user_assets(db: AsyncSession, user_id: str) -> List[Asset]:
    """Get all assets for a specific user."""
    result = await db.execute(
        select(Asset).where(Asset.user_id == user_id).order_by(Asset.created_at.desc())
    )
    return result.scalars().all()


async def get_asset_by_id(
    db: AsyncSession, asset_id: int, user_id: str
) -> Optional[Asset]:
    """Get a specific asset by ID, ensuring it belongs to the user."""
    result = await db.execute(
        select(Asset).where(Asset.id == asset_id, Asset.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_asset(db: AsyncSession, asset: AssetCreate, user_id: str) -> Asset:
    """Create a new asset for a user."""
    db_asset = Asset(
        user_id=user_id,
        symbol=asset.symbol,
        ticker=asset.ticker,
        quantity=asset.quantity,
        buy_price=asset.buy_price,
    )
    db.add(db_asset)
    await db.flush()
    await db.refresh(db_asset)
    return db_asset


async def update_asset(
    db: AsyncSession, asset_id: int, asset_update: AssetUpdate, user_id: str
) -> Optional[Asset]:
    """Update an existing asset, ensuring it belongs to the user."""
    db_asset = await get_asset_by_id(db, asset_id, user_id)
    if not db_asset:
        return None

    if asset_update.quantity is not None:
        db_asset.quantity = asset_update.quantity
    if asset_update.buy_price is not None:
        db_asset.buy_price = asset_update.buy_price

    await db.flush()
    await db.refresh(db_asset)
    return db_asset


async def delete_asset(db: AsyncSession, asset_id: int, user_id: str) -> bool:
    """Delete an asset, ensuring it belongs to the user."""
    result = await db.execute(
        delete(Asset).where(Asset.id == asset_id, Asset.user_id == user_id)
    )
    return result.rowcount > 0

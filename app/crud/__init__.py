"""CRUD operations package."""
from app.crud.asset import (  # noqa: F401
    get_user_assets,
    get_asset_by_id,
    create_asset,
    update_asset,
    delete_asset,
)

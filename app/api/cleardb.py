from fastapi import APIRouter, Depends

from app.api.deps import get_database_maintenance_service
from app.schemas.cleardb import ClearDBResponse
from app.services.database_maintenance_service import DatabaseMaintenanceService

router = APIRouter(tags=["maintenance"])


@router.post("/cleardb", response_model=ClearDBResponse)
async def clear_db(
    maintenance: DatabaseMaintenanceService = Depends(get_database_maintenance_service),
):
    deleted = await maintenance.clear_graph_collections()
    return ClearDBResponse(status="cleared", deleted=deleted)

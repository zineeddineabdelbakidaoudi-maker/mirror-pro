"""Stock movement repository."""
from typing import List
from sqlalchemy.orm import Session
from app.models.stock import StockMovement
from app.repositories.base_repository import BaseRepository


class StockMovementRepository(BaseRepository[StockMovement]):
    def __init__(self, session: Session):
        super().__init__(session, StockMovement)

    def get_by_material(self, material_id: int, limit: int = 50) -> List[StockMovement]:
        return (
            self.session.query(StockMovement)
            .filter(StockMovement.material_id == material_id)
            .order_by(StockMovement.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_reference(self, reference_type: str, reference_id: int) -> List[StockMovement]:
        return (
            self.session.query(StockMovement)
            .filter(
                StockMovement.reference_type == reference_type,
                StockMovement.reference_id == reference_id,
            )
            .all()
        )

    def get_recent(self, limit: int = 20) -> List[StockMovement]:
        return (
            self.session.query(StockMovement)
            .order_by(StockMovement.created_at.desc())
            .limit(limit)
            .all()
        )

"""Material repository."""
from typing import List
from sqlalchemy.orm import Session
from app.models.material import Material
from app.repositories.base_repository import BaseRepository


class MaterialRepository(BaseRepository[Material]):
    def __init__(self, session: Session):
        super().__init__(session, Material)

    def get_all_active(self) -> List[Material]:
        return (
            self.session.query(Material)
            .filter(Material.is_deleted == False)
            .order_by(Material.designation)
            .all()
        )

    def search(self, term: str) -> List[Material]:
        return (
            self.session.query(Material)
            .filter(
                Material.is_deleted == False,
                (Material.designation.ilike(f"%{term}%"))
                | (Material.code.ilike(f"%{term}%"))
                | (Material.category.ilike(f"%{term}%")),
            )
            .all()
        )

    def get_low_stock(self) -> List[Material]:
        materials = self.get_all_active()
        return [m for m in materials if m.is_low_stock]

    def get_by_category(self, category: str) -> List[Material]:
        return (
            self.session.query(Material)
            .filter(Material.is_deleted == False, Material.category == category)
            .order_by(Material.designation)
            .all()
        )

    def get_total_stock_value(self) -> float:
        materials = self.get_all_active()
        return sum(m.stock_value for m in materials)

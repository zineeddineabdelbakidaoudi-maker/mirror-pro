"""Supplier repository."""
from typing import List
from sqlalchemy.orm import Session
from app.models.supplier import Supplier
from app.repositories.base_repository import BaseRepository


class SupplierRepository(BaseRepository[Supplier]):
    def __init__(self, session: Session):
        super().__init__(session, Supplier)

    def search(self, term: str) -> List[Supplier]:
        return (
            self.session.query(Supplier)
            .filter(
                Supplier.is_deleted == False,
                (Supplier.name.ilike(f"%{term}%")) | (Supplier.phone.ilike(f"%{term}%")),
            )
            .all()
        )

    def get_all_active(self) -> List[Supplier]:
        return (
            self.session.query(Supplier)
            .filter(Supplier.is_deleted == False)
            .order_by(Supplier.name)
            .all()
        )

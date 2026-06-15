"""Order repository."""
from typing import List, Optional
from datetime import date
from sqlalchemy.orm import Session, joinedload
from app.models.order import Order, OrderItem, OrderMaterial, OrderStatusHistory
from app.repositories.base_repository import BaseRepository


class OrderRepository(BaseRepository[Order]):
    def __init__(self, session: Session):
        super().__init__(session, Order)

    def get_with_details(self, order_id: int) -> Optional[Order]:
        return (
            self.session.query(Order)
            .options(
                joinedload(Order.items).joinedload(OrderItem.materials),
                joinedload(Order.customer),
            )
            .filter(Order.id == order_id)
            .first()
        )

    def get_all_with_customer(self, include_deleted: bool = False) -> List[Order]:
        query = (
            self.session.query(Order)
            .options(joinedload(Order.customer))
        )
        if not include_deleted:
            query = query.filter(Order.is_deleted == False)
        return query.order_by(Order.created_at.desc()).all()

    def get_by_status(self, status: str) -> List[Order]:
        return (
            self.session.query(Order)
            .options(joinedload(Order.customer))
            .filter(Order.status == status, Order.is_deleted == False)
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_pending_orders(self) -> List[Order]:
        pending_statuses = [
            "confirmée", "en_attente", "en_production",
            "en_découpe", "en_assemblage", "finition", "prêt",
        ]
        return (
            self.session.query(Order)
            .options(joinedload(Order.customer))
            .filter(Order.status.in_(pending_statuses), Order.is_deleted == False)
            .order_by(Order.created_at.desc())
            .all()
        )

    def get_urgent_orders(self) -> List[Order]:
        return (
            self.session.query(Order)
            .options(joinedload(Order.customer))
            .filter(
                Order.urgency == "urgente",
                Order.status.notin_(["livrée", "annulée"]),
                Order.is_deleted == False,
            )
            .all()
        )

    def get_next_reference_count(self, d: date = None) -> int:
        count = self.session.query(Order).count()
        return count + 1

    def get_today_orders(self) -> List[Order]:
        return (
            self.session.query(Order)
            .filter(Order.order_date == date.today(), Order.is_deleted == False)
            .all()
        )

    def add_status_history(self, order_id: int, old_status: str, new_status: str, notes: str = None):
        history = OrderStatusHistory(
            order_id=order_id,
            old_status=old_status,
            new_status=new_status,
            notes=notes,
        )
        self.session.add(history)

    def get_status_history(self, order_id: int) -> List[OrderStatusHistory]:
        return (
            self.session.query(OrderStatusHistory)
            .filter(OrderStatusHistory.order_id == order_id)
            .order_by(OrderStatusHistory.created_at.asc())
            .all()
        )
